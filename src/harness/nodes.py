from __future__ import annotations

import asyncio
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from src.clickhouse import get_clickhouse_client
from src.runtime import PermissionLevel, ToolDefinition, ToolRuntime
from .catalog import CATALOG, catalog_description, compile_sql, get_query_spec
from .ledger import EvidenceLedger
from .mcp_adapter import CatalogMCPAdapter
from .models import AnalysisPlan, TaskSpec, Verification, to_dict


def _catalog_runtime() -> ToolRuntime:
    runtime = ToolRuntime()
    for query_id, spec in CATALOG.items():
        def handler(_query_id=query_id, **arguments):
            expected_type = spec_for(_query_id).tool_query_type
            if arguments.get("query_type") != expected_type:
                raise ValueError(f"query_type mismatch for {_query_id}")
            sql, bindings = compile_sql(_query_id, arguments)
            # clickhouse-driver binds DateTime64 reliably as datetime objects;
            # API/LLM boundaries may use ISO-8601 strings.
            for key in ("start_time", "end_time", "baseline_start", "baseline_end"):
                if isinstance(bindings.get(key), str):
                    try:
                        bindings[key] = datetime.fromisoformat(bindings[key].replace("Z", "+00:00"))
                    except ValueError:
                        # Unit tests and custom adapters may use symbolic bounds.
                        pass
            rows = get_clickhouse_client().execute(sql, bindings)
            query_spec = spec_for(_query_id)
            typed_rows = [query_spec.output_model.model_validate(dict(zip(query_spec.columns, row))).model_dump(mode="json")
                          for row in rows]
            return {query_spec.result_key: typed_rows}

        runtime.register(ToolDefinition(
            name=query_id,
            description=spec.description,
            parameters=spec.input_model.model_json_schema(),
            handler=handler, permission=PermissionLevel.READ,
            timeout_seconds=float(os.getenv("AGENT_TOOL_TIMEOUT_SECONDS", "8")),
        ))
    return runtime


def spec_for(query_id: str):
    return CATALOG[query_id]


def _latest_evidence(ledger: EvidenceLedger, query_id: str) -> Dict[str, Any] | None:
    items = [item for item in ledger.all() if item.get("query_id") == query_id]
    return items[-1] if items else None


def _retryable(item: Dict[str, Any]) -> bool:
    if item.get("status") == "observed":
        return False
    return item.get("error_kind") in {None, "timeout", "transient"}


def _asn_concentration(ledger: EvidenceLedger) -> tuple[bool, List[Dict[str, Any]]]:
    item = _latest_evidence(ledger, "ping.by_asn")
    if not item or item.get("status") != "observed":
        return False, []
    rows = list((item.get("data") or {}).get("statistics", []))
    rows = [row for row in rows if row.get("valid_samples") is None or float(row.get("valid_samples") or 0) >= 10]
    rows.sort(key=lambda row: float(row.get("p95_rtt") or 0), reverse=True)
    summary = _latest_evidence(ledger, "ping.summary")
    summary_rows = (summary or {}).get("data", {}).get("statistics", [])
    overall = float((summary_rows[0] if summary_rows else {}).get("p95_rtt") or 0)
    if not overall and rows:
        values = [float(row.get("p95_rtt") or 0) for row in rows]
        overall = sum(values) / len(values)
    concentrated = bool(rows and overall > 0 and float(rows[0].get("p95_rtt") or 0) > overall * 1.2)
    return concentrated, rows


def _top_prefix(ledger: EvidenceLedger) -> str:
    item = _latest_evidence(ledger, "ping.by_prefix24")
    rows = list(((item or {}).get("data") or {}).get("statistics", []))
    if not rows:
        return ""
    rows.sort(key=lambda row: float(row.get("p95_rtt") or 0), reverse=True)
    return str(rows[0].get("prefix24") or "")


def _top_asn(ledger: EvidenceLedger) -> int | None:
    concentrated, rows = _asn_concentration(ledger)
    if not rows:
        return None
    value = rows[0].get("ip_asn")
    return int(value) if value is not None else None


