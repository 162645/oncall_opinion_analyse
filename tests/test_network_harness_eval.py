from src.eval.network_harness_eval import compare_strategies, evaluate_cases, score_case, DEFAULT_CASES
from src.eval.runners.harness_runner import run_harness_replay


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
    assert metrics["task_success_rate"] == 0.0  # no expected fact claim was emitted


def test_task_success_requires_expected_facts_and_grounded_claims():
    case = DEFAULT_CASES[0]
    state = {
        "task": {"kind": "network_analysis"},
        "execution": {"evidence": [{"evidence_id": "E1", "query_id": "ping.summary", "status": "observed"},
                                      {"evidence_id": "E2", "query_id": "ping.trend", "status": "observed"}]},
        "verification": {"verdict": "PASS"},
        "answer": {"claims": [{"fact_type": "p95_spike", "status": "present", "evidence_ids": ["E2"]}]},
    }
    assert score_case(case, state)["task_success"] is True


def test_eval_matrix_and_strategy_comparison_are_available():
    assert len(DEFAULT_CASES) == 35
    row = score_case(DEFAULT_CASES[0], {"task": {}, "plan": {}, "execution": {}, "verification": {}, "answer": {}})
    result = compare_strategies({"harness": [row], "react": [row]})
    assert set(result) == {"harness", "react"}


def test_replay_fixture_is_injected_into_real_harness(monkeypatch):
    import asyncio
    # Replay contract tests must be deterministic even when a developer's
    # shell has the production LLM flags enabled.
    monkeypatch.setenv("HARNESS_LLM_ENABLED", "false")
    monkeypatch.setenv("HARNESS_PLANNER_ENABLED", "false")
    fixture = {"ping.summary": {"statistics": [{"total_samples": 100, "valid_samples": 100,
        "mean_rtt": 10, "median_rtt": 10, "p95_rtt": 20, "p99_rtt": 30}]}}
    result = asyncio.run(run_harness_replay({"case_id": "replay-1", "query": "US RTT"}, fixture))
    assert result["success"] and result["calls"][0]["query_id"] == "ping.summary"
