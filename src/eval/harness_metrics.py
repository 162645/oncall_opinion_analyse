"""Evaluation records for task quality, reliability, latency and cost."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List

from .harness_benchmark import percentile


@dataclass
class AgentEvaluationRecord:
    task_id: str
    task_success: bool
    tool_calls: int
    tool_successes: int
    recovery_attempted: bool
    recovery_succeeded: bool
    latency_ms: float
    input_tokens: int = 0
    output_tokens: int = 0
    token_cost_usd: float = 0.0
    skill_regression_passed: bool = True


class HarnessEvaluator:
    def __init__(self):
        self.records: List[AgentEvaluationRecord] = []

    def record(self, record: AgentEvaluationRecord):
        self.records.append(record)

    def summary(self) -> Dict[str, Any]:
        count = len(self.records)
        tools = sum(record.tool_calls for record in self.records)
        recoveries = [record for record in self.records if record.recovery_attempted]
        return {
            "tasks": count,
            "task_success_rate": sum(record.task_success for record in self.records) / count if count else 0.0,
            "tool_success_rate": sum(record.tool_successes for record in self.records) / tools if tools else 1.0,
            "recovery_success_rate": sum(record.recovery_succeeded for record in recoveries) / len(recoveries) if recoveries else 1.0,
            "p95_latency_ms": percentile((record.latency_ms for record in self.records), 95),
            "input_tokens": sum(record.input_tokens for record in self.records),
            "output_tokens": sum(record.output_tokens for record in self.records),
            "token_cost_usd": sum(record.token_cost_usd for record in self.records),
            "skill_regression_pass_rate": sum(record.skill_regression_passed for record in self.records) / count if count else 0.0,
        }

    def export(self) -> Dict[str, Any]:
        return {"summary": self.summary(), "records": [asdict(record) for record in self.records]}
