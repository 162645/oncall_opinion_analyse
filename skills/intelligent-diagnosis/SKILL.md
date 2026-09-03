---
name: intelligent-diagnosis
description: 智能故障诊断，自动关联日志、指标、链路数据，结合知识库检索历史案例，定位根因并生成解决方案
---

# Intelligent Diagnosis Skill

智能故障诊断 Skill，实现多 Agent 协作诊断故障。

## 功能说明

| Action | 描述 | 输出 |
|--------|------|------|
| `diagnose_alert` | 诊断告警 | 根因分析报告 |
| `correlate_data` | 关联分析 | 数据关联结果 |
| `generate_report` | 生成报告 | 诊断报告文档 |

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                  Agent Orchestrator                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  Knowledge   │  │   Analysis   │  │  Diagnosis   │   │
│  │    Agent     │──│    Agent     │──│    Agent     │   │
│  │              │  │              │  │              │   │
│  │ 检索历史案例 │  │ 分析网络数据 │  │ 综合诊断     │   │
│  │ 匹配 SOP    │  │ 查询异常事件 │  │ 生成建议     │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│         │                  │                  │          │
│         ▼                  ▼                  ▼          │
│  ┌─────────────────────────────────────────────────┐    │
│  │              RAG Knowledge Base                  │    │
│  │         (Qdrant + BGE-M3 Embedding)             │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## 使用方式

### 1. 诊断告警

```bash
gdpa-cli run intelligent-diagnosis --action diagnose_alert \
  --alert-id "ALT-12345" \
  --alert-title "网络延迟突增" \
  --psm "example.service" \
  --region "Singapore-Central"
```

**执行流程:**

1. **Knowledge Agent** 检索相似历史案例
2. **Analysis Agent** 查询网络测量数据
3. **Diagnosis Agent** 综合分析，定位根因
4. 生成诊断报告

**输出示例:**

```json
{
  "session_id": "diag-20250115-001",
  "root_cause": {
    "category": "network",
    "subcategory": "latency",
    "description": "网络延迟异常，由链路拥塞导致",
    "confidence": 0.88
  },
  "evidence": [
    {
      "source": "network_telemetry",
      "type": "latency_anomaly",
      "avg_latency_ms": 150.5,
      "baseline_ms": 45.2
    },
    {
      "source": "knowledge_base",
      "type": "similar_case",
      "doc_id": "TK-12345"
    }
  ],
  "recommendations": [
    "1. 检查链路拥塞情况",
    "2. 查看历史案例 TK-12345 的解决方案",
    "3. 联系网络运维团队"
  ]
}
```

### 2. 关联分析

```bash
gdpa-cli run intelligent-diagnosis --action correlate_data \
  --session-id "diag-20250115-001"
```

对已诊断的告警进行深度关联分析。

### 3. 生成报告

```bash
gdpa-cli run intelligent-diagnosis --action generate_report \
  --session-id "diag-20250115-001" \
  --format markdown
```

## 诊断模型

### 根因分类

| 类别 | 子类别 | 典型原因 |
|------|--------|---------|
| network | latency | 链路拥塞、设备故障、路由异常 |
| network | packet_loss | 设备故障、链路质量差 |
| network | connection | 防火墙规则、连接数超限 |
| service | overload | 容量不足、流量突发 |
| service | error | 代码缺陷、配置错误 |

### 置信度计算

```
confidence = w1 * knowledge_similarity
           + w2 * data_anomaly_score
           + w3 * pattern_match_score
```

权重默认:
- `w1 = 0.35` (知识相似度)
- `w2 = 0.40` (数据异常分数)
- `w3 = 0.25` (模式匹配分数)

## 与其他 Skill 协作

### 与 network-telemetry 协作

```python
# 诊断前先获取网络数据
gdpa-cli run network-telemetry --action query_anomalies

# 再进行诊断
gdpa-cli run intelligent-diagnosis --action diagnose_alert
```

### 与 knowledge-search 协作

```python
# 诊断时自动调用知识检索
# 也可手动检索更多案例
gdpa-cli run knowledge-search --query "延迟突增"
```

## 配置

诊断行为可通过配置调整:

```yaml
# v1/config/diagnosis.yaml
agents:
  knowledge:
    enabled: true
    top_k: 5
    similarity_threshold: 0.7

  analysis:
    enabled: true
    time_range_hours: 1

  diagnosis:
    enabled: true
    confidence_threshold: 0.6

workflow:
  - knowledge
  - analysis
  - diagnosis
```

## 依赖

- Python 3.9+
- CrewAI / LangChain (可选，用于复杂编排)
- v1/agents/ 模块
- v1/knowledge/ 模块
