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
    analysis_dimensions: List[Literal["time", "asn", "prefix", "path", "region", "operator"]] = Field(default_factory=list)
    comparison: Dict[str, Any] = Field(default_factory=dict)
    constraints: List[str] = Field(default_factory=list)
    semantic_requirements: List[str] = Field(default_factory=list)
    intent_summary: str = ""
    sub_questions: List[str] = Field(default_factory=list)
    answer_requirements: List[str] = Field(default_factory=list)
    ambiguities: List[str] = Field(default_factory=list)
    semantic_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class PlanStep(HarnessModel):
    action_type: Literal["catalog_query", "generated_query"] = "catalog_query"
    query_id: str
    params: Dict[str, Any] = Field(default_factory=dict)
    purpose: str = "collect evidence"
    expected_information_gain: Literal["high", "medium", "low"] = "medium"
    estimated_cost: Literal["low", "medium", "high"] = "low"
    depends_on: List[str] = Field(default_factory=list)
    evidence_goal: str = ""
    stop_condition: Optional[str] = None
    rationale: str = ""


class AnalysisPlan(HarnessModel):
    plan_id: str
    round: int
    steps: List[PlanStep] = Field(default_factory=list)
    source: Literal["recipe", "llm_guarded", "llm_refined"] = "recipe"
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
    verdict: Literal["PASS", "REPLAN", "PARTIAL", "ABSTAIN"]
    score: float
    successful_evidence: int
    total_evidence: int
    missing: List[str] = Field(default_factory=list)
    missing_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    facts: List[Dict[str, Any]] = Field(default_factory=list)
    checks: Dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class RetrievalSource(HarnessModel):
    source: Literal["skill", "knowledge", "graph", "bm25", "history"]
    query: str
    purpose: str = ""
    priority: Literal["high", "medium", "low"] = "medium"


class RetrievalPlan(HarnessModel):
    need_retrieval: bool = False
    sources: List[RetrievalSource] = Field(default_factory=list)


class PlanningContext(HarnessModel):
    task_summary: str = ""
    domain_guidance: List[str] = Field(default_factory=list)
    historical_context: List[str] = Field(default_factory=list)
    entity_context: List[str] = Field(default_factory=list)
    known_facts: List[str] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    hypotheses: List[str] = Field(default_factory=list)
    available_capabilities: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class SemanticReview(HarnessModel):
    answered_requirements: List[str] = Field(default_factory=list)
    missing_requirements: List[str] = Field(default_factory=list)
    supported_claims: List[str] = Field(default_factory=list)
    unsupported_claims: List[str] = Field(default_factory=list)
    uncertainty: List[str] = Field(default_factory=list)
    recommended_next_objective: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ExecutionResult(HarnessModel):
    status: Literal["observed", "unavailable", "failed"]
    data: Any = None
    evidence_id: Optional[str] = None
    latency_ms: int = 0
    row_count: int = 0
    data_quality: str = "unknown"
    error_kind: Optional[str] = None
    retryable: bool = False
    truncated: bool = False
    query_cost: Optional[float] = None
    attempt: int = 1


class QueryIR(HarnessModel):
    """Safe intermediate representation for future long-tail queries."""
    table: str
    dimensions: List[str] = Field(default_factory=list)
    metrics: List[Dict[str, Any]] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)
    group_by: List[str] = Field(default_factory=list)
    order_by: List[str] = Field(default_factory=list)
    limit: int = Field(default=100, ge=1, le=1000)
    time_range: Optional[TimeRange] = None


def to_dict(value: Any) -> Dict[str, Any]:
    """Serialize a contract for LangGraph state/checkpoint storage."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return dict(value)
