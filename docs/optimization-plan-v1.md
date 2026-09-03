# Oncall Opinion Analyse Agent 优化计划 v1.0

> **文档版本**: 1.0  
> **创建日期**: 2025-05-19  
> **目标**: 将项目从基础回调服务升级为智能运维 Agent 平台

---

## 目录

1. [为什么做](#一为什么做)
2. [现状分析](#二现状分析)
3. [技术方案全景图](#三技术方案全景图)
4. [开源项目复用清单](#四开源项目复用清单)
5. [详细技术选型与对比](#五详细技术选型与对比)
6. [实验验证计划](#六实验验证计划)
7. [最终方案选择](#七最终方案选择)
8. [实施路线图](#八实施路线图)
9. [代码组织结构](#九代码组织结构)
10. [附录](#十附录)

---

## 一、为什么做

### 1.1 业务痛点

| 痛点 | 现状 | 影响 |
|------|------|------|
| **故障诊断效率低** | 人工查询多个系统（Argos、Metrics、Trace），手动关联分析 | MTTR 平均 2-4 小时 |
| **知识无法复用** | 历史故障处理经验散落在工单、Wiki、聊天记录 | 相似故障重复排查 |
| **网络数据分析门槛高** | ClickHouse 数据需要写 SQL 查询，非技术人员无法使用 | 数据价值未释放 |
| **告警噪声严重** | 缺乏智能聚合，大量无效告警 | Oncall 疲劳，遗漏真实问题 |
| **跨系统集成困难** | 多个运维工具独立运作，缺乏统一入口 | 操作繁琐，效率低下 |

### 1.2 行业趋势

根据 Gartner 和 IDC 的预测：

| 指标 | 数据 | 来源 |
|------|------|------|
| AIOps 市场规模 | 2024 年 $54 亿 → 2030 年 $500 亿，CAGR 45% | [Market Research](https://aimultiple.com/agentic-frameworks) |
| AI Agent 采用率 | 2025 年 60% 企业将 AI Agent 集成到 CI/CD | [ODSC](https://odsc.medium.com/top-10-open-source-ai-agent-frameworks-to-know-in-2025-c739854ec859) |
| 组织使用 AI 编码 Agent | 2025 年达 82%，较 2024 年初 50% 大幅增长 | [Dev.to](https://dev.to/hemankumar6/i-built-an-open-source-llm-agent-evaluation-tool-that-works-with-any-framework-55h) |

### 1.3 预期收益

| 收益类型 | 指标 | 预期提升 |
|---------|------|---------|
| **效率** | 故障诊断时间 | 降低 60-80% |
| **质量** | 故障根因定位准确率 | 提升至 85%+ |
| **体验** | Oncall 工作量 | 减少 40% |
| **价值** | 数据利用率 | 提升 3-5 倍 |

### 1.4 为什么选择 Agent 架构

```
传统运维工具:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Argos     │    │   Metrics   │    │   Trace     │
│  (日志)     │    │  (指标)     │    │  (链路)     │
└─────────────┘    └─────────────┘    └─────────────┘
       ↑                  ↑                  ↑
       └──────────────────┴──────────────────┘
                    人工切换、手动关联

Agent 架构:
┌─────────────────────────────────────────────────────┐
│                  Orchestrator Agent                 │
│            (自动协调、智能推理、知识驱动)             │
└─────────────────────────────────────────────────────┘
       ↓                  ↓                  ↓
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Argos     │    │   Metrics   │    │   Trace     │
│   Skill     │    │   Skill     │    │   Skill     │
└─────────────┘    └─────────────┘    └─────────────┘
                    统一入口、自动关联
```

---

## 二、现状分析

### 2.1 现有资产盘点

#### Skills 清单 (86 个)

| 类别 | Skills | 完善度 |
|------|--------|--------|
| **可观测性** | argos-alarm, argos-query, argos-dashboard, metrics, trace-query, bytedtrace-knowledge | ⭐⭐⭐⭐⭐ |
| **开发效能** | bits-devops, bits-dev-workflow, devflow, bam-api, bam-query, base-workflow | ⭐⭐⭐⭐⭐ |
| **基础设施** | tcc-query, tcc-deploy, aeolus, tos, redis, abase, rds | ⭐⭐⭐⭐ |
| **知识库** | ttadk-knowledge, kitex-knowledge, hertz-knowledge, gdp-knowledge, overpass-knowledge | ⭐⭐⭐ |
| **数据库** | (待集成) | ❌ |

#### 已有技术栈

| 组件 | 技术 | 状态 |
|------|------|------|
| Agent 框架 | TTADK (基于 Spec-Kit) | ✅ 已有 |
| 命令系统 | SDD Workflow | ✅ 已有 |
| 工具协议 | MCP (Model Context Protocol) | ✅ 已有 |
| 执行入口 | gdpa-cli | ✅ 已有 |
| 状态管理 | Session + status.json | ✅ 已有 |

### 2.2 缺失能力

| 能力 | 优先级 | 说明 |
|------|--------|------|
| **数据库连接** | P0 | 无法直接查询 ClickHouse 网络测量数据 |
| **知识库** | P0 | 无 RAG 检索，历史经验无法复用 |
| **智能诊断** | P0 | 无自动根因分析能力 |
| **多 Agent 协作** | P1 | 单 Agent 模式，复杂任务处理能力有限 |
| **可观测性** | P1 | Agent 行为无法追踪 |
| **告警智能处理** | P1 | 无告警聚合、降噪能力 |

---

## 三、技术方案全景图

### 3.1 总体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           用户交互层                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Claude Code │  │   Cursor    │  │   Web UI    │  │   Lark Bot  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          Agent 编排层                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Orchestrator Agent                            │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │   │
│  │  │ 任务分发  │ │ 状态管理  │ │ 工具路由  │ │ 结果聚合  │            │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐           │
│  │ Diagnosis  │ │  Knowledge │ │   Action   │ │  Analysis  │           │
│  │   Agent    │ │   Agent    │ │   Agent    │ │   Agent    │           │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          知识与数据层                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  RAG Engine │  │ Vector Store│  │ Knowledge   │  │  ClickHouse  │    │
│  │  (检索增强)  │  │  (向量存储)  │  │   Graph     │  │  (时序数据)  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          工具与集成层                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    MCP Toolbox for Databases                    │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │   │
│  │  │ClickH. │ │ MySQL  │ │ Redis  │ │  ES    │ │BigQuery│        │   │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐           │
│  │ argos-alarm│ │  metrics   │ │trace-query │ │  aeolus    │           │
│  │   Skill    │ │   Skill    │ │   Skill    │ │   Skill    │           │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 技术选型矩阵

以下各维度均列出多个候选方案，供实验验证选择最优解。

---

## 四、开源项目复用清单

### 4.1 数据库连接层

| 项目 | GitHub | Stars | 特点 | 可复用程度 |
|------|--------|-------|------|-----------|
| **MCP Toolbox** | [googleapis/mcp-toolbox](https://github.com/googleapis/mcp-toolbox) | 15.3k | Google 官方，多数据库支持，企业级 | ⭐⭐⭐⭐⭐ |
| ClickHouse MCP | [ClickHouse/mcp-clickhouse](https://github.com/ClickHouse/mcp-clickhouse) | 2k+ | ClickHouse 官方，轻量 | ⭐⭐⭐⭐ |
| PostgreSQL MCP | [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) | 40k+ | Anthropic 官方 MCP 服务器合集 | ⭐⭐⭐⭐ |
| Redis MCP | [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) | 40k+ | 官方 Redis MCP | ⭐⭐⭐⭐ |
| Elasticsearch MCP | [elastic/mcp-server-elasticsearch](https://github.com/elastic/mcp-server-elasticsearch) | 500+ | Elastic 官方 | ⭐⭐⭐⭐ |

### 4.2 Agent 框架层

| 项目 | GitHub | Stars | 特点 | 适用场景 |
|------|--------|-------|------|---------|
| **LangChain** | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | 70k+ | 最成熟，工具链丰富 | 通用 Agent 开发 |
| **CrewAI** | [joaomdmoura/crewAI](https://github.com/joaomdmoura/crewAI) | 44k+ | 多 Agent 协作，角色分工 | 运维多 Agent 场景 |
| **AutoGen** | [microsoft/autogen](https://github.com/microsoft/autogen) | 35k+ | Microsoft，对话式协作 | 研究、复杂对话 |
| **OpenAI Agents SDK** | [openai/openai-agents-sdk](https://github.com/openai/openai-agents-sdk) | 19k+ | 轻量，100+ LLM 兼容 | 生产级 Agent |
| **Letta (MemGPT)** | [letta-ai/letta](https://github.com/letta-ai/letta) | 12k+ | 自编辑记忆，状态持久化 | 长期记忆 Agent |
| **LangGraph** | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | 10k+ | 状态图工作流 | 复杂工作流编排 |
| **DSPy** | [stanfordnlp/dspy](https://github.com/stanfordnlp/dspy) | 18k+ | 编程式 Prompt 优化 | Prompt 工程 |
| **SmolAgents** | [huggingface/smolagents](https://github.com/huggingface/smolagents) | 15k+ | HuggingFace，轻量 | 简单 Agent |

### 4.3 RAG 与知识库

| 项目 | GitHub | Stars | 特点 | 适用场景 |
|------|--------|-------|------|---------|
| **LlamaIndex** | [run-llama/llama_index](https://github.com/run-llama/llama_index) | 40k+ | 数据框架，RAG 优化 | 企业知识库 |
| **RAGFlow** | [infiniflow/ragflow](https://github.com/infiniflow/ragflow) | 30k+ | 开源 RAG 引擎，可视化 | 知识库管理 |
| **Langfuse** | [langfuse/langfuse](https://github.com/langfuse/langfuse) | 8k+ | LLM 可观测性 + RAG 评估 | 生产监控 |
| **Haystack** | [deepset-ai/haystack](https://github.com/deepset-ai/haystack) | 18k+ | NLP 框架，RAG 支持 | 文档问答 |
| **Chroma** | [chroma-core/chroma](https://github.com/chroma-core/chroma) | 15k+ | 向量数据库，嵌入式 | 本地向量存储 |
| **Qdrant** | [qdrant/qdrant](https://github.com/qdrant/qdrant) | 20k+ | 高性能向量数据库 | 大规模向量 |
| **Milvus** | [milvus-io/milvus](https://github.com/milvus-io/milvus) | 30k+ | 分布式向量数据库 | 企业级向量 |
| **Weaviate** | [weaviate/weaviate](https://github.com/weaviate/weaviate) | 12k+ | 向量搜索引擎 | 混合检索 |
| **Pinecone** | [pinecone-io/pinecone-python-client](https://github.com/pinecone-io/pinecone-python-client) | 3k+ | 托管向量数据库 | 云服务 |
| **FAISS** | [facebookresearch/faiss](https://github.com/facebookresearch/faiss) | 30k+ | Meta 向量检索库 | 本地向量 |

### 4.4 知识图谱

| 项目 | GitHub | Stars | 特点 |
|------|--------|-------|------|
| **Neo4j** | [neo4j/neo4j](https://github.com/neo4j/neo4j) | 13k+ | 图数据库，知识图谱 |
| **NebulaGraph** | [vesoft-inc/nebula](https://github.com/vesoft-inc/nebula) | 8k+ | 分布式图数据库 |
| **NetworkX** | [networkx/networkx](https://github.com/networkx/networkx) | 15k+ | Python 图分析库 |
| **PyKEEN** | [pykeen/pykeen](https://github.com/pykeen/pykeen) | 1k+ | 知识图谱嵌入 |

### 4.5 文档解析

| 项目 | GitHub | Stars | 特点 | 支持格式 |
|------|--------|-------|------|---------|
| **Unstructured** | [Unstructured-IO/unstructured](https://github.com/Unstructured-IO/unstructured) | 10k+ | 非结构化数据解析 | PDF, DOCX, PPT, HTML, Markdown |
| **LangChain Doc Loaders** | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | 70k+ | 100+ 文档加载器 | 全格式 |
| **PyMuPDF** | [pymupdf/PyMuPDF](https://github.com/pymupdf/PyMuPDF) | 5k+ | PDF 解析 | PDF |
| **python-docx** | [python-openxml/python-docx](https://github.com/python-openxml/python-docx) | 2k+ | Word 文档 | DOCX |
| **python-pptx** | [scanny/python-pptx](https://github.com/scanny/python-pptx) | 2k+ | PPT 文档 | PPTX |
| **BeautifulSoup** | [waylan/beautifulsoup](https://github.com/waylan/beautifulsoup) | 6k+ | HTML/XML 解析 | HTML, XML |
| **MarkItDown** | [microsoft/markitdown](https://github.com/microsoft/markitdown) | 5k+ | Microsoft 文档转 Markdown | 全格式 |

### 4.6 Embedding 模型

| 模型 | 来源 | 维度 | 特点 |
|------|------|------|------|
| **text-embedding-3-large** | OpenAI | 3072 | 最高质量，付费 |
| **text-embedding-3-small** | OpenAI | 1536 | 平衡性价比 |
| **bge-large-zh** | BAAI | 1024 | 中文最优，开源 |
| **bge-m3** | BAAI | 1024 | 多语言，长文本 |
| **e5-large-v2** | Microsoft | 1024 | 高质量，开源 |
| **sentence-transformers** | SBERT | 768 | 通用，开源 |
| **Cohere Embed** | Cohere | 1024 | 企业级，API |

### 4.7 可观测性

| 项目 | GitHub | Stars | 特点 |
|------|--------|-------|------|
| **Langfuse** | [langfuse/langfuse](https://github.com/langfuse/langfuse) | 8k+ | LLM 可观测性，开源 |
| **LangSmith** | [langchain-ai/langsmith-sdk](https://github.com/langchain-ai/langsmith-sdk) | 2k+ | LangChain 官方 |
| **Arize Phoenix** | [Arize-ai/phoenix](https://github.com/Arize-ai/phoenix) | 5k+ | AI 可观测性 |
| **OpenLIT** | [openlit/openlit](https://github.com/openlit/openlit) | 2k+ | OpenTelemetry 原生 |
| **Helicone** | [Helicone/helicone](https://github.com/Helicone/helicone) | 3k+ | LLM 网关 + 监控 |

### 4.8 论文参考

| 论文 | 会议/年份 | 核心贡献 | GitHub |
|------|----------|---------|--------|
| **[RCAgent](https://arxiv.org/html/2310.16340v3)** | 阿里云 | 工具增强 RCA Agent | - |
| **[Flow-of-Action](https://arxiv.org/html/2502.08224v1)** | WWW 2025 | SOP 增强 RCA | - |
| **[mABC](https://arxiv.org/)** | EMNLP 2024 | 多 Agent 区块链协作 | - |
| **[Self-RAG](https://arxiv.org/abs/2310.05506)** | ICLR 2024 | 自主检索决策 | - |
| **[Corrective RAG](https://arxiv.org/abs/2401.15884)** | arXiv 2024 | 纠正性检索 | - |
| **[Agentic RAG](https://arxiv.org/)** | arXiv 2024 | Agent 化检索 | - |

### 4.9 Awesome 列表

| 资源 | GitHub | 内容 |
|------|--------|------|
| **awesome-mcp-servers** | [TensorBlock/awesome-mcp-servers](https://github.com/TensorBlock/awesome-mcp-servers) | 7260+ MCP 服务器 |
| **awesome-LLM-AIOps** | [Jun-jie-Huang/awesome-LLM-AIOps](https://github.com/Jun-jie-Huang/awesome-LLM-AIOps) | LLM + AIOps 论文 |
| **Awesome-LLMOps** | [tensorchord/Awesome-LLMOps](https://github.com/tensorchord/Awesome-LLMOps) | LLMOps 工具 |
| **awesome-llm-agents** | [kaushikb11/awesome-llm-agents](https://github.com/kaushikb11/awesome-llm-agents) | LLM Agent 资源 |

---

## 五、详细技术选型与对比

### 5.1 数据库连接方案

#### 方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| **方案 A: MCP Toolbox** | 多数据库支持、连接池、OAuth2、OpenTelemetry | 需要部署服务、配置复杂 | 企业级、多数据源 |
| **方案 B: ClickHouse 官方 MCP** | 轻量、简单、官方维护 | 仅支持 ClickHouse | 单数据库场景 |
| **方案 C: 自建 MCP Server** | 完全可控、定制化 | 开发成本高 | 特殊需求 |

#### MCP Toolbox 详细配置

```yaml
# tools.yaml
kind: sources
name: clickhouse-network
type: clickhouse
host: ${CLICKHOUSE_HOST}
port: "8123"
database: network_telemetry
user: ${CLICKHOUSE_USER}
password: ${CLICKHOUSE_PASSWORD}
protocol: https
secure: true

---
kind: sources
name: mysql-config
type: mysql
host: ${MYSQL_HOST}
port: "3306"
database: oncall_config
user: ${MYSQL_USER}
password: ${MYSQL_PASSWORD}

---
kind: sources
name: redis-cache
type: redis
host: ${REDIS_HOST}
port: "6379"
password: ${REDIS_PASSWORD}

---
kind: tools
name: query-network-latency
type: clickhouse-execute-sql
source: clickhouse-network
description: "查询网络延迟数据"
parameters:
  - name: start_time
    type: string
  - name: end_time
    type: string
  - name: source_region
    type: string
    required: false
statement: |
  SELECT 
    timestamp,
    source_region,
    target_region,
    avg_latency_ms,
    p99_latency_ms,
    packet_loss_rate
  FROM network_latency
  WHERE timestamp BETWEEN {start_time} AND {end_time}
    AND ({source_region} = '' OR source_region = {source_region})
  ORDER BY timestamp
  LIMIT 1000

---
kind: tools
name: query-anomaly-events
type: clickhouse-execute-sql
source: clickhouse-network
description: "查询异常事件"
parameters:
  - name: time_range
    type: integer
    description: "时间范围（分钟）"
statement: |
  SELECT 
    event_time,
    event_type,
    severity,
    source_ip,
    target_ip,
    details
  FROM network_events
  WHERE event_time > now() - INTERVAL {time_range} MINUTE
    AND severity IN ('warning', 'critical')
  ORDER BY event_time DESC
```

### 5.2 RAG 方案对比

#### 架构方案

| 方案 | 架构 | 优点 | 缺点 |
|------|------|------|------|
| **Simple RAG** | Query → Embedding → Vector Search → LLM | 简单、快速 | 无推理能力 |
| **Self-RAG** | Query → 思考 → 检索决策 → 检索 → 评估 → 生成 | 减少幻觉、自主决策 | 复杂度高 |
| **Corrective RAG** | Query → 检索 → 评估 → 纠正 → 生成 | 提高准确性 | 额外评估步骤 |
| **Agentic RAG** | Query → Agent 规划 → 多轮检索 → 推理 → 生成 | 复杂查询支持 | 延迟高 |
| **Graph RAG** | Query → 知识图谱检索 + 向量检索 → 融合 → 生成 | 关系推理强 | 图谱构建成本高 |

#### RAG 流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                    Agentic RAG 架构 (推荐)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  用户查询                                                       │
│     │                                                          │
│     ▼                                                          │
│  ┌─────────────┐                                               │
│  │ Query Agent │ ← 分析意图、拆解问题                           │
│  └─────────────┘                                               │
│     │                                                          │
│     ├─── 需要检索？ ─── 否 ──→ 直接回答                         │
│     │                                                          │
│     ▼ 是                                                       │
│  ┌─────────────┐                                               │
│  │Retrieval    │ ← 决定检索哪些知识源                           │
│  │Planner      │                                               │
│  └─────────────┘                                               │
│     │                                                          │
│     ├──────────────┬──────────────┬──────────────┐            │
│     ▼              ▼              ▼              ▼            │
│  ┌───────┐    ┌───────┐    ┌───────┐    ┌───────┐            │
│  │Vector │    │Graph  │    │Web    │    │Docs   │            │
│  │Search │    │Search │    │Search │    │Search │            │
│  └───────┘    └───────┘    └───────┘    └───────┘            │
│     │              │              │              │            │
│     └──────────────┴──────────────┴──────────────┘            │
│                         │                                      │
│                         ▼                                      │
│                  ┌─────────────┐                               │
│                  │ Reranker    │ ← 重排序、去重                │
│                  └─────────────┘                               │
│                         │                                      │
│                         ▼                                      │
│                  ┌─────────────┐                               │
│                  │Relevance    │ ← 相关性评估                  │
│                  │Judge        │                               │
│                  └─────────────┘                               │
│                         │                                      │
│          ┌──────────────┴──────────────┐                      │
│          ▼                              ▼                      │
│      相关性足够？                   不够？                      │
│          │                              │                      │
│          ▼                              ▼                      │
│    ┌───────────┐               ┌─────────────┐                │
│    │ Generation│               │ 迭代检索    │                │
│    └───────────┘               └─────────────┘                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 向量存储方案对比

| 存储 | 部署方式 | 性能 | 规模 | 成本 | 推荐场景 |
|------|---------|------|------|------|---------|
| **Chroma** | 嵌入式 | 中 | 小(<1M) | 免费 | 开发测试、小规模 |
| **Qdrant** | 自托管/云 | 高 | 中(<10M) | 低 | 中等规模、生产 |
| **Milvus** | 分布式 | 极高 | 大(>10M) | 中 | 大规模、企业级 |
| **Weaviate** | 自托管/云 | 高 | 中 | 中 | 混合检索 |
| **Pinecone** | 云服务 | 高 | 大 | 高 | 无运维需求 |
| **FAISS** | 嵌入式 | 极高 | 中 | 免费 | 本地高性能 |

#### 向量存储选择决策树

```
开始
  │
  ├── 数据量 < 100万？
  │     │
  │     ├── 是 ──→ 开发测试？
  │     │            │
  │     │            ├── 是 ──→ Chroma (嵌入式，零配置)
  │     │            │
  │     │            └── 否 ──→ 需要持久化？
  │     │                         │
  │     │                         ├── 是 ──→ Qdrant (单机部署)
  │     │                         │
  │     │                         └── 否 ──→ FAISS (内存)
  │     │
  │     └── 否 ──→ 数据量 < 1000万？
  │                  │
  │                  ├── 是 ──→ Qdrant 集群 / Weaviate
  │                  │
  │                  └── 否 ──→ Milvus / Pinecone
```

### 5.4 多 Agent 协作方案对比

| 框架 | 协作模式 | 状态管理 | 工具支持 | 学习曲线 | 生产就绪 |
|------|---------|---------|---------|---------|---------|
| **CrewAI** | 角色分工 | 简单 | 丰富 | 低 | ⭐⭐⭐⭐ |
| **AutoGen** | 对话驱动 | 复杂 | 丰富 | 中 | ⭐⭐⭐ |
| **LangGraph** | 状态图 | 强大 | 最丰富 | 高 | ⭐⭐⭐⭐⭐ |
| **OpenAI Agents SDK** | 轻量 | 简单 | 中等 | 低 | ⭐⭐⭐⭐ |

#### CrewAI 架构示例

```python
from crewai import Agent, Task, Crew, Process
from crewai_tools import tool

# 定义诊断 Agent
diagnosis_agent = Agent(
    role="故障诊断专家",
    goal="分析告警、日志、指标，定位根因",
    backstory="你是一位经验丰富的运维专家，擅长故障诊断",
    tools=[argos_query_tool, metrics_tool, trace_query_tool],
    verbose=True
)

# 定义知识检索 Agent
knowledge_agent = Agent(
    role="知识检索专家",
    goal="从知识库检索历史案例和解决方案",
    backstory="你熟悉所有历史故障处理记录",
    tools=[rag_search_tool, wiki_search_tool],
    verbose=True
)

# 定义行动 Agent
action_agent = Agent(
    role="处置执行专家",
    goal="生成处置建议并执行自动化修复",
    backstory="你擅长执行故障恢复操作",
    tools=[runbook_tool, automation_tool],
    verbose=True
)

# 定义任务
diagnosis_task = Task(
    description="分析告警 {alert_id}，查询相关日志和指标",
    agent=diagnosis_agent,
    expected_output="根因分析报告"
)

knowledge_task = Task(
    description="检索历史相似案例和解决方案",
    agent=knowledge_agent,
    context=[diagnosis_task],  # 依赖诊断结果
    expected_output="历史案例和推荐方案"
)

action_task = Task(
    description="生成处置建议",
    agent=action_agent,
    context=[diagnosis_task, knowledge_task],
    expected_output="处置建议和执行步骤"
)

# 组建 Crew
crew = Crew(
    agents=[diagnosis_agent, knowledge_agent, action_agent],
    tasks=[diagnosis_task, knowledge_task, action_task],
    process=Process.sequential,  # 顺序执行
    verbose=True
)

# 执行
result = crew.kickoff(inputs={"alert_id": "alert-12345"})
```

### 5.5 文档解析方案对比

| 方案 | 支持格式 | OCR | 表格解析 | 结构化输出 |
|------|---------|-----|---------|-----------|
| **Unstructured** | 全格式 | ✅ | ✅ | ✅ |
| **LangChain Loaders** | 全格式 | 部分 | 部分 | ✅ |
| **PyMuPDF** | PDF | ❌ | ✅ | ✅ |
| **MarkItDown** | 全格式 | ❌ | ✅ | ✅ |

#### Unstructured 解析流程

```python
from unstructured.partition.auto import partition
from unstructured.chunking.title import chunk_by_title

# 解析文档
elements = partition(
    filename="incident_report.pdf",
    strategy="hi_res",  # 高精度模式
    extract_images_in_pdf=True,  # 提取图片
    infer_table_structure=True,  # 解析表格结构
)

# 分块
chunks = chunk_by_title(
    elements,
    max_characters=1000,
    new_after_n_chars=800,
)

# 转换为向量存储格式
documents = []
for chunk in chunks:
    documents.append({
        "content": chunk.text,
        "metadata": {
            "source": "incident_report.pdf",
            "page_number": chunk.metadata.page_number,
            "category": chunk.category,  # Title, Narrative, Table, etc.
        }
    })
```

### 5.6 Embedding 模型对比

| 模型 | MTEB 排名 | 中文支持 | 长度 | 成本 | 推荐场景 |
|------|----------|---------|------|------|---------|
| **text-embedding-3-large** | Top 3 | ⭐⭐⭐ | 8191 | 高 | 高质量英文 |
| **bge-large-zh** | Top 10 | ⭐⭐⭐⭐⭐ | 512 | 免费 | 中文最优 |
| **bge-m3** | Top 15 | ⭐⭐⭐⭐⭐ | 8192 | 免费 | 多语言、长文本 |
| **e5-large-v2** | Top 10 | ⭐⭐⭐⭐ | 512 | 免费 | 平衡性价比 |

### 5.7 知识图谱方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| **Neo4j** | 成熟、Cypher 强大 | 商业版收费 | 复杂关系推理 |
| **NebulaGraph** | 分布式、开源 | 学习曲线高 | 大规模图谱 |
| **NetworkX** | 轻量、Python 原生 | 无持久化 | 内存分析 |
| **内存图谱 + 向量** | 简单、快速 | 规模受限 | 小规模关系 |

---

## 六、实验验证计划

### 6.1 实验一：数据库连接方案验证

**目的**：验证 MCP Toolbox vs ClickHouse 官方 MCP 的性能差异

**实验设计**：

```yaml
实验环境:
  - ClickHouse: 单节点，1000万网络测量记录
  - 测试查询: 5种典型查询（简单/复杂/聚合/时间范围/多表Join）
  - 测试次数: 每种查询100次

评估指标:
  - 连接建立时间
  - 查询延迟（P50/P99）
  - 并发能力（10/50/100并发）
  - 内存占用
  - 错误率

实验代码位置: experiments/exp-01-database-connection/
```

**预期结果**：

| 指标 | MCP Toolbox | ClickHouse MCP |
|------|-------------|----------------|
| 连接池 | ✅ 内置 | ❌ 无 |
| 并发稳定性 | 高 | 中 |
| 单查询延迟 | 略高（中间层） | 更低 |
| 功能丰富度 | 高 | 低 |

### 6.2 实验二：RAG 检索效果验证

**目的**：验证不同 RAG 架构的检索效果

**实验设计**：

```yaml
数据集:
  - 历史工单: 1000条
  - Wiki文档: 200篇
  - SOP文档: 50篇

测试问题:
  - 简单查询: 50个（单文档答案）
  - 复杂查询: 30个（多文档综合）
  - 推理查询: 20个（需要推理）

对比方案:
  - Simple RAG
  - Self-RAG
  - Agentic RAG

评估指标:
  - 检索准确率 (Recall@5, Recall@10)
  - 回答准确率
  - 幻觉率
  - 平均延迟

实验代码位置: experiments/exp-02-rag-evaluation/
```

### 6.3 实验三：向量存储性能验证

**目的**：验证不同向量存储的性能

**实验设计**：

```yaml
数据规模:
  - 小规模: 10万向量
  - 中规模: 100万向量
  - 大规模: 1000万向量

测试操作:
  - 写入吞吐量
  - 查询延迟（P50/P99）
  - 并发查询能力
  - 内存/磁盘占用

对比方案:
  - Chroma
  - Qdrant
  - Milvus
  - FAISS

实验代码位置: experiments/exp-03-vector-store/
```

### 6.4 实验四：多 Agent 协作验证

**目的**：验证不同 Agent 框架的效果

**实验设计**：

```yaml
测试场景:
  - 场景1: 单告警诊断
  - 场景2: 复杂故障排查（多系统关联）
  - 场景3: 自动化修复执行

对比框架:
  - CrewAI
  - AutoGen
  - LangGraph

评估指标:
  - 任务完成率
  - 平均执行时间
  - 资源消耗
  - 代码复杂度

实验代码位置: experiments/exp-04-multi-agent/
```

### 6.5 实验五：Embedding 模型验证

**目的**：验证不同 Embedding 模型在运维知识上的效果

**实验设计**：

```yaml
测试数据:
  - 中文工单: 500条
  - 英文文档: 200篇
  - 混合内容: 100条

测试任务:
  - 相似问题检索
  - 文档分类
  - 语义搜索

对比模型:
  - text-embedding-3-large
  - bge-large-zh
  - bge-m3
  - e5-large-v2

评估指标:
  - 检索准确率 (MRR, NDCG)
  - 延迟
  - 成本

实验代码位置: experiments/exp-05-embedding/
```

---

## 七、最终方案选择

### 7.1 选择结果

基于技术调研和实验设计，选择以下方案：

| 模块 | 选择方案 | 选择理由 |
|------|---------|---------|
| **数据库连接** | MCP Toolbox | 多数据库支持、连接池、企业级特性 |
| **Agent 框架** | CrewAI + LangChain | CrewAI 多 Agent 协作成熟，LangChain 工具生态丰富 |
| **RAG 架构** | Agentic RAG | 支持复杂查询、多源检索、迭代推理 |
| **向量存储** | Qdrant | 平衡性能和规模，开源自托管 |
| **Embedding** | bge-m3 | 多语言支持、长文本、开源免费 |
| **文档解析** | Unstructured | 全格式支持、表格解析、结构化输出 |
| **知识图谱** | Neo4j（可选） | 复杂关系推理，后期引入 |
| **可观测性** | Langfuse | 开源、LLM 专用、RAG 评估支持 |

### 7.2 选择理由详解

#### 数据库连接：MCP Toolbox

```
选择理由:
1. 多数据库统一访问
   - ClickHouse: 网络测量数据
   - MySQL: 配置数据
   - Redis: 缓存
   - Elasticsearch: 日志
   
2. 企业级特性
   - 连接池管理，避免连接风暴
   - OAuth2 认证
   - OpenTelemetry 可观测性
   - SQL 注入防护
   
3. 工具自动生成
   - YAML 声明式配置
   - 自动生成参数化查询工具
   
4. 社区活跃
   - Google 官方维护
   - 15k+ Stars
   - 持续更新
```

#### RAG 架构：Agentic RAG

```
选择理由:
1. 适合运维场景
   - 故障诊断需要多源信息
   - 需要迭代推理
   - 复杂查询支持
   
2. 降低幻觉
   - Self-RAG 论文：幻觉率仅 5.8%
   - 相关性评估机制
   - 迭代检索校正
   
3. 灵活性
   - 可接入多种知识源
   - 支持工具调用
   - 可定制推理流程
```

#### 向量存储：Qdrant

```
选择理由:
1. 性能优异
   - Rust 实现，高性能
   - 支持 HNSW 索引
   - 毫秒级查询
   
2. 部署简单
   - Docker 一键部署
   - 支持嵌入式模式
   - 云服务可选
   
3. 功能丰富
   - 向量 + Payload 过滤
   - 支持量化压缩
   - 分布式支持
   
4. 开源免费
   - Apache 2.0 协议
   - 活跃社区
```

#### Embedding：bge-m3

```
选择理由:
1. 多语言支持
   - 中英文效果好
   - 适合混合内容
   
2. 长文本支持
   - 最大 8192 tokens
   - 适合长文档
   
3. 开源免费
   - BAAI 开源
   - 本地部署
   
4. 性能优秀
   - MTEB 排名靠前
   - 中文场景最优
```

---

## 八、实施路线图

### 8.1 阶段划分

```
Phase 0: 基础设施准备 (Week 1-2)
├── 搭建实验环境
├── 部署 MCP Toolbox
├── 部署 Qdrant
└── 部署 Langfuse

Phase 1: 数据库集成 (Week 3-4)
├── 配置 ClickHouse 数据源
├── 配置 MySQL 数据源
├── 配置 Redis 数据源
├── 编写常用查询工具
└── 编写测试用例

Phase 2: 知识库搭建 (Week 5-8)
├── 设计知识库结构
├── 实现文档解析流水线
├── 实现 Embedding 流水线
├── 实现 RAG 检索服务
├── 导入历史知识
└── 评估检索效果

Phase 3: Agent 开发 (Week 9-12)
├── 开发 Diagnosis Agent
├── 开发 Knowledge Agent
├── 开发 Action Agent
├── 实现多 Agent 协作
└── 集成测试

Phase 4: 集成与优化 (Week 13-16)
├── 集成到现有 TTADK 框架
├── 开发运维专用 Skills
├── 性能优化
├── 安全加固
└── 文档编写

Phase 5: 上线与迭代 (Week 17+)
├── 灰度发布
├── 用户反馈收集
├── 持续优化
└── 功能迭代
```

### 8.2 里程碑

| 里程碑 | 时间 | 产出 |
|--------|------|------|
| M1 | Week 2 | 实验环境就绪 |
| M2 | Week 4 | 数据库集成完成，可查询 ClickHouse |
| M3 | Week 8 | 知识库就绪，RAG 检索可用 |
| M4 | Week 12 | Agent 开发完成，可自动诊断故障 |
| M5 | Week 16 | 集成完成，可投入使用 |

---

## 九、代码组织结构

### 9.1 目录结构

```
oncall_opinion_analyse/
├── .claude/                    # 现有 Claude 配置
│   ├── skills/                 # 现有 Skills
│   └── ...
│
├── agent-extension/            # 【新增】Agent 扩展模块
│   │
│   ├── experiments/            # 实验代码
│   │   ├── exp-01-database-connection/
│   │   │   ├── README.md
│   │   │   ├── test_mcp_toolbox.py
│   │   │   ├── test_clickhouse_mcp.py
│   │   │   └── benchmark_results.json
│   │   │
│   │   ├── exp-02-rag-evaluation/
│   │   │   ├── README.md
│   │   │   ├── datasets/
│   │   │   ├── evaluators/
│   │   │   └── results/
│   │   │
│   │   ├── exp-03-vector-store/
│   │   ├── exp-04-multi-agent/
│   │   └── exp-05-embedding/
│   │
│   ├── config/                 # 配置文件
│   │   ├── tools.yaml          # MCP Toolbox 配置
│   │   ├── agents.yaml         # Agent 配置
│   │   ├── knowledge.yaml      # 知识库配置
│   │   └── embedding.yaml      # Embedding 配置
│   │
│   ├── mcp-servers/            # MCP 服务器
│   │   ├── toolbox/            # MCP Toolbox 配置
│   │   │   ├── tools.yaml
│   │   │   └── docker-compose.yml
│   │   └── custom/             # 自定义 MCP 服务器
│   │       └── knowledge-mcp/
│   │
│   ├── knowledge/              # 知识库模块
│   │   ├── parsers/            # 文档解析器
│   │   │   ├── __init__.py
│   │   │   ├── pdf_parser.py
│   │   │   ├── docx_parser.py
│   │   │   ├── wiki_parser.py
│   │   │   └── incident_parser.py
│   │   │
│   │   ├── embeddings/         # Embedding 模块
│   │   │   ├── __init__.py
│   │   │   ├── bge_embedder.py
│   │   │   └── openai_embedder.py
│   │   │
│   │   ├── chunkers/           # 分块策略
│   │   │   ├── __init__.py
│   │   │   ├── semantic_chunker.py
│   │   │   └── recursive_chunker.py
│   │   │
│   │   ├── retrievers/         # 检索器
│   │   │   ├── __init__.py
│   │   │   ├── vector_retriever.py
│   │   │   ├── hybrid_retriever.py
│   │   │   └── agentic_retriever.py
│   │   │
│   │   ├── loaders/            # 数据加载器
│   │   │   ├── __init__.py
│   │   │   ├── incident_loader.py
│   │   │   ├── wiki_loader.py
│   │   │   └── sop_loader.py
│   │   │
│   │   └── pipelines/          # ETL 流水线
│   │       ├── __init__.py
│   │       ├── ingestion_pipeline.py
│   │       └── update_pipeline.py
│   │
│   ├── agents/                 # Agent 实现
│   │   ├── core/               # 核心 Agent
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py
│   │   │   └── base_agent.py
│   │   │
│   │   ├── specialists/        # 专业 Agent
│   │   │   ├── __init__.py
│   │   │   ├── diagnosis_agent.py
│   │   │   ├── knowledge_agent.py
│   │   │   ├── analysis_agent.py
│   │   │   └── action_agent.py
│   │   │
│   │   ├── crews/              # CrewAI Crews
│   │   │   ├── __init__.py
│   │   │   ├── diagnosis_crew.py
│   │   │   └── investigation_crew.py
│   │   │
│   │   └── tools/              # Agent 工具
│   │       ├── __init__.py
│   │       ├── clickhouse_tools.py
│   │       ├── metrics_tools.py
│   │       ├── trace_tools.py
│   │       └── knowledge_tools.py
│   │
│   ├── skills/                 # 新增 Skills
│   │   ├── network-telemetry/  # 网络测量分析
│   │   │   ├── SKILL.md
│   │   │   └── references/
│   │   │
│   │   ├── intelligent-diagnosis/  # 智能诊断
│   │   │   ├── SKILL.md
│   │   │   └── references/
│   │   │
│   │   ├── knowledge-search/   # 知识检索
│   │   │   ├── SKILL.md
│   │   │   └── references/
│   │   │
│   │   └── alert-aggregation/  # 告警聚合
│   │       ├── SKILL.md
│   │       └── references/
│   │
│   ├── observability/          # 可观测性
│   │   ├── langfuse/           # Langfuse 集成
│   │   │   ├── config.py
│   │   │   └── tracer.py
│   │   │
│   │   └── metrics/            # 指标收集
│   │       ├── __init__.py
│   │       └── collector.py
│   │
│   ├── api/                    # API 服务
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI 主入口
│   │   ├── routes/
│   │   │   ├── diagnosis.py
│   │   │   ├── knowledge.py
│   │   │   └── telemetry.py
│   │   └── models/
│   │       ├── requests.py
│   │       └── responses.py
│   │
│   ├── scripts/                # 脚本
│   │   ├── setup.sh            # 环境初始化
│   │   ├── ingest_knowledge.py # 知识导入
│   │   └── run_experiments.py  # 运行实验
│   │
│   ├── tests/                  # 测试
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/
│   │
│   ├── docs/                   # 文档
│   │   ├── architecture.md
│   │   ├── deployment.md
│   │   ├── api.md
│   │   └── troubleshooting.md
│   │
│   ├── docker/                 # Docker 配置
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml
│   │   └── docker-compose.dev.yml
│   │
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── README.md
│
├── .mcp.json                    # MCP 配置（扩展）
├── Makefile                     # 构建命令
└── README.md
```

### 9.2 核心代码示例

#### 9.2.1 MCP Toolbox 配置 (agent-extension/config/tools.yaml)

```yaml
# ClickHouse 数据源 - 网络测量数据
kind: sources
name: clickhouse-network-telemetry
type: clickhouse
host: ${CLICKHOUSE_HOST}
port: ${CLICKHOUSE_PORT:-8123}
database: network_telemetry
user: ${CLICKHOUSE_USER}
password: ${CLICKHOUSE_PASSWORD}
protocol: https
secure: true

---
# MySQL 数据源 - 配置数据
kind: sources
name: mysql-oncall-config
type: mysql
host: ${MYSQL_HOST}
port: ${MYSQL_PORT:-3306}
database: oncall_config
user: ${MYSQL_USER}
password: ${MYSQL_PASSWORD}

---
# Redis 数据源 - 缓存
kind: sources
name: redis-cache
type: redis
host: ${REDIS_HOST}
port: ${REDIS_PORT:-6379}
password: ${REDIS_PASSWORD}

---
# 工具：查询网络延迟
kind: tools
name: query-network-latency
type: clickhouse-execute-sql
source: clickhouse-network-telemetry
description: |
  查询网络延迟指标数据，包括平均延迟、P99延迟、丢包率等。
  适用于故障诊断时的网络性能分析。
parameters:
  - name: start_time
    type: string
    description: "开始时间 (ISO 8601 格式，如 2025-01-01T00:00:00Z)"
    required: true
  - name: end_time
    type: string
    description: "结束时间 (ISO 8601 格式)"
    required: true
  - name: source_region
    type: string
    description: "源区域过滤 (可选)"
    required: false
  - name: target_region
    type: string
    description: "目标区域过滤 (可选)"
    required: false
statement: |
  SELECT 
    timestamp,
    source_region,
    target_region,
    avg_latency_ms,
    p99_latency_ms,
    p95_latency_ms,
    packet_loss_rate,
    throughput_mbps,
    connection_count
  FROM network_latency
  WHERE timestamp BETWEEN {start_time} AND {end_time}
    AND ({source_region} = '' OR source_region = {source_region})
    AND ({target_region} = '' OR target_region = {target_region})
  ORDER BY timestamp
  LIMIT 1000

---
# 工具：查询异常事件
kind: tools
name: query-network-anomalies
type: clickhouse-execute-sql
source: clickhouse-network-telemetry
description: |
  查询网络异常事件，包括延迟突增、丢包、连接失败等。
  用于故障诊断时快速定位异常时段。
parameters:
  - name: time_range_minutes
    type: integer
    description: "查询时间范围（分钟）"
    required: true
  - name: severity
    type: string
    description: "严重程度过滤 (warning/critical)"
    required: false
statement: |
  SELECT 
    event_time,
    event_type,
    severity,
    source_region,
    target_region,
    source_ip,
    target_ip,
    metric_value,
    threshold,
    details
  FROM network_events
  WHERE event_time > now() - INTERVAL {time_range_minutes} MINUTE
    AND ({severity} = '' OR severity = {severity})
  ORDER BY event_time DESC
  LIMIT 100

---
# 工具：查询流量统计
kind: tools
name: query-traffic-stats
type: clickhouse-execute-sql
source: clickhouse-network-telemetry
description: |
  查询流量统计信息，包括入站/出站流量、连接数等。
  用于容量分析和异常流量检测。
parameters:
  - name: start_time
    type: string
    required: true
  - name: end_time
    type: string
    required: true
  - name: granularity
    type: string
    description: "聚合粒度 (1m/5m/1h/1d)"
    required: false
statement: |
  SELECT 
    toStartOfInterval(timestamp, INTERVAL {granularity}) as time_bucket,
    source_region,
    sum(inbound_bytes) as total_inbound_bytes,
    sum(outbound_bytes) as total_outbound_bytes,
    avg(active_connections) as avg_connections,
    max(active_connections) as max_connections
  FROM traffic_stats
  WHERE timestamp BETWEEN {start_time} AND {end_time}
  GROUP BY time_bucket, source_region
  ORDER BY time_bucket
```

#### 9.2.2 知识库配置 (agent-extension/config/knowledge.yaml)

```yaml
# 知识库配置
knowledge_base:
  name: "oncall-knowledge"
  description: "Oncall 运维知识库"
  
  # 向量存储配置
  vector_store:
    type: qdrant
    host: ${QDRANT_HOST:-localhost}
    port: ${QDRANT_PORT:-6333}
    collection: oncall_knowledge
    embedding_dim: 1024  # bge-m3
    
  # 知识源配置
  sources:
    - name: incidents
      type: incident_records
      path: /data/incidents/
      parser: incident_parser
      chunk_size: 500
      chunk_overlap: 50
      
    - name: wiki
      type: wiki_documents
      path: /data/wiki/
      parser: wiki_parser
      chunk_size: 1000
      chunk_overlap: 100
      
    - name: sops
      type: sop_documents
      path: /data/sops/
      parser: sop_parser
      chunk_size: 800
      chunk_overlap: 80
      
    - name: runbooks
      type: runbook_documents
      path: /data/runbooks/
      parser: runbook_parser
      chunk_size: 1000
      chunk_overlap: 100
      
  # Embedding 配置
  embedding:
    model: bge-m3
    provider: local  # local / openai
    batch_size: 32
    max_length: 8192
    
  # 检索配置
  retrieval:
    top_k: 5
    score_threshold: 0.7
    reranker: bge-reranker-v2-m3
    hybrid_search: true
    hybrid_weights:
      vector: 0.7
      keyword: 0.3
      
  # 分块策略
  chunking:
    strategy: semantic  # semantic / recursive / fixed
    min_chunk_size: 100
    max_chunk_size: 1500
    overlap: 100
```

#### 9.2.3 Agent 配置 (agent-extension/config/agents.yaml)

```yaml
# Agent 配置
agents:
  # 编排 Agent
  orchestrator:
    name: "Orchestrator Agent"
    role: "任务编排与协调"
    model: claude-sonnet-4-6
    max_iterations: 10
    
  # 诊断 Agent
  diagnosis:
    name: "Diagnosis Agent"
    role: "故障诊断专家"
    goal: "分析告警、日志、指标，定位根因"
    backstory: |
      你是一位经验丰富的运维专家，擅长故障诊断。
      你能够综合分析多种数据源，快速定位问题根因。
    model: claude-sonnet-4-6
    tools:
      - query-network-latency
      - query-network-anomalies
      - argos-query
      - metrics
      - trace-query
    max_iterations: 15
    
  # 知识 Agent
  knowledge:
    name: "Knowledge Agent"
    role: "知识检索专家"
    goal: "从知识库检索历史案例和解决方案"
    backstory: |
      你熟悉所有历史故障处理记录和最佳实践。
      你能快速找到相似案例，提供解决方案参考。
    model: claude-sonnet-4-6
    tools:
      - knowledge-search
      - wiki-search
    max_iterations: 5
    
  # 分析 Agent
  analysis:
    name: "Analysis Agent"
    role: "数据分析专家"
    goal: "分析网络测量数据，识别异常模式"
    backstory: |
      你擅长分析网络性能数据，能够识别异常模式。
      你熟悉各种统计方法和机器学习技术。
    model: claude-sonnet-4-6
    tools:
      - query-network-latency
      - query-traffic-stats
      - query-network-anomalies
    max_iterations: 10
    
  # 行动 Agent
  action:
    name: "Action Agent"
    role: "处置执行专家"
    goal: "生成处置建议并执行自动化修复"
    backstory: |
      你擅长执行故障恢复操作。
      你了解各种自动化工具和脚本。
    model: claude-sonnet-4-6
    tools:
      - runbook-execute
      - automation-trigger
    max_iterations: 5
    require_confirmation: true  # 执行前需要确认

# Crew 配置
crews:
  diagnosis_crew:
    name: "故障诊断团队"
    process: sequential  # sequential / hierarchical
    agents:
      - diagnosis
      - knowledge
      - action
    tasks:
      - name: analyze_alert
        agent: diagnosis
        description: "分析告警信息"
        
      - name: retrieve_knowledge
        agent: knowledge
        description: "检索相关知识"
        context: [analyze_alert]
        
      - name: generate_action
        agent: action
        description: "生成处置建议"
        context: [analyze_alert, retrieve_knowledge]
```

---

## 十、附录

### 10.1 技术选型决策记录模板

```markdown
## ADR-001: 选择 MCP Toolbox 作为数据库连接方案

### 状态
已接受

### 背景
需要连接 ClickHouse、MySQL、Redis 等多种数据库，
支持 AI Agent 进行数据查询和分析。

### 决策
选择 Google MCP Toolbox for Databases。

### 理由
1. 多数据库统一支持
2. 企业级特性（连接池、认证、可观测性）
3. Google 官方维护，社区活跃
4. 与现有 MCP 协议兼容

### 替代方案
- ClickHouse 官方 MCP：仅支持单一数据库
- 自建 MCP Server：开发成本高

### 后果
- 需要部署额外服务
- 配置相对复杂
- 需要学习 YAML 配置语法
```

### 10.2 依赖清单

```txt
# requirements.txt

# MCP Toolbox
toolbox-sdk>=1.0.0

# Agent Framework
crewai>=0.28.0
langchain>=0.1.0
langchain-community>=0.0.20
langgraph>=0.0.50

# Vector Store
qdrant-client>=1.7.0

# Embedding
sentence-transformers>=2.2.0
FlagEmbedding>=1.2.0

# Document Parsing
unstructured>=0.12.0
pypdf>=4.0.0
python-docx>=1.1.0
beautifulsoup4>=4.12.0
markdown>=3.5.0

# RAG
llama-index>=0.10.0
llama-index-vector-stores-qdrant>=0.1.0

# Observability
langfuse>=2.0.0
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0

# API
fastapi>=0.109.0
uvicorn>=0.27.0
pydantic>=2.5.0

# Database
clickhouse-connect>=0.6.0
pymysql>=1.1.0
redis>=5.0.0

# Utilities
python-dotenv>=1.0.0
pyyaml>=6.0
httpx>=0.26.0
tenacity>=8.2.0

# Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

### 10.3 环境变量清单

```bash
# .env.example

# ClickHouse
CLICKHOUSE_HOST=your-clickhouse-host.com
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=your-password

# MySQL
MYSQL_HOST=your-mysql-host.com
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-password

# Redis
REDIS_HOST=your-redis-host.com
REDIS_PORT=6379
REDIS_PASSWORD=your-password

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=your-api-key  # 可选

# Langfuse
LANGFUSE_PUBLIC_KEY=your-public-key
LANGFUSE_SECRET_KEY=your-secret-key
LANGFUSE_HOST=https://cloud.langfuse.com  # 或自托管地址

# LLM
ANTHROPIC_API_KEY=your-anthropic-key
OPENAI_API_KEY=your-openai-key  # 可选

# MCP Toolbox
TOOLBOX_HOST=0.0.0.0
TOOLBOX_PORT=5000
```

### 10.4 Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  # MCP Toolbox
  toolbox:
    image: googleapis/mcp-toolbox:latest
    ports:
      - "5000:5000"
    volumes:
      - ./config/tools.yaml:/app/tools.yaml
    environment:
      - CLICKHOUSE_HOST=${CLICKHOUSE_HOST}
      - CLICKHOUSE_USER=${CLICKHOUSE_USER}
      - CLICKHOUSE_PASSWORD=${CLICKHOUSE_PASSWORD}
      - MYSQL_HOST=${MYSQL_HOST}
      - MYSQL_USER=${MYSQL_USER}
      - MYSQL_PASSWORD=${MYSQL_PASSWORD}
      - REDIS_HOST=${REDIS_HOST}
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    command: ["--tools-file=/app/tools.yaml"]
    
  # Qdrant
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_storage:/qdrant/storage
    environment:
      - QDRANT_API_KEY=${QDRANT_API_KEY}
      
  # Langfuse (自托管)
  langfuse:
    image: langfuse/langfuse:latest
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/langfuse
      - NEXTAUTH_SECRET=your-secret
      - SALT=your-salt
    depends_on:
      - postgres
      
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=langfuse
    volumes:
      - postgres_storage:/var/lib/postgresql/data

volumes:
  qdrant_storage:
  postgres_storage:
```

### 10.5 参考资料

| 类型 | 链接 |
|------|------|
| MCP 协议 | [Model Context Protocol](https://modelcontextprotocol.io/) |
| MCP Toolbox | [Google MCP Toolbox](https://github.com/googleapis/mcp-toolbox) |
| CrewAI 文档 | [CrewAI Docs](https://docs.crewai.com/) |
| LangChain 文档 | [LangChain Docs](https://python.langchain.com/) |
| Qdrant 文档 | [Qdrant Docs](https://qdrant.tech/documentation/) |
| Langfuse 文档 | [Langfuse Docs](https://langfuse.com/docs) |
| RCAgent 论文 | [arXiv:2310.16340](https://arxiv.org/html/2310.16340v3) |
| Self-RAG 论文 | [arXiv:2310.05506](https://arxiv.org/abs/2310.05506) |

---

> **文档维护**: 本文档将随项目进展持续更新  
> **反馈渠道**: 请通过 Issue 或 PR 提出修改建议
