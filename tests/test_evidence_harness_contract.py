"""Contract tests for the deterministic parts of the evidence-driven Harness."""

import pytest

from src.harness.catalog import CATALOG, compile_sql, read_sql
from src.harness.nodes import understand, planner, executor, synthesizer, context, _steps, _chart_specs, _llm_generate
from src.harness.ledger import EvidenceLedger
from src.harness.models import QueryIR, TimeRange
from src.harness.query_ir import compile_query_ir, validate_query_ir


@pytest.mark.asyncio
async def test_understand_extracts_region_and_time_window():
    state = {"query": "分析 UKRAINE 最近 7 天的 P95 延迟趋势", "trace": []}
    update = await understand(state)
    assert update["task"]["region"] == "UKRAINE"
    assert update["task"]["metric"] == "p95"
    assert update["task"]["time_range"]["hours"] == 168


@pytest.mark.asyncio
async def test_understand_does_not_treat_metric_as_region():
    update = await understand({"query": "分析最近 24 小时 P95 RTT 趋势", "trace": []})
    assert update["task"]["region"] is None


@pytest.mark.asyncio
async def test_baseline_intent_survives_task_contract():
    update = await understand({"query": "US 最近 24 小时延迟相比之前是否变差", "trace": []})
    assert update["task"]["needs_baseline"] is True


@pytest.mark.asyncio
async def test_simple_context_query_skips_retrieval():
    update = await context({
        "query": "JP 最近 24 小时 P95 是多少", "task": {"kind": "network_analysis", "region": "JP",
        "metric": "p95", "goal": "describe", "planning_mode": "recipe", "semantic_requirements": [],
        "analysis_dimensions": [], "intent_summary": "查看当前指标"}, "trace": []})
    assert update["context"]["retrieval_plan"]["need_retrieval"] is False
    assert update["context"]["planning_context"]["constraints"]


@pytest.mark.asyncio
async def test_llm_budget_blocks_calls_before_gateway(monkeypatch):
    class ExplodingGateway:
        async def generate(self, *_args, **_kwargs):
            raise AssertionError("budget should block the gateway")
    monkeypatch.setattr("src.llm.get_llm_gateway", lambda: ExplodingGateway())
    result = await _llm_generate({"budget": {"max_llm_calls": 0, "max_llm_tokens": 100}, "llm_usage": {}}, "test")
    assert result is None


@pytest.mark.asyncio
async def test_understand_llm_enriches_semantics_without_breaking_contract(monkeypatch):
    class FakeGateway:
        async def generate(self, _prompt):
            return type("Response", (), {"content": '{"kind":"network_analysis","goal":"diagnose",'
                    '"region":"UKRAINE","metric":"p95","planning_mode":"long_tail",'
                    '"time_range":{"start_time":"2026-01-01T00:00:00+00:00","end_time":"2026-01-02T00:00:00+00:00"},'
                    '"analysis_dimensions":["time","path"],"semantic_requirements":["compare_day_night"],'
                    '"semantic_confidence":0.91}'})()

    monkeypatch.setenv("HARNESS_UNDERSTAND_ENABLED", "true")
    monkeypatch.setattr("src.llm.get_llm_gateway", lambda: FakeGateway())
    update = await understand({"query": "UKRAINE 比较白天和凌晨的路径变化与 P95 延迟", "trace": []})
    assert update["task"]["planning_mode"] == "long_tail"
    assert update["task"]["analysis_dimensions"] == ["time", "path"]
    assert update["task"]["semantic_requirements"] == ["compare_day_night", "explain_path_change_without_claiming_causality"]


@pytest.mark.asyncio
async def test_planner_only_emits_catalog_query_ids():
    state = {
        "task": {"kind": "network_analysis", "region": "UKRAINE", "goal": "diagnose",
                 "time_range": {"start_time": "2026-01-01T00:00:00+00:00", "end_time": "2026-01-02T00:00:00+00:00"}},
        "execution": {}, "round": 0, "trace": [],
    }
    update = await planner(state)
    assert update["plan"]["steps"]
    assert {step["query_id"] for step in update["plan"]["steps"]} <= set(CATALOG)


def test_catalog_sql_contracts_are_present():
    schema = open("deploy/oncall-clickhouse/schema.sql", encoding="utf-8").read()
    for query_id in CATALOG:
        sql = read_sql(query_id)
        assert query_id in sql
        assert "SELECT" in sql.upper()
        for column in CATALOG[query_id].columns:
            assert column in sql or column == "time_bucket"
    assert "rtt_ms Float32" in schema
    assert "ip_path_hash UInt64" in schema


