# Evidence-driven Network Analysis Harness 设计方案

> 版本：v1 设计稿  
> 目标：把项目从“多个 Agent/工具的集合”收敛为一个面向主动网络测量数据的、可解释、可恢复、可评测的 Agent 分析 Harness。

> 当前实现状态：六节点 LangGraph 已作为唯一执行入口；Ping/Traceroute 查询通过统一 Query Catalog、MCP 适配层和 ToolRuntime 执行；Verifier 与 Synthesizer 共享 EvidenceLedger。远程数据源不可用时，系统会保守降级为 `ABSTAIN/PARTIAL`，不会伪造网络结论。

## 1. 一句话定义

本项目不是让 LLM 直接生成 SQL，也不是把 PingAgent、TracerouteAgent、RAGAgent 机械串起来。

它应该是一个面向网络问题调查的控制循环：

```text
用户问题
  → 结构化任务
  → 选择最小必要查询
  → 获取网络证据
  → 判断证据缺口
  → 必要时继续下钻或换证据
  → 输出带证据和不确定性的结论
```

核心差异是：Agent 不负责“自由发挥”，而是负责在有限预算内决定下一步最有价值的调查动作；Harness 负责状态、工具、查询安全、证据和终止条件。

## 2. 设计原则

### 2.1 一个执行权

只有 LangGraph Harness 可以驱动一次 Agent Run。旧的 `AgentService`、`AgentOrchestrator`、ReAct 实验实现不能再各自拥有一套执行循环。

### 2.2 一个状态真相源

所有节点只读写 `HarnessState`。原始工具结果不直接在节点之间通过临时变量传递，也不让 LLM通过历史消息猜测当前状态。

### 2.3 模型做决策，代码做约束

```text
LLM：理解问题、选择分析能力、解释证据
代码：参数校验、SQL 编译、统计计算、预算、权限、重试、终止
```

### 2.4 高概率场景确定性执行

常用的 Ping/Traceroute 分析使用经过测试和版本化的 Query Catalog；自由 SQL 只能作为受限的长尾能力，不能作为默认路径。

### 2.5 证据先于结论

最终回答中的每个重要事实都必须能够追溯到 `Evidence ID`。证据不足时，系统必须输出“无法确认”，而不是生成一个听起来合理的根因。

## 3. 借鉴成熟 Agent 的部分

本设计借鉴的是成熟项目的边界，而不是它们的模块数量：

- LangGraph：显式 State、Node、Conditional Edge、Checkpoint、Streaming 和 Interrupt，适合有状态、可恢复的 Agent Runtime。
- LangGraph SQL Agent：将 Schema/查询生成/查询检查/执行拆成独立边界，并要求数据库权限最小化。
- OpenHands：用 Controller 驱动单一 State，由 Agent 生成 Action，Runtime 返回 Observation；前端不直接执行 Agent 动作。
- SWE-agent：通过结构化的 Agent-Computer Interface 限制 Agent 的动作空间。本项目对应为 Typed TaskSpec、AnalysisPlan 和 Query ID。
- MCP：Tools、Resources、Prompts 是协议能力，不是业务编排层。本项目用 MCP 暴露能力，但不让 MCP 维护另一套 SQL 和业务逻辑。

参考：

- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph custom SQL agent](https://docs.langchain.com/oss/python/langgraph/sql-agent)
- [LangGraph workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents)
- [OpenHands Agent SDK](https://docs.openhands.dev/sdk/api-reference/openhands.sdk.agent)
- [MCP server primitives](https://modelcontextprotocol.io/specification/2025-06-18/server/index)

## 4. 总体架构

```mermaid
flowchart TB
    USER["用户问题<br/>为什么 UKRAINE 的 P95 RTT 突增？"]
    API["Chat API<br/>HTTP / SSE"]

    subgraph HARNESS["LangGraph Harness · 唯一执行权"]
        direction LR
        U["1 Understand<br/>Query → TaskSpec"]
        C["2 Context<br/>Semantic + Catalog + Recipe"]
        P["3 Planner<br/>TaskSpec → AnalysisPlan"]
        X["4 Executor<br/>PlanStep Batch"]
        V["5 Verifier<br/>Evidence → Verdict"]
        S["6 Synthesizer<br/>Evidence → Answer"]

        U --> C --> P --> X --> V
        V -->|"NEED_MORE_EVIDENCE<br/>且预算充足"| P
        V -->|"SUFFICIENT / PARTIAL / ABSTAIN"| S
    end

    USER --> API --> U
    S --> API

    subgraph KERNEL["Execution Kernel · 不属于 Graph Node"]
        direction LR
        CAT["Query Catalog<br/>QuerySpec + SQL Template"]
        COMP["Query Compiler<br/>参数化编译"]
        GOV["Query Governor<br/>预算与安全策略"]
        RT["Tool Runtime<br/>Timeout / Retry / Circuit / Audit"]
        CAT --> COMP --> GOV --> RT
    end

    P -. "query_id + typed params" .-> CAT
    X --> RT

    subgraph CAP["Network Capabilities"]
        direction LR
        PB["Ping Provider"]
        TP["Traceroute Provider"]
        KP["Knowledge Provider"]
        MP["Metadata Provider"]
    end

    RT --> PB & TP & KP & MP
    PB --> CH[("ClickHouse")]
    TP --> CH
    MP --> CH
    KP --> QD[("Qdrant")] & N4[("Neo4j")]

    X --> EL[("Evidence Ledger")]
    EL --> V & S
    HARNESS <--> REDIS[("Redis Checkpoint / Cache")]
    HARNESS --> OBS["Trace / Metrics / Audit"]

    classDef user fill:#eee8ff,stroke:#7048e8,color:#2e1a67,stroke-width:2px;
    classDef graph fill:#e5f3ff,stroke:#1677b8,color:#083b5c,stroke-width:1px;
    classDef kernel fill:#fff3d6,stroke:#c77d00,color:#633d00;
    classDef cap fill:#e6f7ed,stroke:#219653,color:#124c2b;
    classDef data fill:#f2f4f7,stroke:#667085,color:#202b3c;
    classDef evidence fill:#ffe8ed,stroke:#d6335c,color:#70142c;

    class USER user;
    class U,C,P,X,V,S graph;
    class CAT,COMP,GOV,RT kernel;
    class PB,TP,KP,MP cap;
    class CH,QD,N4,REDIS,OBS data;
    class EL evidence;
```

这里有一个重要约束：只有 6 个模块是 LangGraph Node。`Query Catalog`、`Query Compiler`、`Tool Runtime` 和 `Provider` 是普通服务，内部可以有函数和类，但不能再偷偷启动另一套 Agent 循环。

## 5. 六个核心节点

| 节点 | 是否调用 LLM | 输入 | 输出 | 负责什么 | 不负责什么 |
|---|---:|---|---|---|---|
| Understand | 是，结构化输出 | 原始问题 | `TaskSpec` | 理解目标、对象、范围、指标 | 不查数据库、不生成 SQL |
| Context | 否为主 | `TaskSpec` | `PlanningContext` | 加载语义、Query Catalog、Recipe、数据可用性 | 不决定最终执行步骤 |
| Planner | 是，结构化输出 | TaskSpec、Context、Evidence、Budget | `AnalysisPlan` | 选择 Query ID、参数和依赖 | 不生成原始 SQL、不控制权限 |
| Executor | 否 | AnalysisPlan | Evidence、Error | 执行当前轮工具计划 | 不改变分析目标、不做解释 |
| Verifier | 规则为主 | TaskSpec、Evidence、Budget | `Verification` | 判断证据是否足够、冲突和缺口 | 不创造数据、不替模型编造证据 |
| Synthesizer | 是 | TaskSpec、Evidence、Verification | `FinalAnswer` | 生成结论、限制、图表规格 | 不重新查库、不新增事实 |

### 5.1 UnderstandNode：从分类升级为 TaskSpec

不再只返回 `analysis` 或 `diagnosis`。例如：

```json
{
  "subject": "ping",
  "goal": "detect_and_attribute",
  "scope": {
    "region": "UKRAINE",
    "time_range": {
      "kind": "relative",
      "hours": 24
    }
  },
  "metrics": ["p50_rtt", "p95_rtt", "p99_rtt"],
  "candidate_dimensions": ["asn", "prefix24", "isp"],
  "presentation": {"chart": true},
  "ambiguities": []
}
```

“画图”是输出格式，不是业务意图；“诊断”是分析目标，不是一个单独的 Agent。

### 5.2 ContextNode：给 Planner 提供可用上下文

Context 只提供 Planner 决策所需的信息：

```text
Semantic Context
  字段含义、单位、指标关系、Ping/Traceroute 关联

Catalog Context
  可用 Query ID、输入参数、输出类型、成本等级

Recipe Context
  已发布的 network latency / path change 分析配方

Availability Context
  地区覆盖范围、数据时间范围、数据源健康状态
```

Qdrant 和 Neo4j 不直接成为 Graph 节点，而是由 `Knowledge Provider` 统一封装为：

```text
knowledge.search
graph.expand
```

### 5.3 PlannerNode：只规划能力，不规划 SQL

Planner 的输出必须是可校验的 `AnalysisPlan`：

```json
{
  "plan_id": "plan_001",
  "round": 1,
  "objective": "confirm_degradation",
  "steps": [
    {
      "id": "s1",
      "query_id": "ping.compare_window",
      "params": {
        "region": "UKRAINE",
        "current_window": "24h",
        "baseline_window": "previous_24h"
      },
      "expected_evidence": ["metric_shift"],
      "depends_on": [],
      "required": true
    },
    {
      "id": "s2",
      "query_id": "ping.timeseries",
      "params": {
        "region": "UKRAINE",
        "window": "24h",
        "resolution": "1h"
      },
      "expected_evidence": ["anomaly_window"],
      "depends_on": [],
      "required": true
    }
  ]
}
```

同一轮内无依赖的只读查询可以并行执行；下一轮只能针对 Verifier 返回的 `missing_evidence` 进行规划，不能重复已经成功的查询。

### 5.4 ExecutorNode：执行一批计划步骤

Executor 的唯一职责是：

```text
AnalysisPlan
  → Plan Schema 校验
  → 执行依赖排序
  → Tool Runtime
  → Provider
  → Evidence 标准化
```

Executor 不写 SQL、不拼 Prompt、不决定要不要继续调查。

### 5.5 EvidenceVerifierNode：真正的闭环控制点

Verifier 取代当前“固定 confidence + Reflection”的形式，检查：

1. 目标覆盖：是否同时回答了“是否异常、异常范围、可能原因”。
2. 数据质量：样本数、覆盖时间、缺失比例、新鲜度。
3. 数值一致性：P50/P95/P99、趋势和分组结果是否一致。
4. 跨源一致性：Ping 变化是否得到 Traceroute 或其他证据支持。
5. 结论强度：现有证据允许说“事实”“相关性”还是只能说“假设”。

只允许输出四类 Verdict：

```text
SUFFICIENT          证据充分，可以回答
NEED_MORE_EVIDENCE  证据缺口明确，返回 Planner
PARTIAL             达到预算，输出已有可靠结论
ABSTAIN             数据不足或证据冲突，拒绝归因
```

### 5.6 SynthesizerNode：Evidence → Answer

Synthesizer 的输入不应该是海量原始结果，而应该是：

```text
TaskSpec
AnalysisPlan
Evidence Ledger 摘要
Verification Verdict
ChartSpec
```

输出结构：

```json
{
  "verdict": "SUFFICIENT",
  "claims": [
    {
      "text": "P95 RTT 相比上一窗口升高约 89%",
      "evidence_ids": ["ev_001"]
    },
    {
      "text": "异常窗口的主 AS Path 发生变化",
      "evidence_ids": ["ev_004"]
    }
  ],
  "limitations": [
    "当前样本不足以证明路径变化是唯一根因"
  ],
  "charts": [
    {
      "type": "timeseries",
      "evidence_id": "ev_002",
      "x": "time",
      "series": ["p50_rtt", "p95_rtt", "p99_rtt"]
    }
  ]
}
```

## 6. HarnessState：节点之间到底怎么传数据

建议把当前分散的 `knowledge`、`tool_results`、`reasoning` 和 `confidence` 收敛成一个状态：

```python
class HarnessState(TypedDict):
    run_id: str
    session_id: str
    query: str

    task: TaskSpec | None
    context: PlanningContext | None
    plan: AnalysisPlan | None
    plan_round: int

    evidence: list[Evidence]
    verification: Verification | None
    errors: list[ExecutionError]

    budget: RunBudget
    status: Literal["running", "waiting", "completed", "partial", "abstained", "failed"]
    answer: FinalAnswer | None
    trace: list[TraceEvent]
```

节点只返回局部更新：

```text
Understand → task
Context    → context
Planner    → plan, plan_round
Executor   → evidence, errors
Verifier   → verification, status
Synthesizer→ answer, status
```

原始查询结果可以存到短期缓存或对象存储，State 只保存摘要、引用、统计结果和数据血缘，避免 Redis Checkpoint 被大结果撑爆。

## 7. ReAct 循环的正确形态

本项目会有 ReAct 的思想，但采用“批量计划级循环”：

```text
Plan Round 1
  → Execute: compare_window + timeseries
  → Verify: 确认异常，但缺少维度归因

Plan Round 2
  → Execute: by_asn + by_prefix24
  → Verify: 异常集中在某个 AS/Prefix

Plan Round 3
  → Execute: trace.path_change + knowledge.search
  → Verify: 证据充分或明确无法确认

Synthesize
```

建议预算：

```text
max_plan_rounds = 3
max_query_steps = 8
max_tool_failures = 3
max_total_latency = 45s
max_sql_fallback = 1
```

如果三轮后仍然无法归因，必须输出“现有主动测量数据不足以确认根因”，而不是继续无限调用工具。

## 8. Query Catalog：预定义 SQL 的核心设计

### 8.1 Query Catalog 的定位

Query Catalog 是平台的确定性分析能力目录：每个 Query 都有固定模板、输入模型、输出模型、成本等级和测试数据。

Planner 只能选择：

```text
query_id + typed params
```

Planner 不可以选择：

```text
table_name
column_name
raw SQL
ORDER BY expression
```

### 8.2 第一批 Query Primitive

```text
Ping
├── ping.summary
├── ping.timeseries
├── ping.compare_window
├── ping.by_asn
├── ping.by_asgeo
├── ping.by_country
├── ping.by_prefix24
└── ping.outliers

Traceroute
├── trace.path_distribution
├── trace.path_change
├── trace.as_path
├── trace.asgeo_path
├── trace.terminal_as
├── trace.hop_distribution
└── trace.reachability

Metadata
├── meta.regions
├── meta.data_coverage
├── meta.asn
├── meta.prefix
└── meta.operator
```

### 8.3 目录结构

```text
src/query_catalog/
├── registry.py
├── models.py
├── compiler.py
├── governor.py
└── sql/
    ├── ping/
    │   ├── summary.sql
    │   ├── timeseries.sql
    │   ├── compare_window.sql
    │   ├── by_asn.sql
    │   └── by_prefix24.sql
    └── traceroute/
        ├── path_distribution.sql
        ├── path_change.sql
        └── terminal_as.sql
```

### 8.4 QuerySpec

```python
QuerySpec(
    id="ping.by_asn",
    version="1.0.0",
    description="按 ASN 统计指定区域内的 RTT 分布",
    input_model=PingByASNInput,
    output_model=DimensionRTTResult,
    sql_template="ping/by_asn.sql",
    evidence_type="dimension_attribution",
    cost_class="medium",
    default_limit=20,
    cache_ttl_seconds=300,
)
```

## 9. SQL 稳定性与安全性

执行路径必须是：

```text
Query ID
  → Pydantic/Input Schema
  → Dataset Registry
  → 参数化 SQL Template
  → AST/只读策略检查
  → Query Governor
  → ClickHouse settings
  → Output Schema
  → Evidence
```

具体要求：

- LLM 不直接生成 SQL。
- 用户的地区只映射到逻辑 Dataset ID，物理表名由服务端 Registry 解析。
- 所有值使用参数绑定，不能字符串拼接。
- 地区、AS、Prefix、运营商、时间粒度和排序字段全部白名单化。
- 禁止 DDL、DML、多语句和 `SELECT *`。
- 所有分析查询必须包含时间范围；默认 24 小时，最大 7 天。
- 所有结果必须有最大行数；趋势查询使用聚合粒度，不返回无限明细。
- ClickHouse 使用只读账号，并设置执行时间、内存、线程和结果行数上限。
- 内存超限不做原样重试，而是触发“缩短时间范围/提高聚合粒度/移除低价值维度”的降级策略。
- 每个 QuerySpec 必须有固定小数据集的输入输出测试。

长尾自由 SQL 只允许作为第二阶段能力：

```text
生成 SQL
  → SQL AST 检查
  → 只读策略检查
  → 成本估算 / Dry Run
  → 人工审批（高成本时）
  → 单次执行
```

## 10. Skill：Analysis Recipe，而不是第二套 Agent

Skill 保存的是成功分析的策略和触发条件：

```yaml
id: latency-root-cause
version: 1.0.0
trigger:
  subject: ping
  goal: detect_and_attribute

initial_steps:
  - query: ping.compare_window
  - query: ping.timeseries

rules:
  - when: metric_shift.significant == true
    add:
      - query: ping.by_asn
      - query: ping.by_prefix24
  - when: dimension_attribution.concentration >= 0.5
    add:
      - query: trace.path_change
      - query: knowledge.search

stop:
  - when: anomaly_confirmed == false
    verdict: SUFFICIENT
```

Skill 只能给 Planner 提供建议，不能绕过 Query Governor、Tool Runtime 和 Verifier。

Skill 生命周期：

```text
成功 Trace
  → 提取 Recipe Candidate
  → 参数化
  → 固定数据集 Replay
  → 人工审核
  → 发布
  → 回归测试
  → 版本回滚
```

## 11. MCP：协议适配，不是业务编排

统一关系：

```text
Network Capability
        ↓
    Tool Runtime
     ↙       ↘
Harness 内部调用   MCP Server 对外暴露
```

建议暴露高层只读工具：

```text
network.ping_summary
network.ping_timeseries
network.ping_by_dimension
network.trace_path_change
network.data_coverage
knowledge.search
graph.expand
```

不暴露：

- `execute_sql(sql)`；
- 物理表名和数据库连接信息；
- 与项目无关的任意文件删除或 Shell 执行能力；
- 与 Query Catalog 重复的第二套 SQL 配置。

## 12. 一次真实请求的数据流

用户问题：

```text
分析 UKRAINE 最近 24 小时 P95 RTT 是否异常，
如果异常请说明主要是哪些 AS 和路径导致的。
```

实际流转：

```text
Understand
  TaskSpec = ping + detect_and_attribute + UKRAINE + 24h

Context
  找到 latency-root-cause Recipe
  确认 UKRAINE 有 24h 数据覆盖

Planner Round 1
  ping.compare_window
  ping.timeseries

Executor
  ClickHouse 返回 P50/P95/P99 和小时趋势
  Evidence Ledger 写入 ev_001、ev_002

Verifier
  确认 P95 显著升高
  发现缺少 AS 归因
  返回 NEED_MORE_EVIDENCE

Planner Round 2
  ping.by_asn
  ping.by_prefix24

Executor
  发现异常主要集中在 AS4134 和 Prefix X
  Evidence Ledger 写入 ev_003、ev_004

Verifier
  发现异常集中度较高，但尚无路径证据
  返回 NEED_MORE_EVIDENCE

Planner Round 3
  trace.path_change
  knowledge.search

Verifier
  检查数值、时间、路径和知识证据
  返回 SUFFICIENT 或 ABSTAIN

Synthesizer
  输出结论、图表、Evidence ID 和限制条件
```

## 13. 前端与 API

React 只负责展示，不承担 Agent 决策和统计计算：

```text
React
  → POST /api/chat/send
  ← SSE: task.understood
  ← SSE: plan.created
  ← SSE: tool.started
  ← SSE: evidence.added
  ← SSE: verification.completed
  ← SSE: plan.revised
  ← SSE: answer.completed
```

最终前端接收：

```json
{
  "answer": "...",
  "claims": [],
  "evidence": [],
  "charts": [],
  "limitations": [],
  "verdict": "SUFFICIENT",
  "run_id": "run_xxx"
}
```

前端根据 `ChartSpec` 使用 ECharts/AntV 渲染，后端不再维护 `VisualizationAgent`。

## 14. 目标代码结构

```text
src/
├── harness/
│   ├── graph.py
│   ├── state.py
│   ├── models.py
│   └── nodes/
│       ├── understand.py
│       ├── context.py
│       ├── planner.py
│       ├── executor.py
│       ├── verifier.py
│       └── synthesizer.py
├── query_catalog/
│   ├── registry.py
│   ├── models.py
│   ├── compiler.py
│   ├── governor.py
│   └── sql/
├── capabilities/
│   ├── ping.py
│   ├── traceroute.py
│   ├── knowledge.py
│   └── metadata.py
├── runtime/
│   ├── tool_runtime.py
│   ├── checkpoint.py
│   ├── budget.py
│   └── telemetry.py
├── skills/
│   ├── registry.py
│   ├── lifecycle.py
│   └── recipes/
├── mcp/
│   └── adapter.py
├── knowledge/
├── eval/
└── api/
```

## 15. 重构顺序

### Phase 1：建立新状态和六节点

- 新建 `HarnessState`、`TaskSpec`、`AnalysisPlan`、`Evidence` 和 `Verification`。
- 让 `/api/chat/send` 进入新 Harness。
- 暂时保留旧 AgentService 作为兼容门面，但不再拥有流程控制权。

### Phase 2：Query Catalog

- 从现有 ClickHouse Analyzer 提取首批 Ping/Traceroute QuerySpec。
- 每个 Query 配套 SQL 模板、输入输出模型和固定数据测试。
- 增加 Dataset Registry、Query Compiler 和 Query Governor。

### Phase 3：Verifier Loop

- 用确定性规则实现目标覆盖、样本量、数值一致性和证据引用检查。
- 实现 1～3 轮 Progressive Drill-down。
- 用 Evidence Quality 替代固定 `confidence=0.85`。

### Phase 4：Skill/MCP 收敛

- 将 Skill 改成 Analysis Recipe。
- 将 `src/tools` 和 `src/mcp/tools` 的重复业务能力合并。
- MCP 只保留协议 Adapter。

### Phase 5：删除旧执行权

- 删除旧 Router/Orchestrator/ReAct 编排路径。
- 删除模拟分析和 VisualizationAgent。
- 将前端 Trace、API 文档和评测全部对齐新 Harness。

## 16. 成熟度验收标准

- 所有自然语言请求只有一个 Harness 入口。
- 高频查询不允许 LLM 生成 SQL。
- 每条关键结论都有 Evidence ID。
- Verifier 能区分“异常已确认”和“根因已确认”。
- Ping → ASN/Prefix → Traceroute 的下钻由证据缺口触发，而不是固定执行。
- 正常请求在 1～3 轮内收敛，超过预算可靠停止。
- ClickHouse 内存超限会改变查询策略，不会原样重试。
- Checkpoint 恢复不会重复已经提交的工具执行。
- Demo 数据和真实数据有明确标记。
- 测试覆盖 TaskSpec、Plan、Query、Evidence、Verifier 和最终回答。

## 17. 面试表达

> 我设计的是一个面向主动网络测量的 Evidence-driven Agent Harness。Agent 先把自然语言问题转换为 Typed TaskSpec，再从版本化 Query Catalog 和 Analysis Recipe 中规划查询；所有 Ping、ASN、Prefix 和 Traceroute 查询都由确定性模板和 Query Governor 执行。工具结果进入 Evidence Ledger，Verifier 根据证据覆盖和数据质量决定继续下钻、重新规划、部分回答还是拒绝归因。整个过程通过 LangGraph Checkpoint、Tool Runtime 和 Trace 实现可恢复、可审计和可评测。
