# Harness 演示验收清单

## 一条真实演示问题

```text
分析 UKRAINE 最近 24 小时 Ping 延迟，给出 P95 趋势，并定位是否集中在某个 AS
```

## 面试时展示什么

1. 对话区显示六个 Harness 节点的执行轨迹。
2. “证据校验”显示每个 `query_id` 的观测状态。
3. ClickHouse 不可用时，结果显示 `ABSTAIN`，并说明原因，不输出猜测。
4. ClickHouse 可用时，展示趋势、AS 分组和 Traceroute 结果。

## API 验收

```bash
pytest -q tests/test_evidence_harness_contract.py tests/test_harness_graph.py tests/test_chat_evidence_contract.py
```

响应中的关键字段：`run_id`、`verdict`、`evidence[]`、`trace[]`、`confidence`。

如果配置了 LLM，可将 `HARNESS_LLM_ENABLED=true` 打开；LLM 只负责把已验证证据组织成自然语言，连接失败会自动回退到确定性 Synthesizer，不影响数据查询和拒答策略。
