# Agent Harness Local Benchmark

Generated on 2026-08-18 from `artifacts/benchmarks/harness_metrics.json`.

## Environment

- Python: 3.11.15
- Requests: 1,000
- Concurrency: 20
- Checkpoint integration: local Redis Stack
- Workload: deterministic Harness nodes; no external LLM or business dependency

## Results

| Metric | Measured result |
|---|---:|
| Agent node types | 8 |
| Registered MCP tools | 20 |
| Task success rate | 100% |
| Throughput | 449.81 requests/s |
| P50 latency | 40.33 ms |
| P95 latency | 69.43 ms |
| P99 latency | 78.19 ms |
| Redis cross-instance recovery | 30/30, 100% |
| Tool calls repeated after recovery | 0 |
| Side-effect duplicate rate | 50% baseline → 0% governed |
| Transient-fault success rate | 33.3% baseline → 100% with classified retry |
| Circuit-breaker P95 | 5.74 ms → 0.73 ms, 87.36% reduction |
| Executed-node Trace coverage | 6/6, 100% |
| Finished benchmark spans | 8,000 |
| Skill offline replay | 100/100, 100% |
| Parallel vs sequential P95 | 11.37 ms vs 44.44 ms, 74.42% reduction |
| Token cost | $0.00 for this synthetic run; no LLM calls were made |

## Interpretation boundary

These are local engineering benchmarks, not production SLA or MTTR claims. They prove runtime behavior under controlled failure injection. Real LLM token cost and diagnosis quality require a representative labeled incident dataset and configured model provider.

The OpenTelemetry SDK in-memory export path is covered by tests. Collector and Jaeger Compose configuration validates syntactically, but the external container smoke test could not finish because Docker Hub image pulls timed out twice in the current network environment.

## Reproduce

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements-harness.txt
docker run --rm -d --name oncall-agent-redis-stack \
  -p 127.0.0.1:6390:6379 redis/redis-stack-server:latest
.venv/bin/python -m pytest tests -q
.venv/bin/python scripts/benchmark_harness.py \
  --redis-url redis://127.0.0.1:6390/0 \
  --requests 1000 --concurrency 20
```