def test_replan_only_retries_unavailable_queries():
    task = {"kind": "network_analysis", "region": "UKRAINE", "goal": "describe",
            "time_range": {"start_time": "2026-01-01T00:00:00+00:00", "end_time": "2026-01-02T00:00:00+00:00"}}
    steps = _steps(task, {"evidence": [
        {"evidence_id": "E1", "query_id": "ping.summary", "status": "observed"},
        {"evidence_id": "E2", "query_id": "ping.trend", "status": "unavailable"},
    ]})
    assert [step["query_id"] for step in steps] == ["ping.trend"]


def test_replan_does_not_retry_permanent_failure():
    task = {"kind": "network_analysis", "region": "UKRAINE", "goal": "describe",
            "time_range": {"start_time": "2026-01-01T00:00:00+00:00", "end_time": "2026-01-02T00:00:00+00:00"}}
    steps = _steps(task, {"evidence": [{"evidence_id": "E1", "query_id": "ping.trend",
                                         "status": "unavailable", "error_kind": "validation"}]})
    assert steps == []


def test_chart_spec_keeps_evidence_binding():
    charts = _chart_specs([{
        "evidence_id": "E2", "query_id": "ping.trend", "status": "observed",
        "data": {"trend_data": [{"time_bucket": "t1", "median_rtt": 10, "p95_rtt": 20}]},
    }])
    assert charts[0]["chart_type"] == "line"
    assert charts[0]["evidence_ids"] == ["E2"]
    assert charts[0]["series"][1]["data"] == [20]


def test_catalog_compiler_separates_identifier_and_values():
    sql, bindings = compile_sql("ping.summary", {
        "region": "UKRAINE", "start_time": "2026-01-01T00:00:00+00:00",
        "end_time": "2026-01-02T00:00:00+00:00", "limit": 20,
    })
    assert "UKRAINE__ping" in sql
    assert "%(start_time)s" in sql
    assert bindings["start_time"].startswith("2026-01-01")
    with pytest.raises(ValueError):
        compile_sql("ping.summary", {"region": "UKRAINE; DROP TABLE x", "start_time": "a", "end_time": "b"})


def test_prefix_query_keeps_anomalous_asn_scope():
    sql, bindings = compile_sql("ping.by_prefix24", {
        "region": "UKRAINE", "asn": 64500, "start_time": "2026-01-01T00:00:00+00:00",
        "end_time": "2026-01-02T00:00:00+00:00"})
    assert "ip_asn = %(asn)s" in sql
    assert bindings["asn"] == 64500


def test_query_ir_compiles_only_allowlisted_identifiers():
    ir = QueryIR(table="ping_measurements", dimensions=["hour", "ip_asn"],
                 metrics=[{"function": "quantile", "field": "rtt_ms", "percentile": 0.95}],
                 filters={"region": "UKRAINE"}, group_by=["hour", "ip_asn"],
                 time_range=TimeRange(start_time="2026-01-01T00:00:00+00:00", end_time="2026-01-02T00:00:00+00:00"))
    sql, bindings = compile_query_ir(ir)
    assert "UKRAINE__ping" in sql and "%(start_time)s" in sql
    assert "rtt_ms" in sql and bindings["limit"] == 100
    with pytest.raises(ValueError):
        validate_query_ir(ir.model_copy(update={"filters": {"region": "US;DROP"}}))


def test_query_ir_requires_explicit_time_range():
    from src.harness.models import QueryIR
    with pytest.raises(ValueError, match="time range"):
        validate_query_ir(QueryIR(table="ping_measurements", metrics=[{"function": "count", "field": "rtt_ms"}],
                                  filters={"region": "UKRAINE"}))


@pytest.mark.asyncio
async def test_executor_maps_clickhouse_rows_to_catalog_contract(monkeypatch):
    class FakeClient:
        def execute(self, sql, params):
            assert "UKRAINE__ping" in sql
            return [(10, 9, 20.0, 18.0, 40.0, 60.0)]

    monkeypatch.setattr("src.harness.nodes.get_clickhouse_client", lambda: FakeClient())
    state = {"plan": {"steps": [{"query_id": "ping.summary", "params": {
        "query_type": "ping_stats", "region": "UKRAINE", "start_time": "a", "end_time": "b"
    }}]}, "execution": {}, "trace": []}
    update = await executor(state)
    assert update["execution"]["results"][0]["success"] is True
    assert update["execution"]["evidence"][0]["data"]["statistics"][0]["p95_rtt"] == 40.0


@pytest.mark.asyncio
async def test_executor_rejects_catalog_query_type_mismatch(monkeypatch):
    class ExplodingClient:
        def execute(self, *_args):
            raise AssertionError("invalid query type must be rejected before ClickHouse")

    monkeypatch.setattr("src.harness.nodes.get_clickhouse_client", lambda: ExplodingClient())
    state = {"plan": {"steps": [{"query_id": "ping.summary", "params": {
        "query_type": "ping_trend", "region": "UKRAINE", "start_time": "a", "end_time": "b"
    }}]}, "execution": {}, "trace": []}
    update = await executor(state)
    assert update["execution"]["evidence"][0]["status"] == "unavailable"
    assert "query_type mismatch" in update["execution"]["evidence"][0]["error"]


