from src.eval.network_harness_eval import evaluate_cases, score_case, DEFAULT_CASES


def test_network_eval_reports_interviewable_metrics():
    row = score_case(DEFAULT_CASES[0], {
        "task": {"kind": "network_analysis"},
        "plan": {"steps": [{"query_id": "ping.summary"}, {"query_id": "ping.trend"}]},
        "execution": {"evidence": [{"evidence_id": "E1", "query_id": "ping.summary", "status": "observed"},
                                      {"evidence_id": "E2", "query_id": "ping.trend", "status": "observed"}]},
        "verification": {"verdict": "PASS"}, "answer": {"claims": [{"evidence_ids": ["E1"]}]},
        "round": 1,
    })
    metrics = evaluate_cases([row])
    assert metrics["task_spec_accuracy"] == 1.0
    assert metrics["evidence_coverage"] == 1.0
    assert metrics["unsupported_claim_rate"] == 0.0
    assert metrics["average_query_count"] == 2.0
