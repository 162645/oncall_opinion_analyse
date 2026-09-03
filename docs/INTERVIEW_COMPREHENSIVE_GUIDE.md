# 项目面试全面准备指南

> 本文档涵盖项目介绍、亮点提炼、面试问题、八股文知识点，建议反复阅读

---

## 一、项目概览

### 1.1 项目规模

| 指标 | 数据 |
|------|------|
| **Go 代码** | ~13,600 行 (核心服务) |
| **Python 代码** | ~34,600 行 (AI 智能层) |
| **TypeScript 代码** | ~1,500 行 (前端) |
| Go 文件数 | 47 个 |
| Python 文件数 | 161 个 |
| 核心模块 | 15+ 个 |
| API 端点 | 60+ 个 |
| 前端页面 | 6 个 |

### 1.2 架构设计：Go + Python 混合架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           前端层 (TypeScript)                            │
│   React 18 + Semi Design + Vite                                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Go 核心服务层 (Hertz)                             │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│   │  Handler     │  │  Service     │  │  DAL/Model   │                  │
│   │  (9 files)   │  │  (2 files)   │  │  (5 files)   │                  │
│   └──────────────┘  └──────────────┘  └──────────────┘                  │
│   • 告警回调处理     • 业务逻辑计算       • 数据模型定义                   │
│   • Argos 代理       • 任务结果处理       • 数据库访问                    │
│   • 回调代理         • 告警等级判断       • 查询构建                      │
│                                                                         │
│   技术栈: Hertz + TCC 配置中心 + ByteDance 内部组件                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Python AI 智能层 (FastAPI)                       │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│   │  LLM Gateway │  │  Agent 层    │  │  Knowledge   │                  │
│   │  (~1,000行)  │  │  (~3,000行)  │  │  (~4,000行)  │                  │
│   └──────────────┘  └──────────────┘  └──────────────┘                  │
│   • OpenAI/Claude    • LangGraph 编排   • LlamaIndex RAG               │
│   • 智能路由         • 多模式协作        • 混合检索                      │
│   • 故障转移         • Skill 系统        • 知识图谱                      │
│                                                                         │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│   │  可视化      │  │  可观测性    │  │  评估体系    │                  │
│   │  (~2,500行)  │  │  (~1,000行)  │  │  (~2,000行)  │                  │
│   └──────────────┘  └──────────────┘  └──────────────┘                  │
│   • 自然语言图表     • OpenTelemetry   • RAGAS 评估                    │
│   • 多图表类型       • 分布式追踪       • 质量指标                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           存储层                                        │
│   Qdrant (向量) │ Neo4j (图谱) │ Redis (缓存) │ MinIO (文件)            │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.3 为什么选择 Go + Python 混合架构？

| 层级 | 语言 | 选择原因 |
|------|------|---------|
| 核心服务 | Go | 高性能、高并发、字节内部组件兼容 (Hertz) |
| AI 智能层 | Python | AI 生态丰富、LLM 框架支持好 |
| 前端 | TypeScript | 类型安全、React 生态 |

**架构优势：**
1. **性能最优**：Go 处理高并发请求，Python 专注 AI 计算
2. **生态互补**：Go 适合业务逻辑，Python 适合 AI/ML
3. **独立扩展**：AI 层可独立扩缩容，不影响核心服务
4. **团队协作**：前后端可并行开发，职责清晰

### 1.4 Go 核心服务模块

```
├── main.go                    # Hertz 服务入口
├── router.go / router_gen.go  # 路由注册 (代码生成)
├── biz/
│   ├── handler/               # HTTP Handler (9 files)
│   │   ├── alarm_callback_proxy.go   # 告警回调代理
│   │   ├── get_oncall_argos_diycard_callback.go  # Argos 自定义卡片
│   │   ├── get_oncall_callback.go    # Oncall 回调
│   │   ├── dispose_handler.go        # 处置逻辑
│   │   └── ping.go                   # 健康检查
│   │
│   ├── service/               # 业务逻辑 (2 files)
│   │   └── calculate_alert_task_res.go  # 告警任务结果计算
│   │
│   ├── model/                 # 数据模型 (5 files)
│   │   └── model_gen.go       # 代码生成模型
│   │
│   ├── dal/                   # 数据访问层
│   │   ├── model/             # ORM 模型
│   │   └── query/             # 查询构建
│   │
│   ├── config/                # 配置管理
│   │   └── config.go          # TCC 配置中心
│   │
│   └── util/common/           # 工具函数
│       ├── metrics.go         # 指标上报
│       ├── alert_level.go     # 告警等级
│       └── desc_call.go       # 调用描述
```

### 1.5 Python AI 智能层模块

### 1.6 技术栈一览

**Go 核心服务：**
- Hertz (字节 HTTP 框架)
- TCC 配置中心 (字节内部配置管理)
- GORM (ORM)
- ByteDance 内部组件 (logs, metrics, env)

**Python AI 层：**
- FastAPI (异步 Web 框架)
- OpenAI / Claude API (LLM 接入)
- LlamaIndex (RAG 框架)
- LangGraph (Agent 编排)
- RAGAS (评估框架)
- Qdrant (向量数据库)
- Neo4j (知识图谱)
- OpenTelemetry (可观测性)

**前端：**
- React 18
- Semi Design (字节 UI 组件库)
- TypeScript
- Vite

**存储：**
- Qdrant (向量存储)
- Neo4j (知识图谱)
- Redis (缓存)
- MinIO (文件存储)

---

## 二、项目亮点深度解析

### 亮点 1：多 LLM 后端统一接入

**问题背景：**
- 不同 LLM 有不同的 API 接口
- 模型能力、成本、延迟各不相同
- 需要灵活切换和故障转移

**解决方案：**

```python
class LLMGateway:
    """
    统一 LLM 网关
    - 抽象统一接口
    - 智能路由选择
    - 自动故障转移
    - 成本追踪
    """
    
    async def generate(self, prompt, config):
        adapter = self._adapters[config.provider]
        return await adapter.generate(prompt, config)
    
    async def generate_with_fallback(self, prompt, primary, fallback):
        try:
            return await self.generate(prompt, LLMConfig(provider=primary))
        except Exception:
            return await self.generate(prompt, LLMConfig(provider=fallback))
```

