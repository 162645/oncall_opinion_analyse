"""Small dependency-stable CI gate for the maintained Evidence Harness."""

from src.eval.network_harness_eval import DEFAULT_CASES, evaluate_cases, score_case
from src.harness.catalog import CATALOG, compile_sql
from src.harness.ledger import EvidenceLedger


def test_ci_smoke_covers_catalog_ledger_and_eval():
    assert len(DEFAULT_CASES) == 35
    sql, bindings = compile_sql("ping.by_prefix24", {
        "region": "US", "asn": 64500,
        "start_time": "2026-01-01T00:00:00+00:00",
        "end_time": "2026-01-02T00:00:00+00:00",
    })
    assert "ip_asn = %(asn)s" in sql and bindings["asn"] == 64500
    ledger = EvidenceLedger([{"evidence_id": "E1", "query_id": "ping.summary", "status": "observed"}])
    assert ledger.contains("E1", observed_only=True) and len(CATALOG) >= 8
    row = score_case(DEFAULT_CASES[0], {"task": {}, "plan": {}, "execution": {}, "verification": {}, "answer": {}})
    assert evaluate_cases([row])["cases"] == 1
