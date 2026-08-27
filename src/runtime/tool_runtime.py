"""Governed tool execution shared by MCP, graph nodes and skills."""

from __future__ import annotations

import asyncio
import inspect
import random
import time
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Protocol

from jsonschema import Draft202012Validator


class PermissionLevel(IntEnum):
    READ = 10
    WRITE = 20
    DANGEROUS = 30


class ToolErrorKind(str, Enum):
    VALIDATION = "validation"
    PERMISSION = "permission"
    TIMEOUT = "timeout"
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    CIRCUIT_OPEN = "circuit_open"


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_ms: float = 20.0
    max_delay_ms: float = 500.0
    jitter_ratio: float = 0.15


@dataclass(frozen=True)
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0


@dataclass
class CircuitBreaker:
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    failures: int = 0
    opened_at: Optional[float] = None

    @property
    def state(self) -> str:
        if self.opened_at is None:
            return "closed"
        if time.monotonic() - self.opened_at >= self.config.recovery_timeout_seconds:
            return "half_open"
        return "open"

    def allow(self) -> bool:
        return self.state != "open"

    def success(self):
        self.failures = 0
        self.opened_at = None

    def failure(self):
        self.failures += 1
        if self.failures >= self.config.failure_threshold:
            self.opened_at = time.monotonic()


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[..., Any]
    permission: PermissionLevel = PermissionLevel.READ
    side_effecting: bool = False
    timeout_seconds: float = 10.0
    retry: RetryPolicy = field(default_factory=RetryPolicy)


@dataclass
class AuditEvent:
    tool_name: str
    started_at: float
    duration_ms: float
    success: bool
    attempts: int
    error_kind: Optional[str] = None
    idempotency_key: Optional[str] = None
    cache_hit: bool = False
    actor: str = "anonymous"
    trace_id: str = ""


@dataclass
class ToolExecutionResult:
    success: bool
    data: Any = None
    error: Optional[str] = None
    error_kind: Optional[ToolErrorKind] = None
    attempts: int = 0
    duration_ms: float = 0.0
    idempotency_hit: bool = False


class IdempotencyStore(Protocol):
    async def get(self, key: str) -> Optional[dict]: ...
    async def put(self, key: str, value: dict, ttl_seconds: int = 86400): ...


class InMemoryIdempotencyStore:
    def __init__(self):
        self._values: Dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[dict]:
        async with self._lock:
            return self._values.get(key)

    async def put(self, key: str, value: dict, ttl_seconds: int = 86400):
        async with self._lock:
            self._values[key] = value


