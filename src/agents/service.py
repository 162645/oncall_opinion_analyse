"""Compatibility facade for the evidence-driven Agent Harness.

The service layer intentionally contains no second orchestration strategy.
HTTP, gRPC and Skill callers all enter the same six-node LangGraph Harness;
this module only adapts its result to the historical service response shape.
"""

from dataclasses import dataclass
import time
from typing import Dict, List, Optional

from src.harness import get_harness


@dataclass
class AgentServiceResult:
    """Stable response contract kept for HTTP/gRPC/Skill compatibility."""

    success: bool
    message: str = ""
    intent: Optional[str] = None
    knowledge: Optional[str] = None
    analysis: Optional[str] = None
    diagnosis: Optional[str] = None
    chart_data: Optional[dict] = None
    confidence: float = 0.0
    trace: Optional[List[Dict]] = None
    skill_recommendation: Optional[Dict] = None
    token_usage: Optional[Dict] = None
    total_duration_ms: int = 0

    def __post_init__(self):
        if self.trace is None:
            self.trace = []


class AgentService:
    """Thin compatibility facade over the single production execution path."""

    def __init__(self):
        self.harness = get_harness()

    async def process(
        self,
        query: str,
        mode: str = "sequential",
        session_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AgentServiceResult:
        started = time.perf_counter()
        result = await self.harness.execute(
            query=query,
            session_id=session_id,
            metadata={"mode": mode, "provider": provider, "model": model},
        )
        chart_data = result.chart_data or {}
        return AgentServiceResult(
            success=result.success,
            message=result.message,
            intent=result.state.get("task", {}).get("kind", "unknown"),
            chart_data=chart_data,
            confidence=result.confidence,
            trace=result.trace or [],
            token_usage={},
            total_duration_ms=int((time.perf_counter() - started) * 1000),
        )


_agent_service: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    """Return the process-wide Harness facade."""
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service
