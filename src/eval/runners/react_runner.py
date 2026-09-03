from typing import Any, Dict

from src.eval.replay_runtime import ReplayRuntime


async def run_react_replay(case: Dict[str, Any], fixture: Dict[str, Any]) -> Dict[str, Any]:
    """A bounded catalog-only baseline for apples-to-apples replay comparison."""
    runtime = ReplayRuntime(fixture)
    calls = []
    for query_id in case.get("react_queries", case.get("required_queries", [])):
        result = await runtime.execute(query_id, {"query_type": "replay"})
        calls.append({"query_id": query_id, "success": result.success})
    return {"calls": runtime.calls, "observations": calls, "state": {"execution": {"evidence": []}}}