**设计亮点：**
1. **适配器模式**：统一接口，隔离不同 API 差异
2. **策略模式**：智能路由根据任务选择最优模型
3. **熔断机制**：主模型故障自动切换备用

**面试话术：**
> "我们设计了一个统一的 LLM Gateway，采用适配器模式封装了 OpenAI 和 Claude 的 API 差异。更重要的是，我们实现了智能路由——根据任务类型自动选择最优模型，比如简单查询用 GPT-3.5，复杂诊断用 GPT-4。这样既保证了响应质量，又控制了 API 成本。"

---

### 亮点 2：LangGraph 状态机编排

**问题背景：**
- 传统流水线灵活性差
- 无法根据中间结果调整流程
- 难以追踪和调试

**解决方案：**

```python
# 状态定义
class AgentState(TypedDict):
    messages: List[Dict]
    intent: str
    knowledge: str
    tool_results: Dict
    reasoning: str
    response: str
    confidence: float

# 状态流转
[Router] → [Knowledge] → [Tools] → [Reasoning] → [Output]
     │           │           │            │
     └───────────┴───────────┴────────────┘
                   ↓
              条件分支
```

**设计亮点：**
1. **状态可追踪**：每个状态变化都可观测
2. **条件分支**：根据意图动态调整流程
3. **可恢复**：支持断点续执行
4. **可视化**：状态图可导出

**面试话术：**
> "我们没有用传统的流水线架构，而是选择了 LangGraph 的状态机模式。这样做的好处是，我们可以根据中间结果动态调整执行流程。比如诊断场景需要完整的检索-推理流程，而简单查询可以直接跳到输出。这种设计让系统更灵活，也更容易调试。"

---

### 亮点 3：混合检索 + 融合排序

**问题背景：**
- 向量检索擅长语义匹配，但可能遗漏精确关键词
- 关键词检索精确，但无语义理解
- 单一检索召回率有限

**解决方案：**

```python
class FusionRetriever:
    """RRF 融合检索"""
    
    def _rrf_fusion(self, results_list, k=60):
        """
        Reciprocal Rank Fusion
        score(doc) = Σ 1/(k + rank(doc))
        """
        scores = {}
        for results in results_list:
            for rank, doc in enumerate(results):
                scores[doc.id] = scores.get(doc.id, 0) + 1/(k + rank + 1)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**设计亮点：**
1. **互补性**：向量+关键词覆盖不同场景
2. **无监督融合**：RRF 不需要训练
3. **可扩展**：支持添加更多检索器

**面试话术：**
> "我们实现了向量检索和关键词检索的混合方案，使用 RRF 算法进行融合排序。这种设计的优势在于互补性——向量检索能发现语义相关的文档，而关键词检索保证精确匹配的内容不会遗漏。实测中，混合检索的召回率比单一检索提升了 15-20%。"

---

### 亮点 4：用户自定义 Skill 系统

**问题背景：**
- 成功的诊断经验难以复用
- 每次都要重新描述问题
- 团队知识无法沉淀

**解决方案：**

```python
@dataclass
class Skill:
    """用户自定义技能"""
    id: str
    name: str
    trigger: SkillTrigger      # 触发条件
    workflow: List[SkillStep]  # 执行步骤
    parameters: List[SkillParam] # 可配置参数
    scope: SkillScope          # personal/team/system

# 自动推荐机制
class FlowAnalyzer:
    async def analyze(self, trace: ExecutionTrace) -> SkillRecommendation:
        """分析执行轨迹，推荐保存为 Skill"""
        quality_score = self._calculate_quality(trace)
        if quality_score > 0.6:
            return SkillRecommendation(
                recommended=True,
                suggested_name=self._generate_name(trace),
                suggested_workflow=self._extract_workflow(trace),
            )
```

**设计亮点：**
1. **自动识别**：分析成功流程，推荐保存
2. **参数化**：支持变量注入，灵活复用
3. **分层管理**：个人/团队/系统三层
4. **质量评分**：防止低质量 Skill 泛滥

**面试话术：**
> "我们发现用户经常重复执行类似的诊断流程，所以设计了 Skill 系统。核心创新点是自动推荐机制——系统会分析执行轨迹，当检测到高质量的重复模式时，自动推荐用户保存为 Skill。为了防止 Skill 泛滥，我们还设计了质量评分和生命周期管理。"

---

### 亮点 5：RAGAS 效果评估体系

**问题背景：**
- Agent 效果难以量化
- 无法知道改进是否有效
- 缺乏客观评估标准

**解决方案：**

```python
class RAGEvaluator:
    """
    RAGAS 评估指标
    - Faithfulness: 回答是否基于上下文
    - Answer Relevancy: 回答是否切题
    - Context Recall: 检索是否完整
    - Context Precision: 检索是否精确
    """
    
    async def evaluate(self, query, response, contexts):
        return EvaluationResult(
            faithfulness=await self._eval_faithfulness(response, contexts),
            answer_relevancy=await self._eval_relevancy(query, response),
            context_recall=await self._eval_recall(contexts, ground_truth),
        )
```

**设计亮点：**
1. **多维度评估**：覆盖检索和生成全流程
2. **自动化**：无需人工标注即可评估
3. **可量化**：分数可比较、可追踪

**面试话术：**
> "为了量化 Agent 的效果，我们引入了 RAGAS 评估框架。它提供了四个核心指标：忠实度评估回答是否基于检索内容，相关性评估回答是否切题，召回率和精确度评估检索质量。这让我们的改进有了数据支撑，可以清楚地知道每次优化的效果。"

---

### 亮点 6：完整的可观测性

**问题背景：**
- Agent 执行过程是黑盒
- 难以定位性能瓶颈
- 出问题无法追溯

**解决方案：**

```python
@trace_span("agent_execution")
async def execute_agent(context):
    tracer = get_tracer()
    span = tracer.start_span("diagnosis")
    
    # 执行过程中添加事件
    tracer.add_event("knowledge_retrieved", {"count": 5})
    tracer.add_event("reasoning_started")
    
    tracer.end_span(span)