def _rtt_anomaly_buckets(ledger: EvidenceLedger, rows: List[Dict[str, Any]]) -> List[str]:
    values = [float(row.get("p95_rtt") or 0) for row in rows]
    if not values:
        return []
    baseline = sorted(values)[len(values) // 2]
    compare = _latest_evidence(ledger, "ping.compare_window")
    comparison = ((compare or {}).get("data") or {}).get("comparison", [])
    if comparison and comparison[0].get("baseline_p95"):
        baseline = float(comparison[0]["baseline_p95"])
    threshold = baseline * (1.2 if comparison else 1.5)
    return [str(row.get("time_bucket")) for row in rows if float(row.get("p95_rtt") or 0) > threshold]


REGION_ALIASES = {
    "乌克兰": "UKRAINE", "ukraine": "UKRAINE", "俄罗斯": "RUSSIA", "russia": "RUSSIA",
    "中国": "CHINA", "china": "CHINA", "美国": "US", "us": "US", "英国": "UK", "uk": "UK",
}


def _event(state: Dict[str, Any], node: str, started: float, status: str = "success", **extra: Any) -> Dict[str, Any]:
    return {"step_id": len(state.get("trace", [])) + 1, "step_type": "harness_node", "agent_name": node,
            "action": node, "duration_ms": int((time.perf_counter() - started) * 1000), "status": status, **extra}


def _region(query: str) -> str | None:
    lower = query.lower()
    for alias, value in REGION_ALIASES.items():
        if alias.lower() in lower:
            return value
    excluded = {"P50", "P90", "P95", "P99", "RTT", "ASN", "IP", "SQL", "HTTP", "TCP", "UDP"}
    match = re.search(r"\b([A-Z][A-Z0-9_-]{2,})\b", query)
    candidate = match.group(1).upper() if match else None
    return candidate if candidate not in excluded else None


def _time_range(query: str) -> Dict[str, str]:
    explicit = re.findall(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:?\d{2})", query)
    if len(explicit) >= 2:
        start_time, end_time = explicit[:2]
        try:
            start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            return {"start_time": start.isoformat(), "end_time": end.isoformat(),
                    "hours": max(1, int((end - start).total_seconds() / 3600))}
        except ValueError:
            pass
    hours = 24
    match = re.search(r"最近\s*(\d+)\s*(小时|天)|last\s*(\d+)\s*(hours?|days?)", query, re.I)
    if match:
        number = int(match.group(1) or match.group(3))
        unit = match.group(2) or match.group(4)
        hours = number * (24 if unit.lower().startswith(("天", "day")) else 1)
    end = datetime.now(timezone.utc)
    return {"start_time": (end - timedelta(hours=hours)).isoformat(), "end_time": end.isoformat(), "hours": hours}


async def _llm_task_spec(state: Dict[str, Any], draft: Dict[str, Any]) -> Dict[str, Any] | None:
    """Structured fallback for ambiguous language; rules remain the fast path."""
    try:
        from src.llm import get_llm_gateway
        prompt = (
            "将用户问题转换成严格 JSON，不要 Markdown。只允许字段：kind(network_analysis/knowledge), "
            "goal(describe/diagnose), region(大写地区标识或空字符串), metric(rtt/p95/p99), "
            "planning_mode(recipe/long_tail), time_range(start_time,end_time)。"
            "不要生成 SQL，不要添加字段。若无法确定则保留规则草稿字段。"
            f"\n用户问题：{state['query']}\n规则草稿：{json.dumps(draft, ensure_ascii=False)}"
        )
        response = await asyncio.wait_for(get_llm_gateway().generate(prompt), timeout=5.0)
        candidate = _extract_json_object(response.content)
        if not isinstance(candidate, dict):
            return None
        kind = candidate.get("kind")
        if kind not in {"network_analysis", "knowledge"}:
            return None
        region = str(candidate.get("region") or "").upper()
        if region and not re.fullmatch(r"[A-Z][A-Z0-9_]{1,31}", region):
            return None
        time_range = candidate.get("time_range") or {}
        if not time_range.get("start_time") or not time_range.get("end_time"):
            return None
        return {"kind": kind, "goal": candidate.get("goal") if candidate.get("goal") in {"describe", "diagnose"} else draft["goal"],
                "region": region, "time_range": {"start_time": str(time_range["start_time"]),
                "end_time": str(time_range["end_time"]), "hours": draft["time_range"].get("hours", 24)},
                "metric": candidate.get("metric") if candidate.get("metric") in {"rtt", "p95", "p99"} else draft["metric"],
                "planning_mode": candidate.get("planning_mode") if candidate.get("planning_mode") in {"recipe", "long_tail"} else draft.get("planning_mode", "recipe")}
    except Exception:
        return None


async def understand(state: Dict[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    query = state["query"]
    network = any(word in query.lower() for word in ("ping", "延迟", "rtt", "网络", "traceroute", "trace", "路径", "丢包", "asn", "前缀"))
    complexity_signals = sum(1 for signal in ("对比", "比较", "过去", "白天", "凌晨", "移动", "运营商", "previous", "compare")
                             if signal in query.lower())
    task = {"kind": "network_analysis" if network else "knowledge", "region": _region(query), "time_range": _time_range(query),
            "metric": "p95" if "p95" in query.lower() else ("p99" if "p99" in query.lower() else "rtt"),
            "goal": "diagnose" if any(w in query.lower() for w in ("异常", "原因", "为什么", "故障")) else "describe",
            "planning_mode": "long_tail" if complexity_signals >= 2 else "recipe",
            "needs_baseline": any(word in query.lower() for word in ("变差", "恶化", "相比", "之前", "历史", "baseline", "compare"))}
    low_confidence = not task["region"] or (task["kind"] == "network_analysis" and complexity_signals >= 2)
    if low_confidence and os.getenv("HARNESS_UNDERSTAND_ENABLED", os.getenv("HARNESS_LLM_ENABLED", "false")).lower() == "true":
        enriched = await _llm_task_spec(state, task)
        if enriched:
            task = enriched
    # Validate the node boundary before state enters Context.
    task = to_dict(TaskSpec.model_validate(task))
    return {"task": task, "next_node": "context", "trace": state.get("trace", []) + [_event(state, "understand", started, reasoning="解析意图、地区、时间范围与指标") ]}


async def context(state: Dict[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    task = state.get("task", {})
    recipe = "network_diagnosis_v1" if task.get("kind") == "network_analysis" else "knowledge_answer_v1"
    context_data = {"catalog": list(catalog_description()),
                    "recipe": recipe,
                    "recipe_hints": {"name": recipe, "stages": ["summary", "trend", "asn", "prefix24", "trace"]
                                     if task.get("kind") == "network_analysis" else ["retrieve", "cite"]},
                    "semantic_hints": ["measurement evidence is authoritative", "context evidence is non-causal background"],
                    "knowledge": [], "graph_context": [], "skill_matches": [], "data_source": "ClickHouse"}
    # Network investigations also receive semantic context. Retrieval is an
    # input to planning, never a substitute for measured evidence.
    if task.get("kind") in {"knowledge", "network_analysis"}:
        try:
            from src.knowledge import get_knowledge_service
            retrieval_query = state["query"] if task.get("kind") == "knowledge" else (
                f"主动网络测量 {task.get('region', '')} {task.get('metric', 'rtt')} "
                f"{task.get('goal', 'describe')}：{state['query']}"
            )
            search = await asyncio.wait_for(get_knowledge_service().search(retrieval_query, top_k=3), timeout=2.0)
            context_data["knowledge"] = [{"evidence_id": f"K{i + 1}", "content": item.content[:800],
                                           "score": item.score, "source": item.source,
                                           "metadata": item.metadata} for i, item in enumerate(search.results)]
            context_data["data_source"] = "ClickHouse + Qdrant/BM25/Neo4j knowledge context"
        except Exception as exc:
            context_data["knowledge_error"] = str(exc)
        try:
            from src.skill import get_skill_service
            matches = await asyncio.wait_for(get_skill_service().search(state["query"], top_k=3), timeout=1.0)
            context_data["skill_matches"] = [{"name": item.skill.name, "score": item.score,
                                               "reason": item.match_reason} for item in matches]
        except Exception as exc:
            context_data["skill_error"] = str(exc)
        try:
            from src.knowledge.graph.query import GraphQuery
            from src.knowledge import get_knowledge_service
            graph = getattr(get_knowledge_service(), "graph", None)
            if graph:
                graph_matches = await asyncio.wait_for(asyncio.to_thread(
                    GraphQuery(graph).find_similar_faults,
                    ["latency", "rtt", "path", "timeout"], 3,
                ), timeout=1.0)
                context_data["graph_context"] = graph_matches
        except Exception as exc:
            context_data["graph_error"] = str(exc)
    return {"context": context_data, "next_node": "planner", "trace": state.get("trace", []) + [_event(state, "context", started, reasoning="装载查询目录、分析配方与数据源约束") ]}


def _steps(task: Dict[str, Any], execution: Dict[str, Any], verification: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    if task.get("kind") != "network_analysis":
        return []
    region = task.get("region")
    if not region:
        return []
    tr = task["time_range"]
    ledger = EvidenceLedger(execution.get("evidence", []))
    latest = {item.get("query_id"): item for item in ledger.all()}
    retryable_failed = {query_id for query_id, item in latest.items() if item.get("status") != "observed" and _retryable(item)}
    base = {"region": region, "start_time": tr["start_time"], "end_time": tr["end_time"]}
    missing_evidence = (verification or {}).get("missing_evidence", [])
    if missing_evidence:
        requested = [item.get("query_id") if isinstance(item, dict) else item for item in missing_evidence]
        prefix = _top_prefix(ledger)
        asn = _top_asn(ledger)
        return [{"query_id": query_id, "params": {"query_type": CATALOG[query_id].tool_query_type,
                                                    **({"interval": "hour"} if query_id == "ping.trend" else {}),
                                                    **({"prefix24": prefix} if query_id in {"trace.paths", "trace.path_change"} else {}),
                                                    **({"asn": asn} if query_id == "ping.by_prefix24" and asn else {}), **base}}
                for query_id in requested if query_id in CATALOG and not ledger.has(query_id)
                and (not _latest_evidence(ledger, query_id) or _retryable(_latest_evidence(ledger, query_id)))]
    if not execution.get("evidence"):
        initial = [{"query_id": "ping.summary", "params": {"query_type": "ping_stats", **base}},
                   {"query_id": "ping.trend", "params": {"query_type": "ping_trend", "interval": "hour", **base}}]
        if task.get("needs_baseline"):
            initial.insert(0, {"query_id": "ping.compare_window", "params": {"query_type": "ping_compare", **base}})
        return initial
    if retryable_failed:
        return [{"query_id": query_id, "params": {"query_type": CATALOG[query_id].tool_query_type,
                                                       **({"interval": "hour"} if query_id == "ping.trend" else {}), **base}}
                for query_id in retryable_failed if query_id in CATALOG]
    if task.get("goal") != "diagnose":
        return []
    if not ledger.has("ping.by_asn"):
        return [{"query_id": "ping.by_asn", "params": {"query_type": "ping_stats", "group_by": ["ip_asn"], **base}}]
    concentrated, asn_rows = _asn_concentration(ledger)
    if concentrated and not ledger.has("ping.by_prefix24"):
        return [{"query_id": "ping.by_prefix24", "params": {"query_type": "ping_stats", "asn": _top_asn(ledger), **base}}]
    if ledger.has("ping.by_prefix24") and not ledger.has("trace.paths"):
        return [{"query_id": "trace.paths", "params": {"query_type": "trace_stats", "prefix24": _top_prefix(ledger), **base}}]
    return []


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
                               "title": "Ping RTT 趋势", "x_axis": [str(row.get("time_bucket")) for row in rows],
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


def _extract_json_object(content: str) -> Any:
    """Read a JSON value from a model response without trusting prose around it."""
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start, end = content.find("["), content.rfind("]")
        if start < 0 or end <= start:
            return None
        try:
            return json.loads(content[start:end + 1])
        except json.JSONDecodeError:
            return None


def _renderer_grounded(source: str, rendered: str) -> bool:
    """Preserve every numeric/entity token from a verified claim at runtime."""
    tokens = re.findall(r"\d+(?:\.\d+)?|AS\d+|\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}|[A-Z]{2,}", source)
    return all(token in rendered for token in tokens)


async def _llm_plan(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Ask an LLM for a plan, then accept only catalog-valid primitives."""
    try:
        from src.llm import get_llm_gateway
        task = state.get("task", {})
        context = state.get("context", {})
        evidence = state.get("execution", {}).get("evidence", [])
        prompt = (
            "你是网络测量分析 Planner。只输出 JSON 数组，不要 Markdown。"
            "每项必须是 {query_id, params, purpose}，query_id 只能来自 Catalog；禁止 SQL、禁止新增工具。"
            f"\nTaskSpec={json.dumps(task, ensure_ascii=False, default=str)}"
            f"\nCatalog={json.dumps(context.get('catalog', []), ensure_ascii=False)}"
            f"\nRecipeHints={json.dumps(context.get('recipe_hints', {}), ensure_ascii=False)}"
            f"\nSkillMatches={json.dumps(context.get('skill_matches', [])[:2], ensure_ascii=False, default=str)}"
            f"\nKnowledgeHints={json.dumps(context.get('knowledge', [])[:3], ensure_ascii=False, default=str)[:4000]}"
            f"\nGraphHints={json.dumps(context.get('graph_context', [])[:3], ensure_ascii=False, default=str)}"
            f"\nEvidence={json.dumps(evidence, ensure_ascii=False, default=str)[:8000]}"
            "\n请选择当前最有价值且尚未成功执行的查询。"
        )
        response = await asyncio.wait_for(get_llm_gateway().generate(prompt), timeout=5.0)
        proposed = _extract_json_object(response.content)
        if not isinstance(proposed, list):
            return []
        observed = {item.get("query_id") for item in evidence if item.get("status") == "observed"}
        safe = []
        for item in proposed[:4]:
            if not isinstance(item, dict) or item.get("query_id") not in CATALOG:
                continue
            query_id = item["query_id"]
            if query_id in observed:
                continue
            params = dict(item.get("params") or {})
            params.setdefault("region", task.get("region", ""))
            params.setdefault("start_time", task.get("time_range", {}).get("start_time"))
            params.setdefault("end_time", task.get("time_range", {}).get("end_time"))
            params["query_type"] = CATALOG[query_id].tool_query_type
            if query_id == "ping.trend":
                params.setdefault("interval", "hour")
            # Compile now as a plan guard; no unchecked plan can reach Executor.
            compile_sql(query_id, params)
            safe.append({"query_id": query_id, "params": params,
                         "purpose": str(item.get("purpose") or "collect evidence")[:200]})
        return safe
    except Exception:
        return []


async def planner(state: Dict[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    task = state.get("task", {})
    verification = state.get("verification", {})
    steps = _steps(task, state.get("execution", {}), verification)
    source, rationale = "recipe", "优先使用经过验证的网络分析配方"
    # Long-tail planning is optional and guarded: the model may choose only
    # catalog primitives. If it fails validation or is unavailable, the
    # deterministic recipe remains the safe fallback.
    if not verification.get("missing_evidence") and task.get("planning_mode") == "long_tail" \
            and os.getenv("HARNESS_PLANNER_ENABLED", os.getenv("HARNESS_LLM_ENABLED", "false")).lower() == "true":
        llm_steps = await _llm_plan(state)
        if llm_steps:
            steps, source, rationale = llm_steps, "llm_guarded", "长尾问题由 LLM 选择 Query Primitive，经过 Plan Guard 校验"
    budget = state.get("budget", {})
    used_queries = len(state.get("execution", {}).get("evidence", []))
    remaining_queries = max(0, int(budget.get("max_queries", 8)) - used_queries)
    steps = steps[:remaining_queries]
    current_round = int(state.get("round", 0)) + 1
    plan = AnalysisPlan(plan_id=f"network-v1-r{current_round}", round=current_round,
                        steps=steps, source=source, rationale=rationale)
    return {"round": current_round, "plan": to_dict(plan),
            "next_node": "executor", "trace": state.get("trace", []) + [_event(state, "planner", started,
            reasoning=f"{rationale}；只输出受控 query_id 与类型化参数") ]}


async def _execute_with_runtime(state: Dict[str, Any], runtime: ToolRuntime) -> Dict[str, Any]:
    started = time.perf_counter()
    previous_execution = state.get("execution", {})
    results = list(previous_execution.get("results", []))
    evidence = list(previous_execution.get("evidence", []))
    mcp = CatalogMCPAdapter(runtime)
    for step in state.get("plan", {}).get("steps", []):
        query_id, params = step["query_id"], step["params"]
        begin = time.perf_counter()
        try:
            # Catalog validation is the first SQL safety boundary. The model
            # cannot introduce an arbitrary tool or query type here.
            spec = get_query_spec(query_id)
            if params.get("query_type") != spec.tool_query_type:
                raise ValueError(f"query_type mismatch for {query_id}")
            timeout_seconds = float(os.getenv("AGENT_TOOL_TIMEOUT_SECONDS", "8"))
            # The legacy ClickHouse client is synchronous internally. Move it
            # off the event loop so a dead database cannot freeze the graph.
            runtime_result = await asyncio.wait_for(
                asyncio.to_thread(lambda: asyncio.run(mcp.call_tool(query_id, params, trace_id=state.get("run_id", "")))),
                timeout=timeout_seconds,
            )
            item = {"query_id": query_id, "success": runtime_result.success, "data": runtime_result.data,
                    "error": runtime_result.error, "error_kind": runtime_result.error_kind.value if runtime_result.error_kind else None,
                    "attempts": runtime_result.attempts,
                    "duration_ms": int((time.perf_counter() - begin) * 1000)}
        except Exception as exc:
            item = {"query_id": query_id, "success": False, "data": None, "error": str(exc),
                    "error_kind": "timeout" if isinstance(exc, (TimeoutError, asyncio.TimeoutError)) else "permanent", "attempts": 1,
                    "duration_ms": int((time.perf_counter() - begin) * 1000)}
        results.append(item)
        prior_attempts = sum(1 for old in evidence if old.get("query_id") == query_id)
        evidence.append({"evidence_id": f"E{len(evidence) + 1}", "query_id": query_id, "status": "observed" if item["success"] else "unavailable",
                         "kind": "measurement", "data": item["data"], "error": item["error"], "source": "clickhouse",
                         "params": params, "observed_at": datetime.now(timezone.utc).isoformat(),
                         "trace_id": state.get("run_id", ""), "error_kind": item.get("error_kind"),
                         "attempts": item.get("attempts", 0), "attempt": prior_attempts + 1})
    execution = {"results": results, "evidence": evidence}
    return {"execution": execution, "next_node": "verifier", "trace": state.get("trace", []) + [_event(state, "executor", started, reasoning=f"执行 {len(results)} 个目录查询并记录证据") ]}


async def executor(state: Dict[str, Any]) -> Dict[str, Any]:
    """Compatibility entry point; production graph injects a persistent runtime."""
    return await _execute_with_runtime(state, _catalog_runtime())


def executor_with_runtime(runtime: ToolRuntime):
    async def _executor(state: Dict[str, Any]) -> Dict[str, Any]:
        return await _execute_with_runtime(state, runtime)
    return _executor


async def verifier(state: Dict[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    evidence = state.get("execution", {}).get("evidence", [])
    ledger = EvidenceLedger(evidence)
    successful = ledger.observed()
    latest_by_query = {item.get("query_id"): item for item in evidence}
    has_errors = any(item.get("status") != "observed" for item in latest_by_query.values())
    task = state.get("task", {})
    facts = []
    consistency_issues = []
    freshness_issues = []
    claimability_issues = []
    coverage_issues = []
    trend = (ledger.observed("ping.trend")[0].get("data") or {}).get("trend_data", []) if ledger.has("ping.trend") else []
    anomaly = False
    if len(trend) >= 2:
        p95 = [float(row.get("p95_rtt") or 0) for row in trend if row.get("p95_rtt") is not None]
        if p95:
            baseline = sorted(p95)[len(p95) // 2]
            anomaly = max(p95) > baseline * 1.5 if baseline > 0 else False
            facts.append({"fact": "p95_spike_detected", "claim": "趋势中检测到 P95 RTT 峰值" if anomaly else "趋势中未检测到显著 P95 峰值",
                          "value": anomaly, "evidence_ids": [ledger.observed("ping.trend")[0]["evidence_id"]]})
    # Validate basic metric invariants before any claim is emitted.
    for item in successful:
        data = item.get("data") or {}
        for row in (data.get("statistics", []) + data.get("trend_data", [])):
            total, valid = row.get("total_samples"), row.get("valid_samples")
            if total is not None and valid is not None and (float(valid) < 0 or float(valid) > float(total)):
                consistency_issues.append(f"{item['evidence_id']}: valid_samples exceeds total_samples")
            median, p95 = row.get("median_rtt"), row.get("p95_rtt")
            if median is not None and p95 is not None and float(p95) < float(median):
                consistency_issues.append(f"{item['evidence_id']}: p95_rtt is below median_rtt")
        if item.get("observed_at") and item["observed_at"] > datetime.now(timezone.utc).isoformat():
            freshness_issues.append(f"{item['evidence_id']}: observed_at is in the future")
    missing = []
    if task.get("kind") == "network_analysis" and task.get("goal") == "diagnose":
        if not ledger.has("ping.by_asn"):
            coverage_issues.append("缺少 AS 归因证据")
            missing.append({"query_id": "ping.by_asn", "reason": "attribute latency by ASN", "priority": "high"})
        else:
            asn_rows = (ledger.observed("ping.by_asn")[0].get("data") or {}).get("statistics", [])
            concentrated, asn_rows = _asn_concentration(ledger)
            if concentrated and not ledger.has("ping.by_prefix24"):
                coverage_issues.append("AS 内部仍缺少 Prefix24 归因")
                missing.append({"query_id": "ping.by_prefix24", "reason": "localize concentrated ASN anomaly", "priority": "medium"})
            if concentrated:
                facts.append({"fact": "asn_concentration", "claim": "P95 RTT 差异集中在少数 AS",
                              "value": asn_rows[:3], "evidence_ids": [ledger.observed("ping.by_asn")[0]["evidence_id"]]})
            if ledger.has("ping.by_prefix24"):
                if not ledger.has("trace.paths"):
                    missing.append({"query_id": "trace.paths", "reason": "confirm path-level evidence", "priority": "medium"})
                if not ledger.has("trace.path_change"):
                    missing.append({"query_id": "trace.path_change", "reason": "correlate path changes with RTT trend", "priority": "medium"})
    if ledger.has("ping.by_prefix24"):
        prefix_rows = (ledger.observed("ping.by_prefix24")[0].get("data") or {}).get("statistics", [])
        if prefix_rows:
            facts.append({"fact": "prefix24_candidates", "claim": "异常候选集中到 Prefix24",
                          "value": prefix_rows[:3], "evidence_ids": [ledger.observed("ping.by_prefix24")[0]["evidence_id"]]})
    if ledger.has("ping.compare_window"):
        compare_item = ledger.observed("ping.compare_window")[0]
        compare_rows = (compare_item.get("data") or {}).get("comparison", [])
        if compare_rows:
            row = compare_rows[0]
            delta = row.get("p95_relative_delta")
            degraded = delta is not None and float(delta) > 0.2
            facts.append({"fact": "baseline_degradation", "claim": "当前窗口 P95 RTT 相比历史基线明显变差" if degraded else "当前窗口 P95 RTT 未明显高于历史基线",
                          "value": row, "evidence_ids": [compare_item["evidence_id"]]})
    if ledger.has("trace.paths"):
        path_rows = (ledger.observed("trace.paths")[0].get("data") or {}).get("paths", [])
        facts.append({"fact": "traceroute_paths_observed", "claim": "已获得 Traceroute 路径证据",
                      "value": path_rows[:3], "evidence_ids": [ledger.observed("trace.paths")[0]["evidence_id"]]})
    cross_evidence = {"status": "not_assessed", "reason": "缺少 RTT 趋势和路径变化的共同证据"}
    if ledger.has("ping.trend") and ledger.has("trace.path_change"):
        trend_rows = (ledger.observed("ping.trend")[0].get("data") or {}).get("trend_data", [])
        change_rows = (ledger.observed("trace.path_change")[0].get("data") or {}).get("path_changes", [])
        anomaly_buckets = _rtt_anomaly_buckets(ledger, trend_rows)
        ordered_changes = sorted(change_rows, key=lambda row: str(row.get("time_bucket")))
        change_buckets, previous_path = [], None
        for row in ordered_changes:
            current_path = row.get("dominant_path_hash")
            if previous_path is not None and current_path != previous_path:
                change_buckets.append(str(row.get("time_bucket")))
            previous_path = current_path
        trend_buckets = [str(row.get("time_bucket")) for row in trend_rows]
        near_change_buckets = set()
        for bucket in anomaly_buckets:
            if bucket in trend_buckets:
                index = trend_buckets.index(bucket)
                near_change_buckets.update(trend_buckets[max(0, index - 1): index + 2])
        overlap = sorted(set(change_buckets) & near_change_buckets)
        ids = [ledger.observed("ping.trend")[0]["evidence_id"], ledger.observed("trace.path_change")[0]["evidence_id"]]
        if overlap:
            cross_evidence = {"status": "correlated", "reason": "检测到主导路径切换，且 RTT 异常时间邻近；仅表示相关，不证明因果",
                              "time_buckets": overlap, "path_change_buckets": change_buckets, "evidence_ids": ids}
            facts.append({"fact": "rtt_path_time_correlation", "claim": "RTT 趋势与路径变化时间上相关，但不能单独证明因果",
                          "value": overlap, "evidence_ids": ids})
        else:
            cross_evidence = {"status": "not_correlated", "reason": "没有检测到主导路径切换与 RTT 异常的时间邻近关系；不据此推断因果", "path_change_buckets": change_buckets, "evidence_ids": ids}
    elif ledger.has("trace.paths"):
        cross_evidence = {"status": "observed_only", "reason": "已观察到路径，但缺少路径变化与 RTT 的共同时间桶"}
    for fact in facts:
        if not fact.get("evidence_ids") or any(not ledger.contains(evidence_id, observed_only=True) for evidence_id in fact["evidence_ids"]):
            claimability_issues.append(f"事实 {fact.get('fact')} 缺少有效 Evidence ID")
    diagnostic_facts = {"p95_spike_detected", "baseline_degradation", "asn_concentration", "prefix24_candidates",
                        "traceroute_paths_observed", "rtt_path_time_correlation"}
    if task.get("goal") == "diagnose" and not (set(fact.get("fact") for fact in facts) & diagnostic_facts):
        coverage_issues.append("诊断尚未得到可定位异常或根因方向的事实")
    if not successful:
        verdict, score = ("PASS", 0.55) if task.get("kind") == "knowledge" else ("ABSTAIN", 0.0)
    elif missing or coverage_issues:
        verdict, score = "PARTIAL", 0.55
    elif has_errors or consistency_issues or freshness_issues or claimability_issues:
        verdict, score = "PARTIAL", 0.55
    else:
        verdict, score = "PASS", 0.9
    verification = to_dict(Verification(verdict=verdict, score=score, successful_evidence=len(successful), total_evidence=len(evidence),
                    missing=[item["query_id"] for item in missing], missing_evidence=missing, facts=facts,
                    checks={"coverage": {"ok": not coverage_issues, "issues": coverage_issues},
                               "consistency": {"ok": not consistency_issues, "issues": consistency_issues},
                               "freshness": {"ok": not freshness_issues, "issues": freshness_issues},
                               "claimability": {"ok": not claimability_issues, "issues": claimability_issues},
                               "cross_evidence": cross_evidence},
                    reason="证据足够" if verdict == "PASS" else "仍缺少证明当前结论所需的证据，回答将明确标注限制"))
    next_node = "synthesizer"
    return {"verification": verification, "next_node": next_node, "trace": state.get("trace", []) + [_event(state, "verifier", started, reasoning=f"证据校验结果: {verdict}") ]}


async def synthesizer(state: Dict[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    task, verification = state.get("task", {}), state.get("verification", {})
    ledger = EvidenceLedger(state.get("execution", {}).get("evidence", []))
    for item in state.get("context", {}).get("knowledge", []):
        ledger.add({"evidence_id": item["evidence_id"], "kind": "context", "query_id": "knowledge.search", "status": "observed",
                    "data": {"content": item["content"], "score": item["score"]}, "quality": "retrieved"})
    for index, item in enumerate(state.get("context", {}).get("graph_context", []), start=1):
        ledger.add({"evidence_id": f"G{index}", "kind": "context", "query_id": "knowledge.graph", "status": "observed",
                    "data": item, "quality": "graph_retrieved"})
    evidence = ledger.all()
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
    all_evidence = ledger.all()
    evidence_id_set = {item["evidence_id"] for item in all_evidence}
    claims = []
    for index, fact in enumerate(verification.get("facts", []), start=1):
        evidence_ids = fact.get("evidence_ids", [])
        if evidence_ids and all(evidence_id in evidence_id_set for evidence_id in evidence_ids):
            bound = ledger.bind_claim(f"CL{index}", evidence_ids)
            bound["claim"] = fact.get("claim", fact.get("fact", ""))
            bound["fact"] = fact.get("fact")
            claims.append(bound)
    if claims and task.get("kind") == "network_analysis":
        # Claims are the factual answer surface even when no LLM is enabled.
        # The model may later improve prose, but cannot become the source of facts.
        answer = "\n".join(f"[{claim['claim_id']}] {claim['claim']}" for claim in claims)
    generated_by = "deterministic_synthesizer"
    if (os.getenv("HARNESS_LLM_ENABLED", "false").lower() == "true"
            and verification.get("verdict") in {"PASS", "PARTIAL"} and claims):
        try:
            from src.llm import get_llm_gateway
            prompt = ("你是已验证 Claim 的中文渲染器。只能改写给定 claim，不能增加、删除或合并 claim，"
                      "禁止引入新的数字、对象、因果关系或根因判断。只输出 JSON 数组："
                      "[{\"claim_id\":\"CL1\",\"text\":\"...\"}]。"
                      f"\nVerifiedClaims={json.dumps(claims, ensure_ascii=False, default=str)}"
                      f"\n用户问题：{state['query']}")
            llm_result = await asyncio.wait_for(get_llm_gateway().generate(prompt), timeout=10.0)
            rendered = _extract_json_object(llm_result.content)
            allowed = {claim["claim_id"] for claim in claims}
            if (isinstance(rendered, list) and {item.get("claim_id") for item in rendered} == allowed
                    and all(isinstance(item.get("text"), str) and item["text"].strip() for item in rendered)
                    and all(_renderer_grounded(next(claim["claim"] for claim in claims if claim["claim_id"] == item["claim_id"]), item["text"])
                            for item in rendered)):
                by_id = {item["claim_id"]: item["text"].strip() for item in rendered}
                answer = "\n".join(f"[{claim['claim_id']}] {by_id[claim['claim_id']]}" for claim in claims)
                generated_by = "llm_claim_renderer"
        except Exception:
            # LLM is an enhancement, never a dependency of the evidence path.
            pass
    charts = _chart_specs(evidence)
    answer_data = {"answer": answer, "charts": charts, "evidence": all_evidence,
                   "measurement_evidence": ledger.measurement(), "context_evidence": ledger.context(),
                   "generated_by": generated_by,
                   "claims": claims,
                   "verdict": verification.get("verdict")}
    return {"answer": answer_data, "next_node": "end", "trace": state.get("trace", []) + [_event(state, "synthesizer", started, reasoning="仅基于证据账本生成回答与图表数据") ]}
