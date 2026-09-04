"""Run deterministic network replay cases and emit a machine-readable report.

The runner deliberately reuses the production Harness and swaps only the
ToolRuntime.  A fixture is keyed by query id and contains the same typed
payload returned by the catalog adapter, so the evaluation never calls a
live database and can be reproduced in CI.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from src.eval.network_harness_eval import NetworkEvalCase, evaluate_cases, score_case
from src.eval.runners.harness_runner import run_harness_replay
from src.eval.runners.react_runner import run_react_replay


def load_cases(path: Path) -> list[NetworkEvalCase]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [NetworkEvalCase(
        case_id=row["case_id"],
        query=row["query"],
        expected_queries=tuple(row.get("expected_queries", row.get("required_queries", []))),
        expected_verdict=row.get("expected_verdict", "PASS"),
        expected_cross_status=row.get("expected_cross_status"),
        allowed_facts=tuple(row.get("allowed_facts", [])),
        forbidden_facts=tuple(row.get("forbidden_facts", [])),
        case_type=row.get("case_type", "real_data_replay"),
        expected_facts=tuple(row.get("expected_facts", row.get("allowed_facts", []))),
    ) for row in rows]


async def run(cases: list[NetworkEvalCase], fixture_dir: Path, case_rows: list[dict[str, Any]]) -> dict[str, Any]:
    harness_results, react_results, raw = [], [], []
    for case in cases:
        row = next(x for x in case_rows if x["case_id"] == case.case_id)
        fixture = json.loads((fixture_dir / row["fixture_path"]).read_text(encoding="utf-8"))
        replay = await run_harness_replay({"case_id": case.case_id, "query": case.query}, fixture)
        react = await run_react_replay({"case_id": case.case_id, "query": case.query}, fixture)
        h, r = score_case(case, replay["state"]), score_case(case, react["state"])
        harness_results.append(h); react_results.append(r)
        raw.append({"case_id": case.case_id, "case_type": case.case_type, "expected_verdict": case.expected_verdict,
                    "expected_queries": list(case.expected_queries), "harness": h,
                    "react": r, "harness_calls": replay["calls"], "react_calls": react["calls"],
                    "harness_llm_by_node": [event.get("agent_name") for event in replay["state"].get("trace", [])
                                            if event.get("llm_used")],
                    "react_llm_calls": react["llm_calls"], "react_strategy": react["strategy"]})
    def operational(rows: list[dict[str, Any]], key: str) -> dict[str, float]:
        values = [len(x[key]) for x in raw]
        total = sum(values)
        useful = sum(sum(1 for call in item[key] if call.get("query_id") in set(item.get("expected_queries", [])))
                     for item in raw)
        strategy = key.replace("_calls", "")
        coverage_efficiency = sum(float(item[strategy].get("evidence_coverage", 0.0)) / max(1, len(item[key]))
                                  for item in raw) / len(raw)
        return {"average_tool_calls": sum(values) / len(values),
                "p95_tool_calls": sorted(values)[max(0, int(len(values) * .95) - 1)],
                "useful_tool_rate": useful / total if total else 0.0,
                "evidence_coverage_per_tool_call": coverage_efficiency}
    def diagnostics(strategy: str) -> dict[str, Any]:
        rows = [x[strategy] for x in raw]
        confusion: dict[str, dict[str, int]] = {}
        by_type: dict[str, list[dict[str, Any]]] = {}
        missing: dict[str, int] = {}
        for item in raw:
            actual = item[strategy].get("actual_verdict", item[strategy].get("verdict", "unknown"))
            expected = item["expected_verdict"]
            confusion.setdefault(expected, {})[actual] = confusion.setdefault(expected, {}).get(actual, 0) + 1
            by_type.setdefault(item["case_type"], []).append(item[strategy])
            for query_id in item[strategy].get("missing_required_queries", []):
                missing[query_id] = missing.get(query_id, 0) + 1
        return {"verdict_confusion_matrix": confusion,
                "by_case_type": {name: evaluate_cases(values) for name, values in by_type.items()},
                "missing_evidence_clusters": dict(sorted(missing.items(), key=lambda x: (-x[1], x[0])))}
    for item in raw:
        item["harness"]["actual_verdict"] = item["harness"].get("verdict")
        item["react"]["actual_verdict"] = item["react"].get("verdict")
    harness_summary = {**evaluate_cases(harness_results), **operational(harness_results, "harness_calls"), **diagnostics("harness")}
    react_summary = {**evaluate_cases(react_results), **operational(react_results, "react_calls"), **diagnostics("react")}
    return {"summary": {"harness": harness_summary, "free_react": react_summary}, "cases": raw}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run network Harness replay evaluation")
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, help="single fixture compatibility mode")
    parser.add_argument("--fixture-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.cases.read_text(encoding="utf-8").splitlines() if line.strip()]
    cases = load_cases(args.cases)
    if args.fixture_dir:
        report = asyncio.run(run(cases, args.fixture_dir, rows))
    else:
        # Retain the original one-fixture mode for small smoke experiments.
        fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
        report = asyncio.run(run(cases, args.cases.parent, [{"case_id": c.case_id, "fixture_path": args.fixture.name} for c in cases]))
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
        summary = report["summary"]
        md = ["# Agent Replay Comparison", "", "| Metric | Free ReAct | Evidence Harness |", "|---|---:|---:|",
              f"| Cases | {summary['free_react']['cases']} | {summary['harness']['cases']} |",
              f"| Unsupported claim rate | {summary['free_react']['unsupported_claim_rate']:.2%} | {summary['harness']['unsupported_claim_rate']:.2%} |",
              f"| Key evidence coverage | {summary['free_react']['evidence_coverage']:.2%} | {summary['harness']['evidence_coverage']:.2%} |",
              f"| Verdict accuracy | {summary['free_react']['correct_abstain_rate']:.2%} | {summary['harness']['correct_abstain_rate']:.2%} |",
              f"| Claim presence rate | {summary['free_react']['claim_presence_rate']:.2%} | {summary['harness']['claim_presence_rate']:.2%} |",
              f"| Claim recall | {summary['free_react']['claim_recall']:.2%} | {summary['harness']['claim_recall']:.2%} |",
              f"| Average tool calls | {summary['free_react']['average_tool_calls']:.2f} | {summary['harness']['average_tool_calls']:.2f} |",
              f"| P95 tool calls | {summary['free_react']['p95_tool_calls']:.0f} | {summary['harness']['p95_tool_calls']:.0f} |",
              f"| Useful tool rate | {summary['free_react']['useful_tool_rate']:.2%} | {summary['harness']['useful_tool_rate']:.2%} |",
              f"| Evidence coverage / tool call | {summary['free_react']['evidence_coverage_per_tool_call']:.3f} | {summary['harness']['evidence_coverage_per_tool_call']:.3f} |",
              "", "The baseline is a DeepSeek LLM ReAct policy; Harness uses the same DeepSeek gateway with guarded planning and evidence verification.",
              "Raw per-case results are stored in the JSON report."]
        args.output.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
