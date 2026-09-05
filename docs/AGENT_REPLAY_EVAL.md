# NetProbe Agent Replay Evaluation

This document is the reproducibility contract for the network-analysis replay
benchmark. It deliberately separates end-to-end task success from diagnostic
signals such as query coverage and verdict-label matching.

## Evaluation protocol

- Dataset: `eval_data/network/cases.jsonl` and its replay fixtures.
- Strategies: guarded Evidence Harness and DeepSeek Free ReAct baseline.
- The baseline sees the same Query Catalog and tool schemas, but not
  `expected_queries`, facts, verdicts, or other evaluation labels.
- The Harness keeps deterministic execution, SQL validation, evidence binding,
  verifier gates, and round/query/time/LLM budgets.
- `--max-cases` is available for smoke runs. The default baseline budget is
  eight tool calls per case; use `--react-max-tool-calls 3` only for a clearly
  labelled smoke experiment.

## Metrics

`Task Success Rate` is the primary outcome metric. A case succeeds only when
all required ground-truth facts are recalled, every claim is grounded, and an
ABSTAIN case is correctly abstained. `Evidence Coverage`, `Claim Recall`,
`Unsupported Claim Rate`, and `Verdict Match` are secondary diagnostics.

`Verdict Match` is not answer accuracy: it only compares PASS/PARTIAL/ABSTAIN
to the case label.

## Reproduction

Use the project environment and configure DeepSeek credentials outside Git:

```bash
set -a; source .env; set +a
PYTHONPATH=. python -m scripts.run_agent_eval \
  --cases eval_data/network/cases.jsonl \
  --fixture-dir eval_data/network \
  --max-cases 5 \
  --react-policy llm \
  --react-max-tool-calls 3 \
  --output artifacts/eval/agent_smoke.json
```

For a full comparison, remove `--max-cases` and keep the default eight-call
baseline budget. The JSON output stores per-case results and the exact
evaluation configuration.

## Reporting rule

Do not copy historical benchmark numbers into a new release unless the JSON
report was generated from that exact commit, model, prompt configuration, and
budget. A replay uses real measurement-shaped fixtures, but it is not a claim
of production network-diagnosis accuracy without independently labelled
ground truth.