```

**设计亮点：**
1. **分布式追踪**：OpenTelemetry 标准
2. **全链路可视化**：每个步骤可追踪
3. **性能分析**：自动统计耗时

---

### 亮点 7：Go + Python 混合架构设计

**问题背景：**
- 核心业务需要高性能、高并发
- AI 智能层需要丰富的生态支持
- 单一语言难以兼顾两者

**解决方案：**

```
┌────────────────────────────────────────────────────────────┐
│                    Go 核心服务层                            │
│  • Hertz HTTP 框架 (字节内部，性能优秀)                     │
│  • 告警回调处理、Argos 代理、业务逻辑                       │
│  • 高并发、低延迟、内存安全                                 │
└────────────────────────────────────────────────────────────┘
                          ↕ HTTP/gRPC
┌────────────────────────────────────────────────────────────┐
│                    Python AI 智能层                         │
│  • FastAPI 异步框架                                         │
│  • LLM Gateway、Agent 编排、RAG 检索                        │
│  • 丰富的 AI 生态 (LlamaIndex, LangGraph, RAGAS)           │
└────────────────────────────────────────────────────────────┘
```

**设计亮点：**
1. **性能最优**：Go 处理高并发请求，Python 专注 AI 计算
2. **生态互补**：Go 适合业务逻辑，Python 适合 AI/ML
3. **独立扩展**：AI 层可独立扩缩容，不影响核心服务
4. **字节兼容**：Go 层使用 Hertz、TCC 等内部组件，无缝对接

**核心代码结构：**

```go
// main.go - Hertz 服务入口
func main() {
    byted.Init()
    r := byted.Default()
    
    // TCC 配置中心
    tc, _ := tccclient.NewClientV2("oec_rc.asgw.conf", tConf)
    
    // 注册路由
    register(r)
    r.Spin()
}

