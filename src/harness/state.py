from __future__ import annotations

import os
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


def create_initial_state(query: str, session_id: str, run_id: str, metadata: Optional[Dict[str, Any]] = None) -> HarnessState:
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
        "max_rounds": int((metadata or {}).get("max_rounds", os.getenv("AGENT_MAX_ROUNDS", "3"))),
        "next_node": "understand",
        "error": None,
    }
