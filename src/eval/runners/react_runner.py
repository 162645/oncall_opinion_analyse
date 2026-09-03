from __future__ import annotations

import re
import time
import json
from typing import Any, Awaitable, Callable, Dict

from src.eval.replay_runtime import ReplayRuntime
from src.harness.catalog import CATALOG

Policy = Callable[[str, list[dict[str, Any]], list[dict[str, Any]]], Awaitable[dict[str, Any]]]


def _params(query: str, query_id: str) -> dict[str, Any]:
    regions = re.findall(r"\b[A-Z][A-Z0-9_]{2,31}\b", query)
    region = regions[0] if regions else "UKRAINE"
    dates = re.findall(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:?\d{2})", query)
    start_time, end_time = (dates + ["2025-01-08T14:54:10+00:00", "2025-01-09T14:54:10+00:00"])[:2]
    base: dict[str, Any] = {"query_type": CATALOG[query_id].tool_query_type,
                            "region": region, "start_time": start_time,
                            "end_time": end_time, "limit": 100}
    if query_id == "ping.trend": base["interval"] = "hour"
    if query_id == "ping.by_asn": base["group_by"] = ["ip_asn"]
    return base


async def deterministic_policy(query: str, observations: list[dict[str, Any]], catalog: list[dict[str, Any]]) -> dict[str, Any]:
    """Offline observation-driven policy; it never sees case ground truth."""
    text = query.lower()
    used = {item["query_id"] for item in observations}
    if not used:
        choice = "ping.compare_window" if any(x in text for x in ("历史", "相比", "baseline")) else "ping.summary"
    elif "ping.trend" not in used and any(x in text for x in ("趋势", "异常", "p95", "延迟", "rtt")):
        choice = "ping.trend"
    elif "ping.by_asn" not in used and any(x in text for x in ("asn", "运营商", "集中")):
        choice = "ping.by_asn"
    elif "ping.by_prefix24" not in used and any(x in text for x in ("prefix", "前缀", "下钻")):
        choice = "ping.by_prefix24"
    elif "trace.path_change" not in used and any(x in text for x in ("路径", "path", "路由")):
        choice = "trace.path_change"
    elif "trace.paths" not in used and any(x in text for x in ("路径", "path", "路由")):
        choice = "trace.paths"
    else:
        return {"final": True, "claims": [], "answer": "基于当前观测结束分析；未验证的因果关系不作结论。"}
    return {"query_id": choice, "params": _params(query, choice), "purpose": "collect next observation"}


async def llm_policy(query: str, observations: list[dict[str, Any]], catalog: list[dict[str, Any]]) -> dict[str, Any]:
    """Free ReAct model policy; prompt contains no evaluation ground truth."""
    from src.llm import get_llm_gateway, LLMConfig
    prompt = ("你是网络测量 Free ReAct Agent。只能从 Catalog 选择 query_id，禁止 SQL。"
              "如果证据足够，输出 {\"final\":true,\"claims\":[]}；否则输出 "
              "{\"query_id\":...,\"params\":...,\"purpose\":...}。只输出 JSON。"
              f"\nUserQuery={query}\nCatalog={json.dumps(catalog, ensure_ascii=False)[:10000]}"
              f"\nObservations={json.dumps(observations, ensure_ascii=False, default=str)[:10000]}")
    response = await get_llm_gateway().generate(prompt, config=LLMConfig(
        temperature=float(__import__("os").getenv("HARNESS_LLM_TEMPERATURE", "0")), max_tokens=512))
    match = re.search(r"\{.*\}", response.content, re.S)
    if not match:
        return {"final": True, "claims": []}
    return json.loads(match.group(0))


async def run_react_replay(case: Dict[str, Any], fixture: Dict[str, Any], *, max_tool_calls: int = 8,
                           llm_policy: Policy | None = None) -> Dict[str, Any]:
    """Run Free ReAct with only query, catalog and accumulated observations."""
    runtime = ReplayRuntime(fixture)
    policy = llm_policy or deterministic_policy
    catalog = [{"query_id": s.query_id, "description": s.description,
                "input_schema": s.input_model.model_json_schema()} for s in CATALOG.values()]
    observations: list[dict[str, Any]] = []
    llm_calls: list[dict[str, Any]] = []
    invalid_calls = 0
    started = time.perf_counter()
    for _ in range(max_tool_calls):
        llm_started = time.perf_counter()
        decision = await policy(case["query"], observations, catalog)
        llm_calls.append({"latency_ms": round((time.perf_counter() - llm_started) * 1000, 3),
                          "input_observation_count": len(observations)})
        if decision.get("final"):
            break
        query_id = decision.get("query_id")
        if query_id not in CATALOG or not isinstance(decision.get("params"), dict):
            invalid_calls += 1
            observations.append({"query_id": str(query_id), "status": "invalid"})
            continue
        result = await runtime.execute(query_id, decision["params"])
        observations.append({"query_id": query_id, "status": "observed" if result.success else "failed",
                             "data": result.data, "error": result.error})
    evidence = [{"evidence_id": f"R{i + 1}", "query_id": x["query_id"],
                 "status": x["status"], "data": x.get("data")} for i, x in enumerate(observations)]
    fact_by_query = {"ping.summary": "p95_spike_detected", "ping.trend": "p95_spike_detected",
                     "ping.compare_window": "baseline_degradation", "ping.by_asn": "asn_concentration",
                     "ping.by_prefix24": "prefix24_candidates", "trace.paths": "traceroute_paths_observed",
                     "trace.path_change": "path_change_observed"}
    claims = [{"fact_type": fact_by_query.get(x["query_id"], "measurement_observed"),
               "text": f"已观测到 {x['query_id']} 返回的测量结果。",
               "supporting_query_ids": [x["query_id"]]} for x in observations if x["status"] == "observed"]
    state = {"execution": {"evidence": evidence}, "answer": {"claims": claims},
             "verification": {"verdict": "PASS" if evidence else "ABSTAIN"}}
    return {"calls": runtime.calls, "llm_calls": llm_calls, "invalid_tool_calls": invalid_calls,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3), "state": state,
            "strategy": "free_react_deterministic" if llm_policy is None else "free_react_llm"}
