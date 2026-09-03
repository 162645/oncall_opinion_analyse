# Oncall Opinion Analyse Agent 项目文档

> **版本**: 3.0
> **更新日期**: 2025-05-20
> **项目定位**: 智能运维 Agent 平台

---

## 一、项目概述

### 1.1 背景

Oncall Opinion Analyse Agent 是一个智能运维诊断平台，通过 AI Agent 技术实现：

- **故障自动诊断** - 多 Agent 协作，自动分析根因
- **知识库检索** - RAG 技术检索历史案例和 SOP
- **网络数据分析** - 连接 ClickHouse 分析网络测量数据
- **效果量化评估** - 准确率、MTTR 等指标追踪
- **思考过程可视化** - 展示 Agent 推理链 (v3)
- **自然语言可视化** - 文字描述生成图表 (v3)
- **MCP 工具集成** - 文件/内存/时间等工具 (v3)

### 1.2 技术栈

| 模块 | 技术选型 |
|------|---------|
| MCP 集成 | MCP Protocol (Anthropic) |
| 向量存储 | Qdrant |
| 知识图谱 | Neo4j |
| Agent 框架 | 自研 + CrewAI |
| Embedding | BGE-M3 |
| 图表生成 | Matplotlib |
| 可观测性 | Langfuse |

---

## 二、项目结构

```
oncall_opinion_analyse/
├── docs/                        # 📄 文档目录
│   ├── README.md               # 本文档
│   └── optimization-v3.md      # v3 优化记录
│
├── src/                         # 💻 核心代码
│   ├── trace/                  # 思考过程追踪 (v3)
│   │   ├── models.py           # 追踪数据模型
│   │   ├── collector.py        # 追踪收集器
│   │   └── visualizer.py       # 可视化渲染
│   │
│   ├── visualization/          # 自然语言可视化 (v3)
│   │   ├── intent_parser.py    # 意图解析
│   │   ├── data_fetcher.py     # 数据查询
│   │   ├── chart_generator.py  # 图表生成
│   │   └── service.py          # 服务入口
│   │
│   ├── mcp/                    # MCP 工具集成 (v3)
│   │   ├── base.py             # 基础类型
│   │   ├── config.py           # 配置管理
│   │   ├── client.py           # MCP 客户端
│   │   └── tools/              # 内置工具
│   │       ├── file_tools.py   # 文件操作
│   │       ├── memory_tools.py # 内存存储
│   │       └── time_tools.py   # 时间处理
│   │
│   ├── tools/                  # 工具层
│   │   ├── registry.py         # 工具注册中心
│   │   ├── base.py             # 工具基类
│   │   └── plugins/            # 工具插件
│   │       ├── network/        # 网络工具 (4个)
│   │       ├── database/       # 数据库工具
│   │       └── cloud/          # 云平台工具
│   │
│   ├── knowledge/              # 知识层
│   │   ├── rag/                # Agentic RAG
│   │   ├── graph/              # 知识图谱
│   │   ├── index/              # 多级索引
│   │   └── feedback/           # 反馈闭环
│   │
│   ├── agents/                 # Agent 层
│   │   ├── router/             # 路由
│   │   └── orchestrator/       # 编排器
│   │
│   └── eval/                   # 评估层
│       ├── evaluator.py        # 诊断评估
│       └── metrics.py          # 指标收集
│
├── tests/                       # 🧪 测试文件
│   └── test_mcp.py             # MCP 模块测试
│
├── config/                      # ⚙️ 配置文件
│   ├── tools.yaml              # MCP Toolbox 配置
│   └── .env.example            # 环境变量模板
│
├── docker/                      # 🐳 Docker 部署
│   └── docker-compose.yml      # 服务编排
│
├── biz/                         # 📦 原有业务代码 (Go)
│
├── specs/                       # 📋 测试规格
│
└── legacy/                      # 📁 旧版本代码
    ├── v1/
    └── v2/
```

---

## 三、核心功能

### 3.1 思考过程可视化 (v3)

```python
from src.trace import TraceCollector, TraceVisualizer, StepType

collector = TraceCollector()
collector.start_trace("session-001", "查询延迟")

with collector.trace_step(
    step_type=StepType.TOOL_CALL,
    agent_name="AnalysisAgent",
    action="query_latency",
) as step:
    step.reasoning = "查询新加坡区域延迟，发现 P99=150ms"

trace = collector.end_trace()
print(TraceVisualizer.render_markdown(trace))
```

**输出示例:**
```markdown
# 执行追踪: session-001

## 基本信息
- 查询: 查询延迟
- 开始: 2025-05-20 11:00:00
- 结束: 2025-05-20 11:00:01
- 耗时: 1234ms

## 执行步骤

### Step 1: TOOL_CALL (AnalysisAgent)
- 动作: query_latency
- 耗时: 856ms
- 思考: 查询新加坡区域延迟，发现 P99=150ms
```

### 3.2 自然语言可视化 (v3)

```python
from src.visualization import NaturalLanguageVisualization

service = NaturalLanguageVisualization()
result = await service.visualize("画一个最近24小时的延迟趋势图")

if result.success:
    print(result.chart_base64)  # base64 编码的图片
```

**支持的查询类型:**