class ToolRuntime:
    """Executes registered tools through one reliability and security pipeline."""

    def __init__(
        self,
        idempotency_store: Optional[IdempotencyStore] = None,
        output_limit_bytes: int = 1_000_000,
        transient_exceptions: tuple[type[BaseException], ...] = (
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
        ),
    ):
        self._tools: Dict[str, ToolDefinition] = {}
        self._breakers: Dict[str, CircuitBreaker] = {}
        self.idempotency_store = idempotency_store or InMemoryIdempotencyStore()
        self.output_limit_bytes = output_limit_bytes
        self.transient_exceptions = transient_exceptions
        self.audit_events: List[AuditEvent] = []

    def register(
        self,
        definition: ToolDefinition,
        breaker_config: Optional[CircuitBreakerConfig] = None,
    ):
        Draft202012Validator.check_schema(definition.parameters)
        self._tools[definition.name] = definition
        self._breakers[definition.name] = CircuitBreaker(
            breaker_config or CircuitBreakerConfig()
        )

    def definitions(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    async def execute(
        self,
        name: str,
        arguments: Dict[str, Any],
        *,
        actor: str = "anonymous",
        granted_permission: PermissionLevel = PermissionLevel.READ,
        idempotency_key: Optional[str] = None,
        trace_id: str = "",
        deadline_seconds: Optional[float] = None,
    ) -> ToolExecutionResult:
        started = time.perf_counter()
        tool = self._tools.get(name)
        if tool is None:
            return self._finish(name, started, False, 0, "tool not found", ToolErrorKind.PERMANENT, actor, trace_id, idempotency_key)

        errors = sorted(Draft202012Validator(tool.parameters).iter_errors(arguments), key=lambda e: list(e.path))
        if errors:
            detail = "; ".join(error.message for error in errors)
            return self._finish(name, started, False, 0, detail, ToolErrorKind.VALIDATION, actor, trace_id, idempotency_key)

        if granted_permission < tool.permission:
            return self._finish(name, started, False, 0, "permission denied", ToolErrorKind.PERMISSION, actor, trace_id, idempotency_key)

        if tool.side_effecting and not idempotency_key:
            return self._finish(name, started, False, 0, "side-effecting tool requires idempotency_key", ToolErrorKind.VALIDATION, actor, trace_id, idempotency_key)

        if idempotency_key:
            cached = await self.idempotency_store.get(idempotency_key)
            if cached is not None:
                result = ToolExecutionResult(**cached)
                result.idempotency_hit = True
                self._audit(name, started, result.success, result.attempts, result.error_kind, actor, trace_id, idempotency_key, True)
                return result

        breaker = self._breakers[name]
        if not breaker.allow():
            return self._finish(name, started, False, 0, "circuit breaker open", ToolErrorKind.CIRCUIT_OPEN, actor, trace_id, idempotency_key)

        attempts = 0
        timeout = min(tool.timeout_seconds, deadline_seconds) if deadline_seconds else tool.timeout_seconds
        last_error: Optional[BaseException] = None
        last_kind = ToolErrorKind.PERMANENT
        while attempts < tool.retry.max_attempts:
            attempts += 1
            try:
                value = tool.handler(**arguments)
                if inspect.isawaitable(value):
                    value = await asyncio.wait_for(value, timeout=timeout)
                if len(repr(value).encode("utf-8")) > self.output_limit_bytes:
                    raise ValueError("tool output exceeds configured size limit")
                breaker.success()
                result = ToolExecutionResult(True, data=value, attempts=attempts, duration_ms=(time.perf_counter() - started) * 1000)
                if idempotency_key:
                    await self.idempotency_store.put(idempotency_key, self._serialize_result(result))
                self._audit(name, started, True, attempts, None, actor, trace_id, idempotency_key, False)
                return result
            except asyncio.TimeoutError as exc:
                last_error, last_kind = exc, ToolErrorKind.TIMEOUT
                breaker.failure()
            except self.transient_exceptions as exc:
                last_error, last_kind = exc, ToolErrorKind.TRANSIENT
                breaker.failure()
            except Exception as exc:
                last_error, last_kind = exc, ToolErrorKind.PERMANENT
                breaker.failure()
                break

            if attempts < tool.retry.max_attempts:
                delay = min(tool.retry.base_delay_ms * (2 ** (attempts - 1)), tool.retry.max_delay_ms)
                jitter = delay * tool.retry.jitter_ratio * random.random()
                await asyncio.sleep((delay + jitter) / 1000)

        result = self._finish(name, started, False, attempts, str(last_error or "tool failed"), last_kind, actor, trace_id, idempotency_key)
        if idempotency_key and last_kind == ToolErrorKind.PERMANENT:
            await self.idempotency_store.put(idempotency_key, self._serialize_result(result))
        return result

    @staticmethod
    def _serialize_result(result: ToolExecutionResult) -> dict:
        return {
            "success": result.success,
            "data": result.data,
            "error": result.error,
            "error_kind": result.error_kind,
            "attempts": result.attempts,
            "duration_ms": result.duration_ms,
            "idempotency_hit": result.idempotency_hit,
        }

    def _finish(self, name, started, success, attempts, error, kind, actor, trace_id, idempotency_key):
        result = ToolExecutionResult(success, error=error, error_kind=kind, attempts=attempts, duration_ms=(time.perf_counter() - started) * 1000)
        self._audit(name, started, success, attempts, kind, actor, trace_id, idempotency_key, False)
        return result

    def _audit(self, name, started, success, attempts, kind, actor, trace_id, idempotency_key, cache_hit):
        self.audit_events.append(AuditEvent(
            tool_name=name,
            started_at=time.time() - (time.perf_counter() - started),
            duration_ms=(time.perf_counter() - started) * 1000,
            success=success,
            attempts=attempts,
            error_kind=kind.value if isinstance(kind, ToolErrorKind) else kind,
            idempotency_key=idempotency_key,
            cache_hit=cache_hit,
            actor=actor,
            trace_id=trace_id,
        ))

