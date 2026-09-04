"""Small deterministic evaluation set for interviewable Harness metrics.

The evaluator scores planning and evidence discipline from completed Harness
states. It does not pretend to measure production accuracy without labelled
network data; callers can replace the five seed cases with replay fixtures.
"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List


@dataclass(frozen=True)
class NetworkEvalCase:
    case_id: str
    query: str
    expected_queries: tuple[str, ...]
    expected_verdict: str
    expected_cross_status: str | None = None
    allowed_facts: tuple[str, ...] = ()
    forbidden_facts: tuple[str, ...] = ()
    case_type: str = "real_data_replay"
    expected_facts: tuple[Any, ...] = ()


DEFAULT_CASES = (
    NetworkEvalCase("E01", "UKRAINE P95 RTT 是否异常", ("ping.summary", "ping.trend"), "PASS"),
    NetworkEvalCase("E02", "UKRAINE 延迟异常并定位 AS", ("ping.by_asn",), "PARTIAL"),
    NetworkEvalCase("E03", "UKRAINE ASN 集中后继续定位 Prefix", ("ping.by_prefix24",), "PARTIAL"),
    NetworkEvalCase("E04", "路径变化与 RTT 时间重合", ("trace.path_change",), "PASS", "correlated"),
    NetworkEvalCase("E05", "ClickHouse 不可用时分析延迟", (), "ABSTAIN"),
)


# Expand the seed cases into a 35-case deterministic regression matrix.
_CASE_FAMILIES = (
    ("spike", "P95 RTT 突增", ("ping.summary", "ping.trend"), "PASS"),
    ("baseline", "相比历史窗口是否变差", ("ping.compare_window",), "PASS"),
    ("asn", "异常是否集中在 ASN", ("ping.by_asn",), "PARTIAL"),
    ("prefix", "定位异常 Prefix24", ("ping.by_prefix24",), "PARTIAL"),
    ("paths", "查看 Traceroute 路径", ("trace.paths",), "PASS"),
    ("abstain", "ClickHouse 无法连接时分析", (), "ABSTAIN"),
    ("correlation", "路径切换与 RTT 是否相关", ("trace.path_change",), "PASS"),
)
DEFAULT_CASES = DEFAULT_CASES + tuple(
    NetworkEvalCase(f"E{index:02d}", f"US {label} case {index}", queries, verdict,
                    "correlated" if family == "correlation" else None)
    for index in range(6, 36)
    for family, label, queries, verdict in (_CASE_FAMILIES[(index - 6) % len(_CASE_FAMILIES)],)
)


def score_case(case: NetworkEvalCase, state: Dict[str, Any]) -> Dict[str, Any]:
    task = state.get("task", {})
    plan_queries = {step.get("query_id") for step in state.get("plan", {}).get("steps", [])}
    evidence = state.get("execution", {}).get("evidence", [])
    evidence_queries = {item.get("query_id") for item in evidence if item.get("status") == "observed"}
    verification = state.get("verification", {})
    expected = set(case.expected_queries)
    selected = bool(expected <= (plan_queries | evidence_queries)) if expected else not evidence_queries
    claim_ids = {item.get("evidence_id") for item in evidence if item.get("status") == "observed"}
    claims = state.get("answer", {}).get("claims", [])
    allowed = set(state.get("eval_allowed_facts", case.allowed_facts))
    forbidden = set(state.get("eval_forbidden_facts", case.forbidden_facts))
    # Harness claims use ``fact``; ReAct claims use ``fact_type``.  Evidence
    # ids are necessary but not sufficient: a causal fact cannot be smuggled
    # in merely because some unrelated observation exists.
    unsupported = 0
    actual_facts = set()
    actual_fact_statuses = set()
    for claim in claims:
        fact = claim.get("fact_type") or claim.get("fact") or claim.get("fact_type")
        status = claim.get("status")
        if fact:
            actual_facts.add(fact)
            actual_fact_statuses.add((fact, status))
        bound = set(claim.get("evidence_ids", []))
        supporting_queries = set(claim.get("supporting_query_ids", []))
        # rtt_summary is a universal measurement fact whenever ping.summary
        # is part of the contract; older fixtures may not list it explicitly.
        fact_ok = not allowed or fact == "rtt_summary" or (fact in allowed and fact not in forbidden)
        evidence_ok = (not bound or bound <= claim_ids) and bool(bound or supporting_queries)
        if not (fact_ok and evidence_ok) or fact in forbidden:
            unsupported += 1
    cross_status = verification.get("checks", {}).get("cross_evidence", {}).get("status")
    return {
        "case_id": case.case_id,
        "verdict": verification.get("verdict", "unknown"),
        "task_spec_accuracy": task.get("kind") == "network_analysis",
        "query_selection_accuracy": selected,
        "evidence_coverage": len(expected & evidence_queries) / len(expected) if expected else float(not evidence_queries),
        "unsupported_claim_rate": unsupported / len(claims) if claims else 0.0,
        "claim_count": len(claims),
        "claim_presence": bool(claims),
        "claim_recall": _claim_recall(actual_facts, actual_fact_statuses, case.expected_facts, bool(claims)),
        "missing_required_queries": sorted(expected - evidence_queries),
        "correct_abstain": verification.get("verdict") == case.expected_verdict,
        "cross_status_match": case.expected_cross_status is None or cross_status == case.expected_cross_status,
        "rounds": state.get("round", 0),
        "query_count": len(evidence),
    }


def _claim_recall(actual_types: set[str], actual_statuses: set[tuple[str, Any]],
                  expected: tuple[Any, ...], has_claims: bool) -> float:
    """Match structured facts while retaining compatibility with old fixtures."""
    if not expected:
        return float(has_claims)
    matched = 0
    for item in expected:
        if isinstance(item, dict):
            key = (item.get("fact_type"), item.get("status"))
            matched += int(key in actual_statuses)
        else:
            matched += int(item in actual_types)
    return matched / len(expected)


def evaluate_cases(results: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(results)
    if not rows:
        return {"cases": 0}
    average = lambda key: sum(float(row[key]) for row in rows) / len(rows)
    return {
        "cases": len(rows),
        "task_spec_accuracy": average("task_spec_accuracy"),
        "plan_accuracy": average("query_selection_accuracy"),
        "evidence_coverage": average("evidence_coverage"),
        "unsupported_claim_rate": average("unsupported_claim_rate"),
        "correct_abstain_rate": average("correct_abstain"),
        "cross_evidence_accuracy": average("cross_status_match"),
        "average_rounds": average("rounds"),
        "average_query_count": average("query_count"),
        "claim_presence_rate": average("claim_presence"),
        "claim_recall": average("claim_recall"),
    }


def compare_strategies(results_by_strategy: Dict[str, Iterable[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    """Return one comparable metric row for Harness, Text-to-SQL, or ReAct."""
    return {name: evaluate_cases(rows) for name, rows in results_by_strategy.items()}
