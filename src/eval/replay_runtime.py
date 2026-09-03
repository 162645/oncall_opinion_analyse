"""Deterministic ToolRuntime replacement for network-analysis replay evals."""

from typing import Any, Dict

from src.runtime import ToolErrorKind, ToolExecutionResult


class ReplayRuntime:
    def __init__(self, fixture: Dict[str, Any]):
        self.fixture = fixture
        self.calls: list[dict] = []

    async def execute(self, name: str, arguments: Dict[str, Any], **kwargs):
        self.calls.append({"query_id": name, "arguments": dict(arguments)})
        if name not in self.fixture:
            return ToolExecutionResult(False, error=f"fixture unavailable: {name}",
                                       error_kind=ToolErrorKind.PERMANENT, attempts=1)
        if isinstance(self.fixture[name], dict) and "__error__" in self.fixture[name]:
            fault = self.fixture[name]
            return ToolExecutionResult(False, error=str(fault["__error__"]),
                                       error_kind=ToolErrorKind(fault.get("error_kind", "permanent")), attempts=1)
        return ToolExecutionResult(True, data=self.fixture[name], attempts=1)
