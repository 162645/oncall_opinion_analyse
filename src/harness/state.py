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
    reasoning_context: Dict[str, Any]
    llm_usage: Dict[str, Any]
    replan_history: List[Dict[str, Any]]


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
                   "max_llm_calls": int(options.get("max_llm_calls", os.getenv("AGENT_MAX_LLM_CALLS", "12"))),
                   "max_llm_tokens": int(options.get("max_llm_tokens", os.getenv("AGENT_MAX_LLM_TOKENS", "12000"))),
                   "started_at": time.time()},
        "reasoning_context": {"current_goal": "", "known_facts_summary": [], "unknowns": [],
                               "current_hypotheses": [], "last_decision_reason": ""},
        "llm_usage": {"calls_used": 0, "tokens_in": 0, "tokens_out": 0, "estimated_cost": 0.0, "calls": []},
        "replan_history": [],
    }