@pytest.mark.asyncio
async def test_synthesizer_claims_reference_only_ledger_evidence():
    update = await synthesizer({
        "query": "分析 UKRAINE 延迟",
        "task": {"kind": "network_analysis", "region": "UKRAINE"},
        "verification": {"verdict": "PASS", "successful_evidence": 1, "total_evidence": 1,
                         "facts": [{"fact": "p95_spike_detected", "claim": "P95 RTT 上升",
                                    "evidence_ids": ["E1"]}]},
        "execution": {"evidence": [{"evidence_id": "E1", "query_id": "ping.summary",
                                      "status": "observed", "data": {"statistics": []}}]},
        "context": {}, "trace": [],
    })
    claim = update["answer"]["claims"][0]
    assert claim["claim_id"] == "CL1"
    assert claim["evidence_ids"] == ["E1"]
    assert claim["fact"] == "p95_spike_detected"
    assert {item["evidence_id"] for item in update["answer"]["evidence"]} == {"E1"}


def test_ledger_preserves_provenance_and_distinguishes_ids_from_query_ids():
    ledger = EvidenceLedger([{"evidence_id": "E1", "query_id": "ping.summary", "status": "observed",
                              "observed_at": "2026-01-01T00:00:00+00:00", "source": "clickhouse",
                              "params": {"region": "UKRAINE"}, "trace_id": "run-1"}])
    assert ledger.has("ping.summary") is True
    assert ledger.contains("E1", observed_only=True) is True
    item = ledger.all()[0]
    assert item["observed_at"].startswith("2026-01-01")
    assert item["trace_id"] == "run-1"


@pytest.mark.asyncio
async def test_verifier_reports_structured_missing_evidence_and_invariants():
    from src.harness.nodes import verifier
    update = await verifier({
        "task": {"kind": "network_analysis", "goal": "diagnose"},
        "execution": {"evidence": [{"evidence_id": "E1", "query_id": "ping.trend", "status": "observed",
                                      "data": {"trend_data": [{"time_bucket": "t", "median_rtt": 90, "p95_rtt": 40}]}}]},
        "trace": [],
    })
    assert update["verification"]["missing_evidence"][0]["objective"] == "判断异常是否集中于特定 ASN"
    assert update["verification"]["checks"]["consistency"]["ok"] is False
    assert update["verification"]["facts"] == []


@pytest.mark.asyncio
async def test_verifier_requires_real_dominant_path_switch_for_correlation():
    from src.harness.nodes import verifier
    update = await verifier({
        "task": {"kind": "network_analysis", "goal": "describe"},
        "execution": {"evidence": [
            {"evidence_id": "E1", "query_id": "ping.trend", "status": "observed",
             "data": {"trend_data": [{"time_bucket": "01", "median_rtt": 10, "p95_rtt": 20},
                                      {"time_bucket": "02", "median_rtt": 10, "p95_rtt": 80}]}},
            {"evidence_id": "E2", "query_id": "trace.path_change", "status": "observed",
             "data": {"path_changes": [{"time_bucket": "01", "path_count": 2, "sample_count": 10, "dominant_path_hash": 7},
                                         {"time_bucket": "02", "path_count": 2, "sample_count": 10, "dominant_path_hash": 7}]}}
        ]}, "trace": []})
    assert update["verification"]["checks"]["cross_evidence"]["status"] == "not_correlated"


@pytest.mark.asyncio
async def test_long_tail_planner_is_guarded_to_catalog(monkeypatch):
    class FakeGateway:
        async def generate(self, _prompt):
            return type("Response", (), {"content": '[{"query_id":"ping.summary","params":{"region":"UKRAINE"}}, {"query_id":"drop.table","params":{}}]'})()

    monkeypatch.setenv("HARNESS_PLANNER_ENABLED", "true")
    monkeypatch.setattr("src.llm.get_llm_gateway", lambda: FakeGateway())
    update = await planner({
        "task": {"kind": "network_analysis", "region": "UKRAINE", "goal": "describe",
                 "planning_mode": "long_tail", "time_range": {"start_time": "2026-01-01T00:00:00+00:00", "end_time": "2026-01-02T00:00:00+00:00"}},
        "context": {"catalog": list(CATALOG)}, "execution": {"evidence": []}, "verification": {},
        "round": 0, "trace": [],
    })
    assert update["plan"]["source"] == "llm_guarded"
    assert [step["query_id"] for step in update["plan"]["steps"]] == ["ping.summary"]
