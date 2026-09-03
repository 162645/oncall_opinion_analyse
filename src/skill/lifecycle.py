"""Trace-driven Skill evolution with replay gates and rollback."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .executor import SkillExecutor
from .models import Skill, SkillExecution, SkillStatus


@dataclass
class ReplayCase:
    name: str
    params: Dict[str, Any]
    expected_success: bool = True
    max_duration_ms: Optional[int] = None
    required_steps: List[str] = field(default_factory=list)


@dataclass
class ReplayReport:
    total: int
    passed: int
    success_rate: float
    p95_duration_ms: float
    regressions: List[str] = field(default_factory=list)


@dataclass
class SkillVersion:
    version: str
    snapshot: Skill
    status: SkillStatus
    replay_report: Optional[ReplayReport] = None
    approved_by: Optional[str] = None


class SkillLifecycleManager:
    """Enforces candidate -> validated -> approved -> published transitions."""

    def __init__(self, executor: SkillExecutor, min_replay_success_rate: float = 0.95):
        self.executor = executor
        self.min_replay_success_rate = min_replay_success_rate
        self.versions: Dict[str, List[SkillVersion]] = {}

    def register_candidate(self, skill: Skill) -> SkillVersion:
        skill.status = SkillStatus.CANDIDATE
        version = SkillVersion(skill.version, copy.deepcopy(skill), skill.status)
        self.versions.setdefault(skill.id, []).append(version)
        return version

    async def validate(self, skill: Skill, cases: List[ReplayCase]) -> ReplayReport:
        executions: List[SkillExecution] = []
        regressions: List[str] = []
        for case in cases:
            execution = await self.executor.execute(skill, case.params, {"user_id": "replay"})
            executions.append(execution)
            step_names = {step["step_name"] for step in execution.steps_executed}
            passed = execution.success == case.expected_success
            if case.max_duration_ms is not None:
                passed = passed and execution.duration_ms <= case.max_duration_ms
            passed = passed and set(case.required_steps).issubset(step_names)
            if not passed:
                regressions.append(case.name)
        durations = sorted(e.duration_ms for e in executions)
        passed_count = len(cases) - len(regressions)
        p95 = durations[min(int(len(durations) * 0.95), len(durations) - 1)] if durations else 0.0
        report = ReplayReport(
            total=len(cases), passed=passed_count,
            success_rate=passed_count / len(cases) if cases else 0.0,
            p95_duration_ms=float(p95), regressions=regressions,
        )
        if report.success_rate >= self.min_replay_success_rate:
            skill.status = SkillStatus.VALIDATED
        current = self._current(skill.id)
        if current:
            current.status = skill.status
            current.replay_report = report
        return report

    def approve(self, skill: Skill, approver: str):
        if skill.status != SkillStatus.VALIDATED:
            raise ValueError("Only validated skills can be approved")
        skill.status = SkillStatus.APPROVED
        current = self._current(skill.id)
        current.status = skill.status
        current.approved_by = approver

    def publish(self, skill: Skill):
        if skill.status != SkillStatus.APPROVED:
            raise ValueError("Only approved skills can be published")
        skill.status = SkillStatus.PUBLISHED
        self._current(skill.id).status = skill.status

    def rollback(self, skill: Skill) -> Skill:
        versions = self.versions.get(skill.id, [])
        if len(versions) < 2:
            raise ValueError("No previous skill version available")
        versions[-1].status = SkillStatus.ROLLED_BACK
        restored = copy.deepcopy(versions[-2].snapshot)
        restored.status = SkillStatus.PUBLISHED
        return restored

    def _current(self, skill_id: str) -> Optional[SkillVersion]:
        versions = self.versions.get(skill_id, [])
        return versions[-1] if versions else None