// biz/handler/alarm_callback_proxy.go
func AlarmCallbackProxy(ctx context.Context, c *app.RequestContext) {
    // 高性能处理告警回调
    // 转发到 Python AI 层进行智能分析
}
```

**面试话术：**
> "这个项目我们采用了 Go + Python 的混合架构。Go 作为核心服务层，使用字节内部的 Hertz 框架，处理告警回调、业务逻辑等高并发场景，性能非常优秀。Python 作为 AI 智能层，利用 LlamaIndex、LangGraph 等成熟框架实现 RAG 检索和 Agent 编排。两层通过 HTTP 通信，可以独立部署和扩展。这种设计既保证了核心服务的性能，又能充分利用 Python 的 AI 生态。"

**可能追问：**
- Q: 为什么不全用 Go？
  > A: Go 的 AI 生态不够成熟，LLM SDK、RAG 框架支持都不如 Python。全用 Go 会大大增加开发成本。
  
- Q: 两层怎么通信？
  > A: 通过 HTTP REST API。Go 层处理完基础请求后，需要 AI 分析的部分转发给 Python 层。这样也便于后续引入 gRPC 优化。

- Q: 部署复杂度怎么解决？
  > A: 使用 Docker Compose 统一编排，Go 和 Python 作为独立容器。生产环境可以用 K8s 分别控制副本数。

---

## 三、面试高频问题

### 3.1 项目背景类

#### Q1: 为什么做这个项目？解决了什么问题？

**回答模板：**
> "在做运维的时候，我们发现几个痛点：
> 
> 1. **告警量大**：每天几百条告警，人工处理不过来
> 2. **知识分散**：资深工程师的经验没法传承，新人上手慢
> 3. **响应慢**：平均故障定位要 2-4 小时
> 
> 这个项目的目标是把故障诊断时间从小时级缩短到分钟级，同时把团队经验沉淀下来。"

#### Q2: 项目的技术选型依据是什么？

**回答模板：**
> "技术选型主要考虑三个因素：
> 
> 1. **团队能力**：团队 Python 比较熟悉，所以后端选了 FastAPI
> 2. **生态成熟度**：LangChain/LlamaIndex 生态成熟，文档完善
> 3. **生产就绪**：Qdrant、Neo4j 都是生产级产品
> 
> 具体来说：
> - FastAPI：异步支持好，自动生成文档，适合 AI 场景
> - Semi Design：字节出品，设计一致性好
> - Qdrant：性能好，支持过滤，开源可自部署"

#### Q3: 项目目前的进展和成果？

**回答模板：**
> "目前项目已经完成核心功能开发：
> 
> **量化成果：**
> - 代码量：20,000+ 行 Python，1,700+ 行 TypeScript
> - 模块数：12 个核心模块
> - API 端点：50+ 个
> 
> **业务成果：**
> - 诊断时间：从 2-4 小时缩短到 5-10 分钟
> - 知识复用：已沉淀 50+ 诊断案例
> - 用户满意度：4.5/5.0 评分"

---

### 3.2 架构设计类

#### Q4: 介绍一下整体架构？

**回答模板：**
> "整体是分层架构，从上到下分为：
> 
> 1. **前端层**：React + Semi Design，6 个核心页面
> 2. **API 层**：FastAPI，统一网关，50+ 端点
> 3. **Agent 层**：核心智能层，包含编排、路由、各类 Agent
> 4. **服务层**：LLM Gateway、知识服务、可视化服务
> 5. **存储层**：Qdrant(向量)、Neo4j(图谱)、Redis(缓存)、MinIO(文件)
> 
> 关键设计点是 Agent 层，我们用 LangGraph 实现了状态机编排，可以根据意图动态调整执行流程。"

#### Q5: 为什么用微服务而不是单体？

**回答模板：**
> "目前是模块化单体，没有完全微服务化。原因：
> 
> 1. **团队规模**：小团队，微服务运维成本高
> 2. **开发效率**：模块化单体开发更快，部署简单
> 3. **性能足够**：QPS 不高，单体完全能承载
> 
> 但我们做了模块化设计，每个模块有清晰的边界，未来需要可以拆分。"

#### Q6: 如果流量增长 10 倍，怎么扩展？

**回答模板：**
> "分三个层面考虑：
> 
> **1. 应用层：**
> - 水平扩展 API 服务实例
> - 引入负载均衡
> 
> **2. 数据层：**
> - Qdrant 分片
> - Redis 集群
> - 读写分离
> 
> **3. 性能优化：**
> - 热点数据缓存
> - 异步处理耗时操作
> - LLM 响应流式输出"

---

### 3.3 Agent 设计类

#### Q7: Agent 的协作模式有哪些？怎么选择的？

**回答模板：**
> "我们设计了四种协作模式：
> 
> | 模式 | 场景 | 特点 |
> |------|------|------|
> | Sequential | 复杂诊断 | 步骤可控，便于调试 |
> | Parallel | 简单查询 | 响应快 |
> | Hierarchical | 多层分析 | 层级内并行，效率高 |
> | Debate | 争议问题 | 多角度分析 |
> 
> 选择策略：
> - 简单查询(如'是什么') → Parallel
> - 复杂诊断(如'故障排查') → Sequential
> - 多维度分析(如'对比分析') → Hierarchical"

#### Q8: Agent 状态机如何控制推理和工具调用？

**回答模板：**
> "我们没有让模型自由循环调用工具，而是用 LangGraph 将执行过程拆成受控节点：
> 
> ```
> 循环：
> 1. Router：识别意图并决定路径
> 2. Knowledge/Tools：获取知识和结构化数据证据
> 3. Reasoning：基于证据分析
> 4. Reflection：低置信度时有限重试，随后输出或失败
> ```
> 
> 实现要点：
> - max_iterations 限制重试次数，防止死循环
> - Checkpoint 支持中断后恢复
> - Tool Runtime 统一校验、超时、重试、权限和幂等"

#### Q9: 怎么保证 Agent 推理的稳定性？

**回答模板：**
> "我们做了几层保障：
> 
> 1. **结构化输出**：要求 Agent 输出 JSON，便于解析和验证
> 2. **重试机制**：失败自动重试，最多 3 次
> 3. **降级策略**：LLM 失败时用规则引擎兜底
> 4. **温度控制**：诊断场景用低温度(0.3)，减少随机性
> 5. **自我反思**：执行后让 Agent 检查结果合理性"

---

### 3.4 RAG 技术类

#### Q10: 向量检索的原理是什么？

**回答模板：**
> "向量检索的核心步骤：
> 
> 1. **Embedding**：把文本转成高维向量(768维)
>    - 用 BGE-M3 模型，中文效果好
> 
> 2. **索引构建**：向量存入 Qdrant
>    - HNSW 算法，支持 ANN 查询
> 
> 3. **相似度计算**：余弦相似度
>    - cos(a, b) = a·b / (|a|·|b|)
> 
> 4. **Top-K 检索**：返回最相似的 K 个文档"

#### Q11: 为什么用混合检索？RRF 原理是什么？

**回答模板：**
> "单一检索都有局限：
> - 向量检索：语义匹配好，但精确关键词可能遗漏
> - 关键词检索：精确匹配，但无语义理解
> 
> RRF (Reciprocal Rank Fusion) 原理：
> 
> ```python
> score(doc) = Σ 1/(k + rank(doc))
> ```
> 
> k 是平滑参数(默认60)，rank 是文档在各检索器中的排名。
> 
> 优势：
> 1. 不需要训练，无监督方法
> 2. 对排名不敏感，鲁棒性好
> 3. 易于实现和理解"

#### Q12: 分块策略怎么设计的？

**回答模板：**
> "我们使用滑动窗口分块：
> 
> - chunk_size: 500 tokens
> - chunk_overlap: 50 tokens
> 
> 为什么这样设计：
> 
> 1. **500 tokens**：
>    - 太小：上下文不完整
>    - 太大：检索精度下降
>    - 500 是平衡点
> 
> 2. **50 tokens 重叠**：
>    - 保证边界信息不丢失
>    - 避免关键句子被截断
> 
> 进阶：我们还支持语义分块，根据句子边界自动切分"

#### Q13: 怎么处理表格和图片？

**回答模板：**
> "不同内容类型有不同处理策略：
> 
> **表格：**
> - Markdown 格式保留结构
> - 关键数值提取为文本
> - 表头作为元数据
> 
> **图片：**
> - OCR 提取文字
> - 多模态模型生成描述
> - 关键区域标注
> 
> **流程图：**
> - 提取节点和边
> - 转换为结构化描述"

---

### 3.5 LLM 相关类

#### Q14: 怎么控制 LLM 的输出格式？

**回答模板：**
> "我们用几种方法：
> 
> 1. **Prompt 约束**：
>    ```
>    请输出 JSON 格式，包含以下字段：
>    - diagnosis: 诊断结论
>    - confidence: 置信度(0-1)
>    - suggestions: 建议列表
>    ```
> 
> 2. **Few-shot 示例**：
>    提供标准输出示例，让模型学习格式
> 
> 3. **输出解析**：
>    - 正则提取 JSON
>    - 失败时重试或降级
> 
> 4. **Function Calling**：
>    OpenAI 支持结构化输出"

#### Q15: Prompt 怎么设计的？

**回答模板：**
> "我们的 Prompt 设计遵循几个原则：
> 
> 1. **角色定义**：'你是一位经验丰富的运维专家'
> 
> 2. **任务明确**：明确要做什么，输出什么格式
> 
> 3. **上下文注入**：
>    ```
>    用户问题: {query}
>    知识库信息: {knowledge}
>    指标数据: {metrics}
>    ```
> 
> 4. **思维链引导**：
>    ```
>    请按以下步骤分析：
>    1. 问题确认
>    2. 信息整理
>    3. 假设生成
>    4. 验证推理
>    5. 结论输出
>    ```
> 
> 5. **边界约束**：'如果信息不足，请明确说明'"

#### Q16: 怎么降低 LLM 调用成本？

**回答模板：**
> "我们从几个方面优化成本：
> 
> 1. **模型路由**：
>    - 简单查询用 GPT-3.5 ($0.0005/1K tokens)
>    - 复杂诊断用 GPT-4 ($0.03/1K tokens)
>    - 成本差异 60 倍
> 
> 2. **缓存策略**：
>    - 相似问题直接返回缓存
>    - Embedding 结果缓存
> 
> 3. **Token 优化**：
>    - Prompt 压缩
>    - 只检索 Top-3 文档
>    - 截断过长上下文
> 
> 4. **批量处理**：
>    - Embedding 批量计算
>    - 减少请求次数"

---

### 3.6 工程实践类

#### Q17: 怎么保证系统稳定性？

**回答模板：**
> "从多个层面保障：
> 
> **1. 代码层面：**
> - 类型提示 (Python Type Hints)
> - 单元测试覆盖核心逻辑
> - 异常处理和日志记录
> 
> **2. 架构层面：**
> - 熔断机制：LLM 超时自动降级
> - 限流：防止系统过载
> - 重试策略：指数退避
> 
> **3. 监控层面：**
> - OpenTelemetry 分布式追踪
> - 关键指标监控
> - 告警通知"

#### Q18: 怎么做性能优化？

**回答模板：**
> "性能优化分几个方向：
> 
> **1. 并发优化：**
> ```python
> # 多 Agent 并行执行
> results = await asyncio.gather(
>     knowledge_agent.execute(context),
>     tool_agent.execute(context),
> )
> ```
> 
> **2. 缓存优化：**
> - Redis 缓存热点查询
> - Embedding 结果缓存
> 
> **3. 响应优化：**
> - LLM 流式输出
> - 首字延迟优化
> 
> **4. 检索优化：**
> - 向量索引优化
> - 预计算常用查询"

#### Q19: 怎么做测试？

**回答模板：**
> "我们有三层测试：
> 
> **1. 单元测试：**
> - 测试各模块核心函数
> - Mock 外部依赖
> - 覆盖率 70%+
> 
> **2. 集成测试：**
> - 测试 API 端点
> - 测试 Agent 执行流程
> - 使用测试数据库
> 
> **3. 评估测试：**
> - RAGAS 指标评估
> - 测试集验证效果
> - 回归测试防止退化"

---

### 3.7 难点挑战类

#### Q20: 项目中遇到的最大挑战是什么？

**回答模板：**
> "最大挑战是 Agent 推理结果不稳定。
> 
> **问题：** 同一个问题多次执行，结果不一致，有时甚至完全错误。
> 
> **分析：**
> 1. LLM 本身有随机性
> 2. Prompt 设计不够明确
> 3. 没有推理过程约束
> 
> **解决：**
> 1. 降低 temperature 参数 (0.7 → 0.3)
> 2. 引入 ReAct 循环，强制分步推理
> 3. 添加自我反思机制
> 4. 构建评估体系持续监控
> 
> **效果：** 推理稳定性从 60% 提升到 85%"

#### Q21: 怎么处理用户反馈的问题？

**回答模板：**
> "我们有完整的反馈闭环：
> 
> 1. **收集反馈：**
>    - 点赞/点踩
>    - 详细评价
>    - 问题分类
> 
> 2. **问题分类：**
>    - 检索问题：召回不全
>    - 推理问题：逻辑错误
>    - 生成问题：表述不清
> 
> 3. **针对性优化：**
>    - 检索问题 → 扩展知识库
>    - 推理问题 → 改进 Prompt
>    - 生成问题 → 添加模板
> 
> 4. **效果验证：**
>    - 回归测试
>    - A/B 对比"

---

## 四、八股文知识点

### 4.1 Python 相关

#### 1. Python GIL 是什么？对多线程有什么影响？

**简答：**
> GIL (Global Interpreter Lock) 是 Python 的全局解释器锁，同一时刻只有一个线程执行 Python 字节码。
> 
> **影响：**
> - CPU 密集型任务：多线程无法利用多核
> - IO 密集型任务：影响不大，IO 期间释放 GIL
> 
> **解决方案：**
> - 使用 multiprocessing 替代 threading
> - 使用 asyncio 协程
> - 使用 C 扩展释放 GIL
> 
> **本项目应用：**
> 我们使用 asyncio 而不是多线程，因为 Agent 执行主要是 IO 密集型（LLM API 调用、数据库查询），asyncio 更轻量，性能更好。

#### 2. Python 的装饰器原理？

**简答：**
> 装饰器是一个函数，接收函数作为参数，返回一个新的函数。
> 
> ```python
> def trace_span(name):
>     def decorator(func):
>         @wraps(func)
>         async def wrapper(*args, **kwargs):
>             tracer.start_span(name)
>             result = await func(*args, **kwargs)
>             tracer.end_span()
>             return result
>         return wrapper
>     return decorator
> ```
> 
> **本项目应用：**
> 我们用装饰器实现追踪功能，`@trace_span` 自动记录函数执行时间和状态。

#### 3. Python 的异步编程原理？

**简答：**
> Python 异步基于协程 (coroutine) 和事件循环 (event loop)：
> 
> 1. `async def` 定义协程函数
> 2. `await` 挂起当前协程，让出控制权
> 3. 事件循环调度多个协程
> 
> **原理：**
> - 协程是用户态轻量级线程
> - 切换开销小，不需要内核参与
> - IO 操作时挂起，不阻塞线程
> 
> **本项目应用：**
> ```python
> async def parallel_retrieval(query):
>     # 并行执行多个检索
>     results = await asyncio.gather(
>         vector_search(query),
>         keyword_search(query),
>     )
>     return results
> ```

#### 4. Python 的内存管理机制？

**简答：**
> Python 使用引用计数 + 垃圾回收：
> 
> 1. **引用计数：**
>    - 每个对象有引用计数
>    - 引用为 0 时立即释放
> 
> 2. **垃圾回收：**
>    - 解决循环引用问题
>    - 分代回收策略
> 
> **优化建议：**
> - 避免循环引用
> - 使用 `__slots__` 减少内存
> - 大对象及时释放

#### 5. Python 的元类 (metaclass) 是什么？

**简答：**
> 元类是创建类的类。类是对象的模板，元类是类的模板。
> 
> ```python
> class SingletonMeta(type):
>     _instances = {}
>     def __call__(cls, *args, **kwargs):
>         if cls not in cls._instances:
>             cls._instances[cls] = super().__call__(*args, **kwargs)
>         return cls._instances[cls]
> 
> class AgentService(metaclass=SingletonMeta):
>     pass
> ```
> 
> **本项目应用：**
> 我们用元类实现单例模式，确保全局只有一个 AgentService 实例。

---

### 4.2 Go 语言相关

#### 6. Go 的 Goroutine 和 Channel 原理？

**简答：**
> Goroutine 是 Go 的轻量级协程，Channel 是协程间通信机制。
> 
> **Goroutine 特点：**
> - 初始栈仅 2KB，可动态增长
> - 由 Go 运行时调度，非内核线程
> - 创建开销小，可轻松创建百万级
> 
> **Channel 原理：**
> - 底层是环形缓冲区 + 锁
> - 分为无缓冲（同步）和有缓冲（异步）
> - 通过 make(chan T, size) 创建
> 
> **本项目应用：**
> 我们在 Go 层使用 Goroutine 并发处理多个告警回调，用 Channel 传递结果。
> ```go
> func processAlerts(alerts []Alert) {
>     ch := make(chan Result, len(alerts))
>     for _, alert := range alerts {
>         go func(a Alert) {
>             ch <- processSingle(a)
>         }(alert)
>     }
>     for range alerts {
>         result := <-ch
>         // 处理结果
>     }
> }
> ```

#### 7. Go 的 GMP 调度模型？

**简答：**
> GMP 是 Go 的调度模型：
> - **G (Goroutine)**：协程，用户态线程
> - **M (Machine)**：系统线程，执行 G
> - **P (Processor)**：逻辑处理器，持有本地 G 队列
> 
> **调度流程：**
> 1. P 的本地队列存放待运行的 G
> 2. M 从绑定的 P 获取 G 执行
> 3. G 阻塞时，M 释放 P，让其他 M 接管
> 4. 工作窃取：P 空闲时从其他 P 偷 G
> 
> **优势：**
> - 减少线程切换开销
> - 负载自动均衡
> - 适合高并发场景

#### 8. Go 的垃圾回收机制？

**简答：**
> Go 使用三色标记 + 写屏障的 GC：
> 
> **三色标记：**
> - 白色：未访问对象（待回收）
> - 灰色：已访问但成员未访问
> - 黑色：已访问完成（保留）
> 
> **写屏障：**
> - 解决并发标记时的对象变更
> - 插入写屏障：新引用对象标灰
> - 删除写屏障：旧引用对象标灰
> 
> **特点：**
> - 并发标记，STW 时间短（<1ms）
> - 适合高延迟敏感场景
> 
> **本项目应用：**
> Go 服务处理高并发请求，GC 暂停时间短，不影响请求延迟。

#### 9. Go 的 interface 原理？

**简答：**
> Go interface 分为两种：
> 
> 1. **eface (空接口)**：`interface{}`
>    ```go
>    type eface struct {
>        _type *_type      // 类型信息
>        data  unsafe.Pointer  // 数据指针
>    }
>    ```
> 
> 2. **iface (带方法接口)**：
>    ```go
>    type iface struct {
>        tab  *itab        // 接口表（类型+方法表）
>        data unsafe.Pointer
>    }
>    ```
> 
> **鸭子类型：**
> - 不需要显式声明实现
> - 只要方法签名匹配就满足接口
> 
> **本项目应用：**
> 我们定义了 Handler 接口，不同业务 Handler 实现该接口：
> ```go
> type Handler interface {
>     Handle(ctx context.Context, req *Request) (*Response, error)
> }
> ```

#### 10. Go 的 defer 原理？

**简答：**
> defer 延迟执行，在函数返回前按 LIFO 顺序执行。
> 
> **原理：**
> - 编译时将 defer 转换为 runtime.deferproc
> - 函数返回时调用 runtime.deferreturn
> - defer 链表存储在 Goroutine 结构中
> 
> **注意点：**
> - 参数在 defer 声明时求值
> - defer 在 return 之后、函数返回之前执行
> - 可以修改命名返回值
> 
> **本项目应用：**
> ```go
> func handleRequest(ctx context.Context, c *app.RequestContext) {
>     timer := metrics.StartTimer("request")
>     defer timer.Stop()  // 保证指标上报
>     
>     // 业务逻辑
> }
> ```

#### 11. Go context 原理和使用场景？

**简答：**
> Context 用于传递请求范围的数据、取消信号、截止时间。
> 
> **核心方法：**
> ```go
> context.Background()     // 根 Context
> context.WithCancel()     // 可取消
> context.WithTimeout()    // 超时取消
> context.WithValue()      // 传递值
> ```
> 
> **传播机制：**
> - 子 Context 继承父 Context 的取消信号
> - 父取消时，所有子 Context 都取消
> 
> **本项目应用：**
> ```go
> func (h *Handler) Process(ctx context.Context, req *Request) {
>     ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
>     defer cancel()
>     
>     // 超时自动取消，防止请求堆积
>     result, err := h.service.Call(ctx, req)
> }
> ```

#### 12. Go sync.Map 和普通 map 的区别？

**简答：**
> 普通 map 不是并发安全的，sync.Map 是并发安全的 map。
> 
> **sync.Map 原理：**
> - 使用空间换时间：read map + dirty map
> - 读优先从 read 读（无锁）
> - 写入 dirty（加锁），定期提升到 read
> - 适合读多写少场景
> 
> **适用场景：**
> - 读多写少：sync.Map 性能好
> - 读写均衡：用 map + sync.RWMutex
> - 写多：用 map + sync.Mutex
> 
> **本项目应用：**
> 我们用 sync.Map 缓存配置信息，定期从 TCC 刷新：
> ```go
> var configCache sync.Map
> 
> func getConfig(key string) interface{} {
>     if v, ok := configCache.Load(key); ok {
>         return v
>     }
>     // 从 TCC 加载
>     configCache.Store(key, value)
>     return value
> }
> ```

---

### 4.3 数据库相关

#### 6. 为什么用 Qdrant 而不是 Milvus/Pinecone？

**简答：**
> 选择 Qdrant 的原因：
> 
> 1. **开源可自部署**：数据安全可控
> 2. **性能好**：HNSW 索引，查询快
> 3. **功能丰富**：支持过滤、分片、快照
> 4. **轻量级**：单机部署简单
> 
> **对比：**
> - Milvus：功能更强但更重，适合超大规模
> - Pinecone：托管服务，国内访问不便

#### 7. 向量索引 HNSW 的原理？

**简答：**
> HNSW (Hierarchical Navigable Small World) 是一种 ANN (近似最近邻) 算法：
> 
> 1. **分层结构**：
>    - 多层图，上层稀疏，下层密集
>    - 类似跳表的思想
> 
> 2. **搜索过程**：
>    - 从顶层开始，贪心搜索
>    - 逐层下沉，缩小范围
> 
> 3. **优势**：
>    - 查询复杂度 O(log n)
>    - 支持动态插入
> 
> **本项目应用：**
> Qdrant 默认使用 HNSW，我们配置了 ef_construct=128 和 m=16 来平衡查询速度和索引质量。

#### 8. Redis 的数据结构有哪些？怎么用？

**简答：**
> Redis 核心数据结构：
> 
> 1. **String**：缓存、计数器
> 2. **Hash**：对象存储
> 3. **List**：消息队列
> 4. **Set**：去重、标签
> 5. **ZSet**：排行榜、延迟队列
> 
> **本项目应用：**
> - 缓存查询结果
> - 会话状态存储
> - 分布式锁

#### 9. 数据库索引的原理？

**简答：**
> 索引是加速查询的数据结构：
> 
> 1. **B+树索引**：
>    - 范围查询效率高
>    - 数据在叶子节点，非叶节点只存键
> 
> 2. **哈希索引**：
>    - 等值查询 O(1)
>    - 不支持范围查询
> 
> 3. **全文索引**：
>    - 倒排索引
>    - 支持关键词搜索
> 
> **本项目应用：**
> 我们在 skills 表上建了多个索引：
> - owner 索引：快速查询用户的 Skill
> - scope 索引：过滤作用域
> - FULLTEXT 索引：名称和描述搜索

---

### 4.3 计算机网络

#### 10. HTTP 和 HTTPS 的区别？

**简答：**
> | 特点 | HTTP | HTTPS |
> |------|------|-------|
> | 加密 | 明文传输 | SSL/TLS 加密 |
> | 端口 | 80 | 443 |
> | 证书 | 不需要 | 需要 CA 证书 |
> | 性能 | 快 | 略慢(握手开销) |
> 
> **HTTPS 握手过程：**
> 1. 客户端发起请求
> 2. 服务端返回证书
> 3. 客户端验证证书
> 4. 协商对称密钥
> 5. 加密通信

#### 11. RESTful API 设计原则？

**简答：**
> RESTful 设计原则：
> 
> 1. **资源为中心**：URL 表示资源
> 2. **HTTP 方法语义**：
>    - GET：查询
>    - POST：创建
>    - PUT：更新
>    - DELETE：删除
> 3. **状态码正确使用**：
>    - 200：成功
>    - 400：客户端错误
>    - 500：服务端错误
> 4. **无状态**：每个请求包含所有信息
> 
> **本项目应用：**
> ```
> GET    /api/skills/        # 列表
> POST   /api/skills/        # 创建
> GET    /api/skills/{id}    # 详情
> PUT    /api/skills/{id}    # 更新
> DELETE /api/skills/{id}    # 删除
> ```

#### 12. 什么是 CORS？怎么解决？

**简答：**
> CORS (Cross-Origin Resource Sharing) 跨域资源共享：
> 
> **原因：** 浏览器同源策略，阻止跨域请求
> 
> **解决方案：**
> 1. 服务端设置响应头：
>    ```
>    Access-Control-Allow-Origin: *
>    Access-Control-Allow-Methods: GET, POST, PUT, DELETE
>    ```
> 2. 预检请求处理：OPTIONS 请求返回允许的头
> 
> **本项目应用：**
> ```python
> app.add_middleware(
>     CORSMiddleware,
>     allow_origins=["http://localhost:5173"],
>     allow_methods=["*"],
>     allow_headers=["*"],
> )
> ```

---

### 4.4 操作系统

#### 13. 进程和线程的区别？

**简答：**
> | 特点 | 进程 | 线程 |
> |------|------|------|
> | 资源 | 独立地址空间 | 共享地址空间 |
> | 开销 | 大 | 小 |
> | 通信 | IPC | 共享内存 |
> | 崩溃影响 | 独立 | 可能影响整个进程 |
> 
> **Python 中的选择：**
> - IO 密集型：多线程 / 协程
> - CPU 密集型：多进程

#### 14. 什么是上下文切换？

**简答：**
> 上下文切换是 CPU 从一个进程/线程切换到另一个的过程：
> 
> 1. **保存当前上下文**：寄存器、程序计数器等
> 2. **切换到新上下文**：加载新进程状态
> 3. **恢复执行**
> 
> **开销：**
> - 直接开销：保存/恢复寄存器
> - 间接开销：缓存失效
> 
> **优化：**
> - 减少线程数
> - 使用协程替代线程

---

### 4.5 算法相关

#### 15. BM25 算法原理？

**简答：**
> BM25 是一种关键词检索排序算法：
> 
> ```
> score(D, Q) = Σ IDF(qi) * (f(qi, D) * (k1 + 1)) / (f(qi, D) + k1 * (1 - b + b * |D|/avgdl))
> ```
> 
> **核心要素：**
> 1. **词频 (TF)**：词在文档中出现次数
> 2. **逆文档频率 (IDF)**：词的区分度
> 3. **文档长度归一化**：避免长文档优势
> 
> **参数：**
> - k1：词频饱和参数，通常 1.2-2.0
> - b：文档长度归一化参数，通常 0.75

#### 16. 余弦相似度原理？

**简答：**
> 余弦相似度衡量两个向量的方向相似程度：
> 
> ```
> cos(A, B) = (A · B) / (|A| * |B|)
> ```
> 
> **特点：**
> - 值域 [-1, 1]
> - 关注方向，不关注长度
> - 适合文本相似度计算
> 
> **本项目应用：**
> 向量检索时用余弦相似度计算文档和查询的相似程度。

#### 17. RRF 融合排序原理？

**简答：**
> RRF (Reciprocal Rank Fusion) 是一种无监督的排序融合方法：
> 
> ```
> score(d) = Σ 1 / (k + rank(d))
> ```
> 
> **优势：**
> 1. 不需要训练
> 2. 对分数尺度不敏感
> 3. 计算简单高效
> 
> **示例：**
> - 文档 A 在向量检索排第 1，关键词检索排第 3
> - 分数 = 1/(60+1) + 1/(60+3) = 0.0164 + 0.0159 = 0.0323

---

### 4.6 系统设计

#### 18. 如何设计一个高可用系统？

**简答：**
> 高可用设计的核心原则：
> 
> 1. **冗余**：多实例部署，避免单点故障
> 2. **隔离**：故障隔离，避免级联
> 3. **降级**：核心功能保底，非核心可降级
> 4. **熔断**：防止故障扩散
> 5. **限流**：保护系统不过载
> 
> **本项目应用：**
> - LLM Gateway 熔断：主模型失败切换备用
> - 降级策略：LLM 不可用时用规则引擎
> - 缓存兜底：减少对后端压力

#### 19. 如何设计一个分布式追踪系统？

**简答：**
> 分布式追踪核心概念：
> 
> 1. **Trace**：一次请求的完整路径
> 2. **Span**：单个操作，包含开始时间、持续时间
> 3. **Context Propagation**：跨服务传递上下文
> 
> **实现要点：**
> 1. 生成 Trace ID 和 Span ID
> 2. 在服务间传递（HTTP Header）
> 3. 收集和存储追踪数据
> 4. 可视化展示调用链
> 
> **本项目应用：**
> 使用 OpenTelemetry 标准，每个 Agent 执行都有完整的追踪链路。

#### 20. 如何设计一个缓存策略？

**简答：**
> 缓存设计要点：
> 
> 1. **缓存什么**：
>    - 热点数据
>    - 计算成本高的数据
>    - 变化不频繁的数据
> 
> 2. **缓存策略**：
>    - Cache-Aside：先查缓存，没有则查库并回填
>    - Write-Through：写缓存同时写库
>    - Write-Behind：先写缓存，异步写库
> 
> 3. **失效策略**：
>    - TTL 过期
>    - LRU/LFU 淘汰
>    - 主动失效
> 
> **本项目应用：**
> - Embedding 结果缓存（TTL 1小时）
> - 知识库查询缓存（TTL 30分钟）

---

## 五、项目演示话术

### 5.1 一分钟介绍

> "这是一个智能运维诊断平台，核心是用 AI Agent 自动化故障诊断。系统集成了多 LLM 后端、LangGraph 状态机编排、混合检索 RAG、用户自定义 Skill 等特性。目前有 2 万行 Python 代码，12 个核心模块，能把故障定位时间从小时级缩短到分钟级。"

### 5.2 三分钟介绍

> "这个项目是智能运维诊断平台，解决的问题是故障诊断效率低、知识难以沉淀。
> 
> **技术亮点：**
> 1. **多 LLM 统一接入**：设计了 LLM Gateway，支持 OpenAI 和 Claude，还能根据任务自动选择最优模型
> 2. **状态机编排**：用 LangGraph 实现了灵活的 Agent 工作流，可以根据意图动态调整执行流程
> 3. **混合检索 RAG**：向量加关键词检索，用 RRF 融合排序，召回率提升 15-20%
> 4. **Skill 系统**：用户可以把成功流程保存成可复用的 Skill，自动推荐机制很方便
> 5. **完整评估体系**：引入 RAGAS 框架，可以量化 Agent 效果
> 
> **项目规模：**
> 2 万行 Python，106 个文件，50+ API 端点，6 个前端页面。
> 
> **业务效果：**
> 诊断时间从 2-4 小时缩短到 5-10 分钟，用户满意度 4.5 分。"

### 5.3 五分钟演示流程

> 1. **首页概览**（30秒）：展示系统功能模块和统计数据
> 2. **知识库管理**（1分钟）：上传文档、查看知识库列表
> 3. **智能对话**（2分钟）：
>    - 演示一个诊断问题
>    - 展示执行追踪
>    - 展示 Skill 推荐弹窗
> 4. **Skill 管理**（1分钟）：展示预设 Skill、执行一个 Skill
> 5. **可视化**（30秒）：演示自然语言生成图表

---

## 六、面试策略

### 6.1 如何引导面试官

**技巧：** 在回答中埋点，引导面试官追问你擅长的内容

**示例：**
> 回答："我们用 LangGraph 实现了状态机编排..."
> 
> 埋点："状态机的好处是每个状态变化都可以追踪，调试很方便。"
> 
> 期望追问："状态机具体怎么设计的？" 或 "追踪怎么做的？"

### 6.2 遇到不会的问题怎么办

**策略：**
1. **诚实承认**："这个问题我没有深入研究过"
2. **尝试关联**："不过我在项目中遇到过类似的..."
3. **展示思考**："如果让我设计，我会考虑..."

**示例：**
> "Redis 集群怎么做数据分片？这个我还没实际部署过。不过我知道 Redis Cluster 用的是一致性哈希，考虑到我们项目目前流量不大，单机 Redis 就够用了。如果将来需要扩展，我会先调研 Codis 或者 Redis Cluster 方案。"

### 6.3 如何展示技术深度

**技巧：** 用"问题-方案-权衡"的结构

**示例：**
> "在设计 LLM Gateway 时，我们面临一个选择：是用同步还是异步？
> 
> 问题：Agent 执行涉及多次 LLM 调用，同步会阻塞。
> 
> 方案：我们选择了全异步设计，用 asyncio.gather 并行执行。
> 
> 权衡：异步调试更难，但性能提升明显。我们加了完善的日志和追踪来弥补。"

---

## 七、常见追问

### 7.1 关于项目的追问

| 问题 | 核心考察点 |
|------|-----------|
| 为什么选择这个技术方案？ | 技术判断力 |
| 有没有考虑过其他方案？ | 技术广度 |
| 如果重新做，会有什么改进？ | 反思能力 |
| 遇到过什么坑？怎么解决的？ | 实战经验 |
| 项目中你主要负责什么？ | 贡献度 |
| 项目上线了吗？效果怎么样？ | 业务价值 |

### 7.2 关于技术的追问

| 问题 | 核心考察点 |
|------|-----------|
| 这个原理是什么？ | 理解深度 |
| 性能瓶颈在哪？怎么优化？ | 性能意识 |
| 怎么测试的？覆盖了哪些场景？ | 工程素养 |
| 如果数据量增加 10 倍怎么办？ | 架构能力 |
| 有没有踩过坑？ | 实践经验 |

---

## 八、总结

### 核心记忆点

1. **项目定位**：智能运维诊断平台
2. **核心价值**：故障定位从小时级到分钟级
3. **技术亮点**：LLM Gateway、LangGraph、混合检索、Skill 系统、RAGAS 评估
4. **项目规模**：2万行代码、12个模块、50+ API
5. **技术栈**：FastAPI、React、Qdrant、OpenAI/Claude

### 面试必背

1. 项目介绍：30秒版本、1分钟版本、3分钟版本
2. 技术亮点：每个亮点准备 3 分钟讲解
3. 难点挑战：准备 2-3 个有深度的例子
4. 八股文：重点准备 Python 异步、向量检索、分布式追踪

### 面试心态

1. 自信但不傲慢
2. 诚实承认不会的
3. 展示学习能力和思考能力
4. 引导到熟悉的领域
