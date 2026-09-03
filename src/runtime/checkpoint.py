"""Checkpoint and execution-ledger adapters.

LangGraph owns node-level state and cursor persistence.  The execution ledger
stores tool idempotency records separately so replaying a checkpoint cannot
repeat an already committed side effect.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from langgraph.checkpoint.memory import InMemorySaver
try:
    # Optional in the 2 GB demo profile.  Redis persistence remains available
    # when the extra package is installed, while memory checkpoints keep the
    # core harness importable and runnable without Redis.
    from langgraph.checkpoint.redis.aio import AsyncRedisSaver
except ImportError:  # pragma: no cover - exercised by the slim deployment
    AsyncRedisSaver = None  # type: ignore[assignment,misc]


@dataclass(frozen=True)
class CheckpointConfig:
    backend: str = "memory"
    redis_url: str = "redis://localhost:6379/0"
    prefix: str = "agent_harness"
    ttl_minutes: int = 1440


class CheckpointerFactory:
    """Builds supported LangGraph checkpointers without hiding degradation."""

    @staticmethod
    def create(config: CheckpointConfig):
        if config.backend == "memory":
            return InMemorySaver()
        if config.backend == "redis":
            if AsyncRedisSaver is None:
                raise RuntimeError(
                    "Redis checkpoint backend requires the optional "
                    "langgraph-checkpoint-redis package"
                )
            return AsyncRedisSaver(
                redis_url=config.redis_url,
                checkpoint_prefix=f"{config.prefix}:checkpoint",
                checkpoint_write_prefix=f"{config.prefix}:write",
                ttl={"default_ttl": config.ttl_minutes, "refresh_on_read": True},
            )
        raise ValueError(f"Unsupported checkpoint backend: {config.backend}")


class RedisExecutionLedger:
    """Atomic Redis ledger for side-effecting tool executions."""

    def __init__(self, redis_client: Any, prefix: str = "agent_harness:tool"):
        self.redis = redis_client
        self.prefix = prefix

    def _key(self, idempotency_key: str) -> str:
        return f"{self.prefix}:{idempotency_key}"

    async def get(self, idempotency_key: str) -> Optional[dict]:
        value = await self.redis.get(self._key(idempotency_key))
        if value is None:
            return None
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        return json.loads(value)

    async def put_if_absent(
        self,
        idempotency_key: str,
        value: dict,
        ttl_seconds: int = 86400,
    ) -> bool:
        payload = json.dumps(value, ensure_ascii=False, default=str)
        return bool(
            await self.redis.set(
                self._key(idempotency_key), payload, ex=ttl_seconds, nx=True
            )
        )

    async def put(self, idempotency_key: str, value: dict, ttl_seconds: int = 86400):
        payload = json.dumps(value, ensure_ascii=False, default=str)
        await self.redis.set(self._key(idempotency_key), payload, ex=ttl_seconds)
