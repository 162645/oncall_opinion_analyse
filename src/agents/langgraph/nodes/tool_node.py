"""Governed tool execution node; production code contains no mock handlers."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, List, Optional

from src.runtime import PermissionLevel, ToolRuntime

from ..state import AgentState


class ToolNode:
    """Executes planner output through the shared ToolRuntime.

    A planner may be injected by the application.  Without one, callers pass
    explicit ``metadata.tool_calls``; the node never fabricates production data.
    """

    def __init__(
        self,
        runtime: Optional[ToolRuntime] = None,
        planner: Optional[Callable[[AgentState], Awaitable[List[Dict[str, Any]]]]] = None,
    ):
        self.runtime = runtime or ToolRuntime()
        self.planner = planner

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": definition.name,
                "description": definition.description,
                "parameters": definition.parameters,
                "permission": definition.permission.name.lower(),
                "side_effecting": definition.side_effecting,
            }
            for definition in self.runtime.definitions()
        ]

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        calls = await self._plan_tool_calls(state)
        results: Dict[str, Any] = {}
        completed = dict(state.get("completed_tools", {}))
        run_id = state.get("run_id", "unknown")
        actor = state.get("metadata", {}).get("actor", "agent")

        for index, call in enumerate(calls):
            name = call["tool"]
            key = call.get("idempotency_key") or f"{run_id}:tools:{index}:{name}"
            permission = getattr(
                PermissionLevel,
                call.get("permission", "read").upper(),
                PermissionLevel.READ,
            )
            result = await self.runtime.execute(
                name,
                call.get("arguments", call.get("params", {})),
                actor=actor,
                granted_permission=permission,
                idempotency_key=key if call.get("side_effecting", False) else call.get("idempotency_key"),
                deadline_seconds=call.get("deadline_seconds"),
            )
            results[name] = {
                "success": result.success,
                "data": result.data,
                "error": result.error,
                "error_kind": result.error_kind.value if result.error_kind else None,
                "attempts": result.attempts,
                "duration_ms": result.duration_ms,
                "idempotency_hit": result.idempotency_hit,
            }
            if result.success:
                completed[key] = results[name]
            elif call.get("required", True):
                return {
                    "tool_results": results,
                    "completed_tools": completed,
                    "error": f"Required tool failed: {name}: {result.error}",
                    "current_step": "tools",
                    "next_action": "failure",
                }

        return {
            "tool_results": results,
            "completed_tools": completed,
            "current_step": "tools",
        }

    async def _plan_tool_calls(self, state: AgentState) -> List[Dict[str, Any]]:
        if self.planner:
            return await self.planner(state)
        calls = state.get("metadata", {}).get("tool_calls", [])
        return list(calls) if isinstance(calls, list) else []
