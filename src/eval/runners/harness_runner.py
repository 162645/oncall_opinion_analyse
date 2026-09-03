from typing import Any, Dict

from src.harness.graph import EvidenceDrivenHarness
from src.eval.replay_runtime import ReplayRuntime


async def run_harness_replay(case: Dict[str, Any], fixture: Dict[str, Any]) -> Dict[str, Any]:
    runtime = ReplayRuntime(fixture)
    result = await EvidenceDrivenHarness(runtime=runtime).execute(case["query"], session_id=f"replay-{case['case_id']}")
    return {"state": result.state, "calls": runtime.calls, "success": result.success}
