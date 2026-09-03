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


def load_cases(path: Path) -> list[NetworkEvalCase]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [NetworkEvalCase(
        case_id=row["case_id"],
        query=row["query"],
        expected_queries=tuple(row.get("expected_queries", row.get("required_queries", []))),
        expected_verdict=row.get("expected_verdict", "PASS"),
        expected_cross_status=row.get("expected_cross_status"),
    ) for row in rows]


async def run(cases: list[NetworkEvalCase], fixture: dict[str, Any]) -> dict[str, Any]:
    results = []
    for case in cases:
        replay = await run_harness_replay({"case_id": case.case_id, "query": case.query}, fixture)
        results.append(score_case(case, replay["state"]))
    return {"summary": evaluate_cases(results), "cases": results}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run network Harness replay evaluation")
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = asyncio.run(run(load_cases(args.cases), json.loads(args.fixture.read_text(encoding="utf-8"))))
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
