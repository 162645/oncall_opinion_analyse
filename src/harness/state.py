from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, TypedDict


class HarnessState(TypedDict, total=False):
    query: str
    run_id: str
    session_id: str
    task: Dict[str, Any]
    context: Dict[str, Any]
    plan: Dict[str, Any]
    execution: Dict[str, Any]
    verification: Dict[str, Any]
    answer: Dict[str, Any]
    trace: List[Dict[str, Any]]
    round: int
    max_rounds: int
    next_node: str
    error: Optional[str]
    budget: Dict[str, Any]


def create_initial_state(query: str, session_id: str, run_id: str, metadata: Optional[Dict[str, Any]] = None) -> HarnessState:
    options = metadata or {}
    return {
        "query": query,
        "session_id": session_id,
        "run_id": run_id,
        "task": {},
        "context": {"metadata": metadata or {}},
        "plan": {"steps": []},
        "execution": {"results": [], "evidence": []},
        "verification": {},
        "answer": {},
        "trace": [],
        "round": 0,
        # Four rounds are required for the full evidence path:
        # baseline/trend → ASN → Prefix24 → Traceroute.
        "max_rounds": int((metadata or {}).get("max_rounds", os.getenv("AGENT_MAX_ROUNDS", "4"))),
        "next_node": "understand",
        "error": None,
        "budget": {"max_queries": int(options.get("max_queries", os.getenv("AGENT_MAX_QUERIES", "8"))),
                   "max_tool_failures": int(options.get("max_tool_failures", os.getenv("AGENT_MAX_TOOL_FAILURES", "3"))),
                   "deadline_seconds": float(options.get("deadline_seconds", os.getenv("AGENT_DEADLINE_SECONDS", "45"))),
                   "started_at": time.time()},
    }
