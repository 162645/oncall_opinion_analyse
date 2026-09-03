from __future__ import annotations

import asyncio
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from src.clickhouse import get_clickhouse_client
from .catalog import catalog_description, compile_sql, get_query_spec


REGION_ALIASES = {
    "乌克兰": "UKRAINE", "ukraine": "UKRAINE", "俄罗斯": "RUSSIA", "russia": "RUSSIA",
    "中国": "CHINA", "china": "CHINA", "美国": "US", "us": "US", "英国": "UK", "uk": "UK",
}


def _event(state: Dict[str, Any], node: str, started: float, status: str = "success", **extra: Any) -> Dict[str, Any]:
    return {"step_id": len(state.get("trace", [])) + 1, "step_type": "harness_node", "agent_name": node,
            "action": node, "duration_ms": int((time.perf_counter() - started) * 1000), "status": status, **extra}


def _region(query: str) -> str:
    lower = query.lower()
    for alias, value in REGION_ALIASES.items():
        if alias.lower() in lower:
            return value
    match = re.search(r"\b([A-Z][A-Z0-9_-]{2,})\b", query)
    return match.group(1).upper() if match else ""


def _time_range(query: str) -> Dict[str, str]:
    hours = 24
    match = re.search(r"最近\s*(\d+)\s*(小时|天)|last\s*(\d+)\s*(hours?|days?)", query, re.I)
    if match:
        number = int(match.group(1) or match.group(3))
        unit = match.group(2) or match.group(4)
        hours = number * (24 if unit.lower().startswith(("天", "day")) else 1)
    end = datetime.now(timezone.utc)
    return {"start_time": (end - timedelta(hours=hours)).isoformat(), "end_time": end.isoformat(), "hours": hours}


