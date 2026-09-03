"""Contract tests for the deterministic parts of the evidence-driven Harness."""

import pytest

from src.harness.catalog import CATALOG, compile_sql, read_sql
from src.harness.nodes import understand, planner, executor, synthesizer, _steps, _chart_specs


@pytest.mark.asyncio
async def test_understand_extracts_region_and_time_window():
    state = {"query": "分析 UKRAINE 最近 7 天的 P95 延迟趋势", "trace": []}
    update = await understand(state)
    assert update["task"]["region"] == "UKRAINE"
    assert update["task"]["metric"] == "p95"
    assert update["task"]["time_range"]["hours"] == 168


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
        "verification": {"verdict": "PASS", "successful_evidence": 1, "total_evidence": 1},
        "execution": {"evidence": [{"evidence_id": "E1", "query_id": "ping.summary",
                                      "status": "observed", "data": {"statistics": []}}]},
        "context": {}, "trace": [],
    })
    claim = update["answer"]["claims"][0]
    assert claim == {"claim_id": "CL1", "evidence_ids": ["E1"]}
    assert {item["evidence_id"] for item in update["answer"]["evidence"]} == {"E1"}
