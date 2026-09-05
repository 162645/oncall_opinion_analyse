# Network replay fixtures

This directory contains a small, checked-in replay seed used by CI and local
smoke runs. It is intentionally measurement-shaped and contains no production
credentials or private data. The full 50-case report is an artifact tied to a
specific commit; it must not be regenerated or described as production
diagnosis accuracy without independently labelled ground truth.

Run it with:

```bash
PYTHONPATH=. python -m scripts.run_agent_eval \
  --cases eval_data/network/cases.jsonl \
  --fixture-dir eval_data/network \
  --max-cases 5 --react-policy deterministic
```