async def understand(state: Dict[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    query = state["query"]
    network = any(word in query.lower() for word in ("ping", "延迟", "rtt", "网络", "traceroute", "trace", "路径", "丢包", "asn", "前缀"))
    task = {"kind": "network_analysis" if network else "knowledge", "region": _region(query), "time_range": _time_range(query),
            "metric": "p95" if "p95" in query.lower() else ("p99" if "p99" in query.lower() else "rtt"),
            "goal": "diagnose" if any(w in query.lower() for w in ("异常", "原因", "为什么", "故障")) else "describe"}
    return {"task": task, "next_node": "context", "trace": state.get("trace", []) + [_event(state, "understand", started, reasoning="解析意图、地区、时间范围与指标") ]}


async def context(state: Dict[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    task = state.get("task", {})
    context_data = {"catalog": list(catalog_description()),
                    "recipe": "network_diagnosis_v1" if task.get("kind") == "network_analysis" else "knowledge_answer_v1",
                    "knowledge": [], "data_source": "ClickHouse"}
    if task.get("kind") == "knowledge":
        try:
            from src.knowledge import get_knowledge_service
            search = await asyncio.wait_for(get_knowledge_service().search(state["query"], top_k=3), timeout=2.0)
            context_data["knowledge"] = [{"evidence_id": f"K{i + 1}", "content": item.content[:800],
                                           "score": item.score, "source": item.source,
                                           "metadata": item.metadata} for i, item in enumerate(search.results)]
            context_data["data_source"] = "Qdrant + BM25 + memory fallback"
        except Exception as exc:
            context_data["knowledge_error"] = str(exc)
    return {"context": context_data, "next_node": "planner", "trace": state.get("trace", []) + [_event(state, "context", started, reasoning="装载查询目录、分析配方与数据源约束") ]}


def _steps(task: Dict[str, Any], execution: Dict[str, Any]) -> List[Dict[str, Any]]:
    if task.get("kind") != "network_analysis":
        return []
    region = task.get("region")
    if not region:
        return []
    tr = task["time_range"]
    previous = execution.get("evidence", [])
    if previous:
        # A re-plan only retries unavailable catalog items. It never repeats
        # successful queries, which keeps recovery bounded and auditable.
        failed = {item.get("query_id") for item in previous if item.get("status") != "observed"}
        if not failed:
            return []
    else:
        failed = set()
    steps = [{"query_id": "ping.summary", "params": {"query_type": "ping_stats", "region": region, **tr}},
             {"query_id": "ping.trend", "params": {"query_type": "ping_trend", "region": region, "interval": "hour", **tr}}]
    if task.get("goal") == "diagnose" or any("anomaly" in str(x).lower() for x in execution.get("evidence", [])):
        steps.append({"query_id": "ping.by_asn", "params": {"query_type": "ping_stats", "region": region, "group_by": ["ip_asn"], **tr}})
        steps.append({"query_id": "trace.paths", "params": {"query_type": "trace_stats", "region": region, **tr}})
    return [step for step in steps if not failed or step["query_id"] in failed]


def _chart_specs(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    charts = []
    for item in evidence:
        data = item.get("data") or {}
        if item.get("status") != "observed":
            continue
        if item.get("query_id") == "ping.trend":
            rows = data.get("trend_data", [])
            if rows:
                charts.append({"chart_id": "C1", "evidence_ids": [item["evidence_id"]], "chart_type": "line",
                               "title": "Ping RTT 趋势", "x_axis": [str(row.get("time")) for row in rows],
                               "y_axis_name": "RTT (ms)", "series": [
                                   {"name": "Median RTT", "data": [row.get("median_rtt") for row in rows]},
                                   {"name": "P95 RTT", "data": [row.get("p95_rtt") for row in rows]},
                               ]})
        elif item.get("query_id") == "ping.by_asn":
            rows = (data.get("statistics") or [])[:10]
            if rows:
                charts.append({"chart_id": "C2", "evidence_ids": [item["evidence_id"]], "chart_type": "bar",
                               "title": "AS 维度 P95 RTT 对比", "x_axis": [f"AS{row.get('ip_asn')}" for row in rows],
                               "y_axis_name": "RTT (ms)", "series": [{"name": "P95 RTT", "data": [row.get("p95_rtt") for row in rows]}]})
    return charts


async def planner(state: Dict[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    steps = _steps(state.get("task", {}), state.get("execution", {}))
    current_round = int(state.get("round", 0)) + 1
    return {"round": current_round, "plan": {"plan_id": f"network-v1-r{current_round}", "steps": steps, "round": current_round},
            "next_node": "executor", "trace": state.get("trace", []) + [_event(state, "planner", started, reasoning="只输出受控 query_id 与类型化参数，不生成自由 SQL") ]}


async def executor(state: Dict[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    previous_execution = state.get("execution", {})
    results = [item for item in previous_execution.get("results", []) if item.get("success")]
    evidence = [item for item in previous_execution.get("evidence", []) if item.get("status") == "observed"]
    for step in state.get("plan", {}).get("steps", []):
        query_id, params = step["query_id"], step["params"]
        begin = time.perf_counter()
        try:
            # Catalog validation is the first SQL safety boundary. The model
            # cannot introduce an arbitrary tool or query type here.
            spec = get_query_spec(query_id)
            if params.get("query_type") != spec.tool_query_type:
                raise ValueError(f"query_type mismatch for {query_id}")
            sql, bindings = compile_sql(query_id, params)
            timeout_seconds = float(os.getenv("AGENT_TOOL_TIMEOUT_SECONDS", "8"))
            # The legacy ClickHouse client is synchronous internally. Move it
            # off the event loop so a dead database cannot freeze the graph.
            rows = await asyncio.wait_for(
                asyncio.to_thread(lambda: get_clickhouse_client().execute(sql, bindings)),
                timeout=timeout_seconds,
            )
            records = [dict(zip(spec.columns, row)) for row in rows]
            data = {spec.result_key: records}
            item = {"query_id": query_id, "success": True, "data": data, "error": None,
                    "duration_ms": int((time.perf_counter() - begin) * 1000)}
        except Exception as exc:
            item = {"query_id": query_id, "success": False, "data": None, "error": str(exc),
                    "duration_ms": int((time.perf_counter() - begin) * 1000)}
        results.append(item)
        evidence.append({"evidence_id": f"E{len(evidence) + 1}", "query_id": query_id, "status": "observed" if item["success"] else "unavailable",
                         "data": item["data"], "error": item["error"]})
    execution = {"results": results, "evidence": evidence}
    return {"execution": execution, "next_node": "verifier", "trace": state.get("trace", []) + [_event(state, "executor", started, reasoning=f"执行 {len(results)} 个目录查询并记录证据") ]}


async def verifier(state: Dict[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    evidence = state.get("execution", {}).get("evidence", [])
    successful = [item for item in evidence if item.get("status") == "observed"]
    has_errors = any(item.get("status") != "observed" for item in evidence)
    if not evidence and state.get("task", {}).get("kind") == "knowledge":
        verdict, score = "PASS", 0.55
    elif successful and not has_errors:
        verdict, score = "PASS", 0.9
    elif successful:
        verdict, score = "PARTIAL", 0.55
    else:
        verdict, score = "ABSTAIN", 0.0
    verification = {"verdict": verdict, "score": score, "successful_evidence": len(successful), "total_evidence": len(evidence),
                    "reason": "证据足够" if verdict == "PASS" else "数据源未返回完整证据，回答将明确标注限制"}
    next_node = "synthesizer"
    return {"verification": verification, "next_node": next_node, "trace": state.get("trace", []) + [_event(state, "verifier", started, reasoning=f"证据校验结果: {verdict}") ]}


async def synthesizer(state: Dict[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    task, verification = state.get("task", {}), state.get("verification", {})
    evidence = state.get("execution", {}).get("evidence", [])
    if task.get("kind") != "network_analysis":
        knowledge = state.get("context", {}).get("knowledge", [])
        if knowledge:
            answer = "基于知识库检索结果：\n\n" + "\n\n".join(f"[{item['evidence_id']}] {item['content']}" for item in knowledge)
        else:
            answer = "知识库没有返回可引用内容。若需要基于测量数据分析，请指定地区、时间范围和指标。"
    elif verification.get("verdict") == "ABSTAIN":
        answer = f"暂时无法基于真实数据给出结论：{verification.get('reason')}。请检查 ClickHouse 连接、地区表名及时间范围后重试。"
    else:
        answer = f"已完成 {task.get('region')} 的网络测量分析。证据状态为 {verification.get('verdict')}，有效证据 {verification.get('successful_evidence')}/{verification.get('total_evidence')}。"
        if verification.get("verdict") != "PASS":
            answer += " 部分查询失败，因此不对缺失数据做推断。"
    generated_by = "deterministic_synthesizer"
    if (os.getenv("HARNESS_LLM_ENABLED", "false").lower() == "true"
            and verification.get("verdict") in {"PASS", "PARTIAL"} and evidence):
        try:
            from src.llm import get_llm_gateway
            prompt = ("你是网络测量分析助手。只能使用给定 evidence，不能补造数据；每个事实后标注 evidence_id。"
                      "如果证据不支持结论，明确说不知道。\nEvidence:\n" + json.dumps(evidence, ensure_ascii=False, default=str)[:12000]
                      + "\n请用简洁中文回答用户问题：" + state["query"])
            llm_result = await asyncio.wait_for(get_llm_gateway().generate(prompt), timeout=10.0)
            if llm_result.content.strip():
                answer, generated_by = llm_result.content.strip(), "llm_synthesizer"
        except Exception:
            # LLM is an enhancement, never a dependency of the evidence path.
            pass
    charts = _chart_specs(evidence)
    context_evidence = state.get("context", {}).get("knowledge", [])
    all_evidence = evidence + [{"evidence_id": item["evidence_id"], "query_id": "knowledge.search", "status": "observed",
                                "data": {"content": item["content"], "score": item["score"]}} for item in context_evidence]
    answer_data = {"answer": answer, "charts": charts, "evidence": all_evidence,
                   "generated_by": generated_by,
                   "claims": [{"claim_id": "CL1", "evidence_ids": [item["evidence_id"] for item in all_evidence]}] if all_evidence else [],
                   "verdict": verification.get("verdict")}
    return {"answer": answer_data, "next_node": "end", "trace": state.get("trace", []) + [_event(state, "synthesizer", started, reasoning="仅基于证据账本生成回答与图表数据") ]}
