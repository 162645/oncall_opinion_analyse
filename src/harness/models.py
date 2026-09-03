"""Typed contracts shared by Harness nodes.

LangGraph state remains JSON-compatible dictionaries for checkpoint portability;
these dataclasses define the shape at node boundaries and are deliberately
free of model/provider-specific fields.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class TimeRange:
    start_time: str
    end_time: str


@dataclass(frozen=True)
class TaskSpec:
    kind: str
    goal: str
    region: Optional[str]
    metric: str
    time_range: TimeRange


@dataclass(frozen=True)
class PlanStep:
    query_id: str
    params: Dict[str, Any]
    purpose: str = "collect evidence"


@dataclass(frozen=True)
class AnalysisPlan:
    plan_id: str
    round: int
    steps: List[PlanStep] = field(default_factory=list)


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    query_id: str
    status: str
    data: Any = None
    error: Optional[str] = None
    quality: str = "unknown"


@dataclass(frozen=True)
class Verification:
    verdict: str
    score: float
    successful_evidence: int
    total_evidence: int
    missing: List[str] = field(default_factory=list)
    reason: str = ""


def to_dict(value: Any) -> Dict[str, Any]:
    """Serialize a contract for LangGraph state/checkpoint storage."""
    return asdict(value)
