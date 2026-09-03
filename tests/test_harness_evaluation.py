from src.eval import AgentEvaluationRecord, HarnessEvaluator


def test_harness_evaluator_covers_quality_reliability_latency_and_cost():
    evaluator = HarnessEvaluator()
    evaluator.record(AgentEvaluationRecord(
        task_id="1", task_success=True, tool_calls=2, tool_successes=2,
        recovery_attempted=True, recovery_succeeded=True, latency_ms=10,
        input_tokens=100, output_tokens=20, token_cost_usd=0.001,
    ))
    evaluator.record(AgentEvaluationRecord(
        task_id="2", task_success=False, tool_calls=1, tool_successes=0,
        recovery_attempted=False, recovery_succeeded=False, latency_ms=30,
        input_tokens=50, output_tokens=10, token_cost_usd=0.0005,
        skill_regression_passed=False,
    ))
    summary = evaluator.summary()
    assert summary["task_success_rate"] == 0.5
    assert summary["tool_success_rate"] == 2 / 3
    assert summary["recovery_success_rate"] == 1.0
    assert summary["input_tokens"] == 150
    assert summary["token_cost_usd"] == 0.0015
    assert summary["skill_regression_pass_rate"] == 0.5
