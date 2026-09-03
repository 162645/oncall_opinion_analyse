"""Pydantic contracts at the boundaries of the evidence-driven Harness."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class HarnessModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class TimeRange(HarnessModel):
    start_time: str
    end_time: str
    hours: Optional[int] = None


class TaskSpec(HarnessModel):
    kind: Literal["network_analysis", "knowledge"]
    goal: Literal["describe", "diagnose"]
    region: Optional[str] = None
    metric: Literal["rtt", "p95", "p99"] = "rtt"
    planning_mode: Literal["recipe", "long_tail"] = "recipe"
    needs_baseline: bool = False
    wants_path_analysis: bool = False
    time_range: TimeRange


class PlanStep(HarnessModel):
    query_id: str
    params: Dict[str, Any] = Field(default_factory=dict)
    purpose: str = "collect evidence"


class AnalysisPlan(HarnessModel):
    plan_id: str
    round: int
    steps: List[PlanStep] = Field(default_factory=list)
    source: Literal["recipe", "llm_guarded"] = "recipe"
    rationale: str = ""


class Evidence(HarnessModel):
    evidence_id: str
    query_id: str
    status: str
    data: Any = None
    error: Optional[str] = None
    quality: str = "unknown"
    source: str = "unknown"
    params: Dict[str, Any] = Field(default_factory=dict)
    observed_at: Optional[str] = None
    trace_id: str = ""
    kind: Literal["measurement", "context"] = "measurement"
    attempts: int = 0
    attempt: int = 1


class Verification(HarnessModel):
    verdict: Literal["PASS", "PARTIAL", "ABSTAIN"]
    score: float
    successful_evidence: int
    total_evidence: int
    missing: List[str] = Field(default_factory=list)
    missing_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    facts: List[Dict[str, Any]] = Field(default_factory=list)
    checks: Dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


def to_dict(value: Any) -> Dict[str, Any]:
    """Serialize a contract for LangGraph state/checkpoint storage."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return dict(value)