| 查询示例 | 解析结果 |
|---------|---------|
| "画一个延迟趋势图" | 折线图, latency, 1h |
| "最近24小时流量变化" | 折线图, traffic, 24h |
| "各区域错误率对比" | 柱状图, error_rate, 按区域 |
| "新加坡延迟分布饼图" | 饼图, latency, region=Singapore |

### 3.3 MCP 工具集成 (v3)

```python
from src.mcp import MCPClient

client = MCPClient()
await client.initialize()

# 文件操作
await client.call_tool("write_file", path="report.md", content="# 报告")
result = await client.call_tool("read_file", path="report.md")

# 内存存储
await client.call_tool("memory_save", key="incident", value={"type": "latency"}, ttl=3600)

# 时间处理
result = await client.call_tool("time_now")
```

**内置工具:**

| 类别 | 工具 | 功能 |
|------|------|------|
| 文件 | read_file, write_file, list_directory | 文件操作 |
| 内存 | memory_save, memory_load, memory_search | 持久化存储 |
| 时间 | time_now, time_format, time_diff | 时间处理 |

### 3.4 动态工具发现

```python
from src.tools import ToolRegistry

# 自动发现并注册工具
registry = ToolRegistry()
registry.discover_tools()

# 根据意图选择工具
tools = registry.select_tools("查询新加坡区域的网络延迟")
```

### 3.5 Agentic RAG

```python
from src.knowledge.rag import IterativeRetriever

# 多轮迭代检索
retriever = IterativeRetriever()
results = await retriever.retrieve(
    query="新加坡到美国链路延迟突增",
    max_iterations=3
)
# 自动: 生成子问题 → 检索 → 评估 → 重排序
```

### 3.6 多模式 Agent 编排

```python
from src.agents import AgentOrchestrator, CollaborationMode

orchestrator = AgentOrchestrator()

# 并行执行
result = await orchestrator.execute(
    context=context,
    mode=CollaborationMode.PARALLEL
)

# 辩论模式
result = await orchestrator.execute(
    context=context,
    mode=CollaborationMode.DEBATE
)
```

---

## 四、快速开始

### 4.1 环境准备

```bash
# 1. 安装依赖
pip install qdrant-client neo4j FlagEmbedding pydantic httpx matplotlib aiofiles

# 2. 配置环境变量
cp config/.env.example config/.env
# 编辑 config/.env 填写数据库连接信息

# 3. 启动服务
cd docker
docker-compose up -d
```

### 4.2 验证服务

```bash
# 运行 MCP 测试
python3 tests/test_mcp.py

# Qdrant
curl http://localhost:6333/health
```

### 4.3 运行诊断

```python
from src.agents import AgentOrchestrator, AgentContext

orchestrator = AgentOrchestrator()
context = AgentContext(
    session_id="test-001",
    query="新加坡区域网络延迟突增",
    entities={"region": "Singapore-Central"}
)

result = await orchestrator.execute(context)
print(result.final_result)
```

---

## 五、配置说明

### 5.1 MCP 配置 (.mcp.json)

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    },
    "time": {
      "command": "uvx",
      "args": ["mcp-server-time"]
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    }
  }
}
```

### 5.2 Docker Compose

```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
```

---

## 六、API 参考

### 6.1 TraceCollector (v3)

| 方法 | 说明 |
|------|------|
| `start_trace(session_id, query)` | 开始追踪 |
| `trace_step(step_type, agent, action)` | 追踪步骤上下文 |
| `end_trace()` | 结束追踪 |

### 6.2 NaturalLanguageVisualization (v3)

| 方法 | 说明 |
|------|------|
| `visualize(query)` | 从自然语言生成图表 |

### 6.3 MCPClient (v3)

| 方法 | 说明 |
|------|------|
| `initialize()` | 初始化客户端 |
| `call_tool(name, **params)` | 调用工具 |
| `list_tools()` | 列出可用工具 |

### 6.4 ToolRegistry

| 方法 | 说明 |
|------|------|
| `discover_tools()` | 自动发现插件工具 |
| `register(tool)` | 注册工具 |
| `select_tools(query)` | 语义选择工具 |

---

## 七、性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 检索准确率 | > 85% | Top-5 召回率 |
| 诊断延迟 | < 2s | 并行模式 |
| 根因准确率 | > 80% | 评估得分 |
| MTTR 降低 | 60-80% | vs 人工诊断 |

---

## 八、版本历史

| Phase | 功能 | 状态 |
|-------|------|------|
| v3.0 | 思考过程可视化 + 自然语言可视化 + MCP | ✅ 已完成 |
| v3.1 | Web UI 界面 | 📅 计划中 |
| v2.0 | 动态工具 + Agentic RAG + 知识图谱 | ✅ 已完成 |
| v1.0 | 基础 Agent 框架 | ✅ 已完成 |

---

## 九、依赖清单

```txt
qdrant-client>=1.7.0
neo4j>=5.0.0
FlagEmbedding>=1.2.0
pydantic>=2.0.0
httpx>=0.25.0
matplotlib>=3.7.0
aiofiles>=23.0.0
```

---

## 十、参考资料

- [MCP Protocol](https://modelcontextprotocol.io/)
- [Qdrant](https://github.com/qdrant/qdrant)
- [Neo4j](https://neo4j.com/)
- [BGE-M3](https://huggingface.co/BAAI/bge-m3)
- [Matplotlib](https://matplotlib.org/)
