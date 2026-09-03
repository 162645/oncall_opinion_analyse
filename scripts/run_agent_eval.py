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
        raw.append({"case_id": case.case_id, "case_type": case.case_type, "harness": h,
                    "react": r, "harness_calls": replay["calls"], "react_calls": react["calls"],
                    "react_llm_calls": react["llm_calls"], "react_strategy": react["strategy"]})
    def operational(rows: list[dict[str, Any]], key: str) -> dict[str, float]:
        values = [len(x[key]) for x in raw]
        return {"average_tool_calls": sum(values) / len(values), "p95_tool_calls": sorted(values)[max(0, int(len(values) * .95) - 1)]}
    return {"summary": {"harness": {**evaluate_cases(harness_results), **operational(harness_results, "harness_calls")},
                         "free_react": {**evaluate_cases(react_results), **operational(react_results, "react_calls")}}, "cases": raw}


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
              f"| Correct abstain rate | {summary['free_react']['correct_abstain_rate']:.2%} | {summary['harness']['correct_abstain_rate']:.2%} |",
              f"| Average tool calls | {summary['free_react']['average_tool_calls']:.2f} | {summary['harness']['average_tool_calls']:.2f} |",
              "", "Raw per-case results are stored in `agent_comparison.json`."]
        args.output.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
