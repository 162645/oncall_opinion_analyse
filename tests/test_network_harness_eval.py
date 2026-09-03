from src.eval.network_harness_eval import compare_strategies, evaluate_cases, score_case, DEFAULT_CASES


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


def test_eval_matrix_and_strategy_comparison_are_available():
    assert len(DEFAULT_CASES) == 35
    row = score_case(DEFAULT_CASES[0], {"task": {}, "plan": {}, "execution": {}, "verification": {}, "answer": {}})
    result = compare_strategies({"harness": [row], "react": [row]})
    assert set(result) == {"harness", "react"}
