---
name: knowledge-search
description: 从知识库检索历史案例、SOP文档、解决方案，支持向量相似度检索和关键词混合检索
---

# Knowledge Search Skill

知识检索 Skill，支持从向量数据库检索历史案例和 SOP。

## 功能说明

| Action | 描述 | 返回结果 |
|--------|------|---------|
| `search_similar` | 相似案例检索 | 相似度排序的案例列表 |
| `find_sop` | SOP 查找 | 匹配的 SOP 文档 |
| `get_recommendations` | 推荐方案 | 解决方案建议 |

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    Query Processing                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Query     │───▶│  Embedding  │───▶│   Vector    │  │
│  │   Text      │    │   (BGE-M3)  │    │   Search    │  │
│  └─────────────┘    └─────────────┘    └─────────────┘  │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                    Hybrid Retrieval                      │
│                                                          │
│   Vector Score (70%)  +  Keyword Score (30%)             │
│                                                          │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                     Qdrant Vector DB                     │
│                                                          │
│   Collections:                                           │
│   - oncall_tickets (历史工单)                            │
│   - sop_documents (SOP 文档)                             │
│   - solutions (解决方案)                                  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## 使用方式

### 1. 相似案例检索

```bash
gdpa-cli run knowledge-search --action search_similar \
  --query "新加坡区域网络延迟突增" \
  --top-k 5 \
  --doc-type ticket
```

**参数说明:**
- `query`: 查询文本
- `top_k`: 返回数量 (默认 5)
- `doc_type`: 文档类型 (ticket/sop/solution)
- `filters`: 过滤条件 (JSON 格式)

**返回示例:**

```json
{
  "results": [
    {
      "doc_id": "TK-12345",
      "title": "新加坡区域网络延迟异常",
      "content": "问题描述: 2025-01-10 新加坡区域...",
      "score": 0.92,
      "metadata": {
        "severity": "critical",
        "psm": "example.service",
        "resolution_time_minutes": 45
      }
    }
  ],
  "query_vector_dimension": 1024,
  "total_searched": 10000
}
```

### 2. SOP 查找

```bash
gdpa-cli run knowledge-search --action find_sop \
  --query "延迟排查" \
  --category network
```

**返回匹配的 SOP 文档:**

```json
{
  "results": [
    {
      "doc_id": "SOP-001",
      "title": "网络延迟排查流程",
      "steps": [
        "1. 确认延迟范围和影响",
        "2. 查询网络测量数据",
        "3. 检查链路状态",
        "4. 分析历史案例",
        "5. 执行解决方案"
      ],
      "score": 0.88
    }
  ]
}
```

### 3. 获取推荐方案

```bash
gdpa-cli run knowledge-search --action get_recommendations \
  --query "网络延迟突增" \
  --context '{"region": "Singapore", "psm": "example.service"}'
```

**返回推荐的解决方案:**

```json
{
  "recommendations": [
    {
      "source": "TK-12345",
      "solution": "重启链路设备，流量切换到备用路径",
      "confidence": 0.85
    },
    {
      "source": "SOP-001",
      "solution": "按照网络延迟排查流程执行",
      "confidence": 0.78
    }
  ]
}
```

## 数据导入

### 导入历史工单

```python
from v1.knowledge import TicketParser, BGEEmbedding, QdrantRetriever

# 初始化
parser = TicketParser()
embedding = BGEEmbedding()
retriever = QdrantRetriever()

# 解析工单
doc = parser.parse(raw_ticket_content)

# 生成向量
vector = embedding.embed_single(doc.content)

# 存入向量库
retriever.upsert(
    doc_id=doc.doc_id,
    vector=vector,
    content=doc.content,
    metadata=doc.metadata,
)
```

### 批量导入

```bash
python -m v1.scripts.import_knowledge \
  --source ./data/tickets \
  --type ticket \
  --collection oncall_tickets
```

## 向量配置

```yaml
# v1/config/qdrant.yaml
collections:
  oncall_tickets:
    vector_size: 1024
    distance: Cosine

  sop_documents:
    vector_size: 1024
    distance: Cosine

embedding:
  model: BAAI/bge-m3
  max_length: 8192
  device: cpu  # 或 cuda

retrieval:
  vector_weight: 0.7
  keyword_weight: 0.3
  default_top_k: 5
```

## 性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 查询延迟 | < 50ms | P95 延迟 |
| 召回率 | > 85% | Top-5 召回率 |
| 准确率 | > 80% | 相关性评估 |

## 典型场景

### 场景1: 新告警匹配历史案例

```python
# 收到新告警
alert = {
    "title": "US-East 区域服务超时",
    "description": "大量请求超时...",
    "psm": "example.service"
}

# 构建查询
query = f"{alert['title']} {alert['description']}"

# 检索相似案例
results = knowledge_search.search_similar(query, top_k=3)

# 查看解决方案
for r in results:
    print(f"案例 {r.doc_id}: {r.metadata.get('solution')}")
```

### 场景2: 查找操作手册

```python
# 需要 SOP 指导
query = "如何排查 DNS 解析失败"

# 查找 SOP
sops = knowledge_search.find_sop(query, category="network")

# 按步骤执行
for sop in sops:
    print(f"SOP: {sop.title}")
    for step in sop.steps:
        print(f"  {step}")
```

## 依赖

- Qdrant (向量数据库)
- BGE-M3 (Embedding 模型)
- Python 3.9+
- qdrant-client
- FlagEmbedding (可选)
