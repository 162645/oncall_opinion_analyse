# V5 版本规划：智能运维 Agent 增强

> **版本**: v5.0.0  
> **目标**: 集成开源框架，增强 Agent 智能化能力，打造生产级运维诊断平台

---

## 一、V4 现状分析

### 1.1 已实现功能

| 模块 | 功能 | 状态 |
|------|------|------|
| 知识库 | 多格式文档解析、向量检索、关键词检索、融合检索 | ✅ |
| Agent | 意图路由、多模式编排、ReAct、反思 | ✅ |
| 可视化 | 自然语言生成图表、多指标组合图 | ✅ |
| API | FastAPI 路由、知识库 CRUD、对话接口 | ✅ |
| 前端 | React + Semi Design、知识库管理、对话界面 | ✅ |
| 存储 | MinIO 文件存储、Redis 缓存、Qdrant 向量库 | ✅ |

### 1.2 存在的问题

| 问题 | 影响 | 优先级 |
|------|------|--------|
| **LLM 未真正接入** | Agent 推理能力弱，无法生成高质量回复 | 🔴 高 |
| **工具调用能力弱** | 无法执行实际运维操作（查询、执行命令） | 🔴 高 |
| **RAG 效果有限** | 检索策略简单，缺乏重排序和查询优化 | 🟡 中 |
| **知识图谱未启用** | 故障关联分析能力缺失 | 🟡 中 |
| **可观测性不足** | 难以追踪 Agent 执行过程和诊断问题 | 🟡 中 |
| **评估体系缺失** | 无法量化 Agent 效果 | 🟢 低 |

---

## 二、V5 目标

### 2.1 核心目标

```
┌─────────────────────────────────────────────────────────────┐
│                     V5 核心目标                              │
├─────────────────────────────────────────────────────────────┤
│ 1. LLM 接入        - 支持多种 LLM 后端（OpenAI/Claude/本地）  │
│ 2. 工具能力增强    - MCP 协议 + 动态工具发现 + 自动调用       │
│ 3. RAG 效果提升    - LlamaIndex 集成 + 高级检索策略          │
│ 4. 可观测性完善    - OpenTelemetry + 分布式追踪              │
│ 5. 评估体系建立    - RAGAS 评估 + 效果量化                   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 能力提升预期

| 维度 | V4 | V5 | 提升 |
|------|-----|-----|------|
| 问题理解准确率 | 60% | 85% | +25% |
| 诊断结论准确率 | 50% | 80% | +30% |
| 工具调用成功率 | 0% | 90% | 新增 |
| 知识检索召回率 | 40% | 75% | +35% |
| 用户满意度 | - | 可量化 | 新增 |

---

## 三、架构设计

### 3.1 V5 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户界面层 (React + Semi)                       │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐   │
│  │ 知识库管理 │ │ 对话界面  │ │ 可视化展示 │ │ 工具管理  │ │ 评估报告  │   │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API 网关层 (FastAPI)                            │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    统一 API 网关 + 认证 + 限流 + 追踪                   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Agent 智能层                                    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Agent Orchestrator (增强版)                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐  │   │
│  │  │ IntentRouter│  │ LangGraph   │  │ ToolRouter                  │  │   │
│  │  │ 意图理解    │  │ 状态机编排  │  │ 工具路由                    │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐       │
│  │   KnowledgeAgent  │  │   ToolAgent       │  │  DiagnosisAgent   │       │
│  │   (LlamaIndex)    │  │   (MCP + 动态)    │  │   (ReAct + 反思)  │       │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘       │
│                                                                             │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐       │
│  │  VisualizationAg  │  │   GraphAgent      │  │   EvalAgent       │       │
│  │   (高级可视化)    │  │   (知识图谱)      │  │   (效果评估)      │       │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐
│   LLM Gateway          │ │   Tool Layer          │ │   Knowledge Layer     │
│  ┌─────────────────┐   │ │  ┌─────────────────┐  │ │  ┌─────────────────┐  │
│  │ OpenAI Adapter  │   │ │  │ MCP Tools       │  │ │  │ LlamaIndex      │  │
│  │ Claude Adapter  │   │ │  │ - Prometheus    │  │ │  │ Vector Index    │  │
│  │ Local Adapter   │   │ │  │ - ClickHouse    │  │ │  │ GraphRAG        │  │
│  │                 │   │ │  │ - Kubernetes    │  │ │  │ Hybrid Search   │  │
│  │ 统一接口 + 路由 │   │ │  │ - Shell         │  │ │  │ Reranker        │  │
│  └─────────────────┘   │ │  └─────────────────┘  │ │  └─────────────────┘  │
└───────────────────────┘ └───────────────────────┘ └───────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              存储与基础设施层                                │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │   Qdrant    │  │   Neo4j     │  │   Redis     │  │   MinIO     │       │
│  │  向量存储   │  │  知识图谱   │  │  缓存/队列  │  │  文件存储   │       │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                          │
│  │ Prometheus  │  │ ClickHouse  │  │ OpenObserve │  ← 新增：统一可观测性    │
│  │  监控指标   │  │  业务数据   │  │  日志追踪   │                          │
│  └─────────────┘  └─────────────┘  └─────────────┘                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 核心增强模块

#### 3.2.1 LLM Gateway (新增)

```python
# src/llm/gateway.py

class LLMGateway:
    """
    LLM 统一网关
    
    支持:
    - 多后端路由 (OpenAI, Claude, Local)
    - 自动故障转移
    - 成本优化
    - 流式响应
    """
    
    def __init__(self):
        self.adapters = {
            "openai": OpenAIAdapter(),
            "claude": ClaudeAdapter(),
            "local": LocalAdapter(),  # 本地模型
        }
        self.router = LLMRouter()  # 智能路由
    
    async def generate(
        self,
        prompt: str,
        model: str = "auto",
        **kwargs
    ) -> AsyncIterator[str]:
        """统一生成接口，支持流式输出"""
        adapter = self.router.select(model, prompt)
        async for chunk in adapter.generate(prompt, **kwargs):
            yield chunk
```

#### 3.2.2 Tool Layer (增强)

```python
# src/tools/mcp_manager.py

class MCPToolManager:
    """
    MCP 工具管理器
    
    功能:
    - 动态发现 MCP 服务器
    - 自动注册工具
    - 工具调用追踪
    """
    
    async def discover_tools(self) -> List[Tool]:
        """从 MCP 服务器发现可用工具"""
        tools = []
        for server in self.mcp_servers:
            server_tools = await server.list_tools()
            tools.extend(server_tools)
        return tools
    
    async def execute_tool(
        self,
        tool_name: str,
        params: dict,
    ) -> ToolResult:
        """执行工具调用，支持自动重试和超时"""
        tool = self.get_tool(tool_name)
        result = await tool.execute(**params)
        return result
```

#### 3.2.3 Knowledge Layer (LlamaIndex 集成)

```python
# src/knowledge/llama_index_service.py

from llama_index.core import VectorStoreIndex, Settings
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.flag_embedding import FlagEmbedding
from llama_index.postprocessor.cohere_rerank import CohereRerank

class LlamaIndexService:
    """
    LlamaIndex 知识服务
    
    特性:
    - 150+ 数据连接器
    - 高级索引策略
    - 自动查询优化
    - 多种重排序器
    """
    
    def __init__(self):
        # 配置 Embedding
        Settings.embed_model = FlagEmbedding(
            model_name="BAAI/bge-m3",
        )
        
        # 配置向量存储
        self.vector_store = QdrantVectorStore(...)
        
        # 配置重排序器
        self.reranker = CohereRerank(api_key="...")
    
    async def query(
        self,
        query: str,
        mode: str = "hybrid",
    ) -> Response:
        """
        智能查询
        
        mode:
        - "vector": 纯向量检索
        - "keyword": 关键词检索
        - "hybrid": 混合检索
        - "graph": 图谱增强检索
        """
        if mode == "hybrid":
            return await self._hybrid_query(query)
        elif mode == "graph":
            return await self._graph_rag_query(query)
```

---

## 四、集成开源工具清单

### 4.1 必须集成 (核心能力提升)

| 工具 | 版本 | 用途 | 集成点 | 优先级 |
|------|------|------|--------|--------|
| **LlamaIndex** | 0.10+ | RAG 框架，高级检索 | `src/knowledge/` | 🔴 P0 |
| **LangGraph** | 0.1+ | Agent 状态机编排 | `src/agents/` | 🔴 P0 |
| **OpenTelemetry** | 1.20+ | 分布式追踪 | `src/trace/` | 🔴 P0 |
| **RAGAS** | 0.1+ | RAG 评估框架 | `src/eval/` | 🔴 P0 |

### 4.2 建议集成 (能力增强)

| 工具 | 版本 | 用途 | 集成点 | 优先级 |
|------|------|------|--------|--------|
| **BGE-M3** | latest | 多语言 Embedding | `src/knowledge/` | 🟡 P1 |
| **AntV G6** | 5.0+ | 知识图谱可视化 | `frontend/` | 🟡 P1 |
| **DSPy** | 2.5+ | 声明式 LLM 编程 | `src/agents/` | 🟡 P1 |

### 4.3 可选集成 (锦上添花)

| 工具 | 版本 | 用途 | 集成点 | 优先级 |
|------|------|------|--------|--------|
| **OpenObserve** | latest | 统一可观测性 | 运维层 | 🟢 P2 |
| **DeepEval** | latest | LLM 测试框架 | `src/eval/` | 🟢 P2 |
| **React Flow** | 11+ | Agent 流程编辑 | `frontend/` | 🟢 P2 |

---

## 五、详细实现计划

### Phase 1: LLM Gateway (Week 1-2)

**目标**: 建立统一的 LLM 接入层

#### 1.1 文件结构

```
src/llm/
├── __init__.py
├── gateway.py              # LLM 统一网关
├── router.py               # 智能路由
├── adapters/
│   ├── __init__.py
│   ├── base.py             # Adapter 基类
│   ├── openai_adapter.py   # OpenAI 适配器
│   ├── claude_adapter.py   # Claude 适配器
│   └── local_adapter.py    # 本地模型适配器
├── prompts/
│   ├── __init__.py
│   ├── templates.py        # Prompt 模板
│   └── few_shot.py         # Few-shot 示例
└── utils/
    ├── token_counter.py    # Token 计数
    └── cost_tracker.py     # 成本追踪
```

#### 1.2 核心实现

```python
# src/llm/gateway.py

from typing import AsyncIterator, Optional, Dict, Any
from dataclasses import dataclass
import asyncio

@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str = "openai"  # openai, claude, local
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 4096
    stream: bool = True


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    model: str
    usage: Dict[str, int]
    latency_ms: int


class LLMGateway:
    """
    LLM 统一网关
    
    功能:
    1. 多后端支持 (OpenAI, Claude, Local)
    2. 智能路由 (根据任务选择最优模型)
    3. 自动故障转移
    4. 流式响应
    5. 成本追踪
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._adapters: Dict[str, "BaseAdapter"] = {}
        self._router = LLMRouter()
        
        # 初始化适配器
        self._init_adapters()
    
    def _init_adapters(self):
        """初始化所有适配器"""
        from .adapters import OpenAIAdapter, ClaudeAdapter, LocalAdapter
        
        self._adapters = {
            "openai": OpenAIAdapter(),
            "claude": ClaudeAdapter(),
            "local": LocalAdapter(),
        }
    
    async def generate(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        **kwargs
    ) -> LLMResponse:
        """
        同步生成响应
        """
        cfg = config or self.config
        adapter = self._adapters[cfg.provider]
        
        response = await adapter.generate(
            prompt=prompt,
            model=cfg.model,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            **kwargs
        )
        
        return response
    
    async def generate_stream(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式生成响应
        """
        cfg = config or self.config
        adapter = self._adapters[cfg.provider]
        
        async for chunk in adapter.generate_stream(
            prompt=prompt,
            model=cfg.model,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            **kwargs
        ):
            yield chunk
    
    async def generate_with_fallback(
        self,
        prompt: str,
        primary: str = "openai",
        fallback: str = "claude",
        **kwargs
    ) -> LLMResponse:
        """
        带故障转移的生成
        """
        try:
            return await self.generate(prompt, LLMConfig(provider=primary), **kwargs)
        except Exception as e:
            # 记录错误
            self._log_error(primary, e)
            # 尝试备用
            return await self.generate(prompt, LLMConfig(provider=fallback), **kwargs)
    
    def estimate_tokens(self, text: str) -> int:
        """估算 Token 数量"""
        # 简单估算: 中文约 1.5 字/token, 英文约 4 字符/token
        chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)


class LLMRouter:
    """
    智能路由器
    
    根据任务类型选择最优模型:
    - 简单查询 -> 快速模型 (gpt-3.5)
    - 复杂推理 -> 强力模型 (gpt-4)
    - 代码生成 -> 代码模型 (claude-3-opus)
    - 中文任务 -> 中文优化模型
    """
    
    def select(self, prompt: str, task_type: Optional[str] = None) -> tuple:
        """选择最优的 provider 和 model"""
        if task_type == "code":
            return "claude", "claude-3-opus-20240229"
        elif task_type == "simple":
            return "openai", "gpt-3.5-turbo"
        elif self._is_chinese_heavy(prompt):
            return "openai", "gpt-4-turbo"
        else:
            return "openai", "gpt-4"
    
    def _is_chinese_heavy(self, text: str) -> bool:
        """判断是否中文为主"""
        chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
        return chinese_chars / max(len(text), 1) > 0.5


# 全局实例
_gateway: Optional[LLMGateway] = None

def get_llm_gateway() -> LLMGateway:
    """获取 LLM 网关实例"""
    global _gateway
    if _gateway is None:
        _gateway = LLMGateway()
    return _gateway
```

#### 1.3 API 集成

```python
# src/api/router/llm.py

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class GenerateRequest(BaseModel):
    prompt: str
    provider: str = "openai"
    model: str = "gpt-4"
    stream: bool = False

@router.post("/generate")
async def generate(request: GenerateRequest):
    """LLM 生成接口"""
    from src.llm import get_llm_gateway, LLMConfig
    
    gateway = get_llm_gateway()
    config = LLMConfig(
        provider=request.provider,
        model=request.model,
        stream=request.stream,
    )
    
    if request.stream:
        # 流式响应
        from fastapi.responses import StreamingResponse
        async def stream():
            async for chunk in gateway.generate_stream(request.prompt, config):
                yield f"data: {chunk}\n\n"
        return StreamingResponse(stream(), media_type="text/event-stream")
    else:
        response = await gateway.generate(request.prompt, config)
        return {"content": response.content, "model": response.model}
```

### Phase 2: LangGraph Agent 编排 (Week 3-4)

**目标**: 使用 LangGraph 替代自研 Orchestrator，支持复杂状态流转

#### 2.1 文件结构

```
src/agents/langgraph/
├── __init__.py
├── graph_builder.py        # 图构建器
├── nodes/
│   ├── __init__.py
│   ├── router_node.py      # 路由节点
│   ├── knowledge_node.py   # 知识检索节点
│   ├── tool_node.py        # 工具调用节点
│   ├── reasoning_node.py   # 推理节点
│   └── output_node.py      # 输出节点
├── state/
│   ├── __init__.py
│   └── agent_state.py      # Agent 状态定义
└── tools/
    ├── __init__.py
    ├── prometheus_tool.py  # Prometheus 查询工具
    ├── clickhouse_tool.py  # ClickHouse 查询工具
    └── shell_tool.py       # Shell 执行工具
```

#### 2.2 核心实现

```python
# src/agents/langgraph/graph_builder.py

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

class AgentState(TypedDict):
    """Agent 状态"""
    messages: list          # 对话历史
    intent: str             # 识别的意图
    knowledge: str          # 检索到的知识
    tool_results: dict      # 工具调用结果
    reasoning: str          # 推理过程
    response: str           # 最终响应
    confidence: float       # 置信度


class AgentGraphBuilder:
    """
    LangGraph Agent 图构建器
    
    构建一个智能运维诊断图:
    
    [Router] → [Knowledge] → [Tools] → [Reasoning] → [Output]
         │           │           │            │
         └───────────┴───────────┴────────────┘
                       ↓
                    [END]
    """
    
    def __init__(self, llm_gateway):
        self.llm = llm_gateway
        self.tools = self._init_tools()
    
    def _init_tools(self) -> list:
        """初始化工具"""
        from .tools import PrometheusTool, ClickHouseTool, ShellTool
        return [
            PrometheusTool(),
            ClickHouseTool(),
            ShellTool(),
        ]
    
    def build(self) -> StateGraph:
        """构建 Agent 图"""
        # 创建状态图
        graph = StateGraph(AgentState)
        
        # 添加节点
        graph.add_node("router", self._router_node)
        graph.add_node("knowledge", self._knowledge_node)
        graph.add_node("tools", ToolNode(self.tools))
        graph.add_node("reasoning", self._reasoning_node)
        graph.add_node("output", self._output_node)
        
        # 设置入口
        graph.set_entry_point("router")
        
        # 添加边
        graph.add_conditional_edges(
            "router",
            self._route_intent,
            {
                "knowledge": "knowledge",
                "tools": "tools",
                "output": "output",
            }
        )
        
        graph.add_edge("knowledge", "reasoning")
        graph.add_edge("tools", "reasoning")
        graph.add_edge("reasoning", "output")
        graph.add_edge("output", END)
        
        return graph.compile()
    
    async def _router_node(self, state: AgentState) -> dict:
        """路由节点: 识别意图"""
        from src.llm import get_llm_gateway
        
        llm = get_llm_gateway()
        prompt = f"""分析用户问题，识别意图类型:

用户问题: {state['messages'][-1]}

意图类型:
- query: 简单知识查询
- diagnosis: 故障诊断分析
- action: 执行运维操作
- visualization: 数据可视化

只输出意图类型名称。"""
        
        response = await llm.generate(prompt)
        intent = response.content.strip().lower()
        
        return {"intent": intent}
    
    async def _knowledge_node(self, state: AgentState) -> dict:
        """知识检索节点"""
        from src.knowledge.service import get_knowledge_service
        
        service = get_knowledge_service()
        query = state['messages'][-1]
        
        result = await service.search(query, top_k=5)
        knowledge = "\n".join([r.content for r in result.results])
        
        return {"knowledge": knowledge}
    
    async def _reasoning_node(self, state: AgentState) -> dict:
        """推理节点"""
        from src.llm import get_llm_gateway
        
        llm = get_llm_gateway()
        
        prompt = f"""基于以下信息进行推理分析:

用户问题: {state['messages'][-1]}
知识库信息: {state.get('knowledge', '无')}
工具结果: {state.get('tool_results', {})}

请给出详细的分析过程和结论。"""
        
        response = await llm.generate(prompt)
        
        return {
            "reasoning": response.content,
            "confidence": 0.85,
        }
    
    async def _output_node(self, state: AgentState) -> dict:
        """输出节点: 生成最终响应"""
        from src.llm import get_llm_gateway
        
        llm = get_llm_gateway()
        
        prompt = f"""生成用户友好的响应:

用户问题: {state['messages'][-1]}
分析结论: {state.get('reasoning', '')}

请用清晰的结构化格式输出答案。"""
        
        response = await llm.generate(prompt)
        
        return {"response": response.content}
    
    def _route_intent(self, state: AgentState) -> str:
        """根据意图路由"""
        intent = state.get("intent", "query")
        
        if intent == "action":
            return "tools"
        elif intent in ["query", "diagnosis"]:
            return "knowledge"
        else:
            return "output"


# 全局图实例
_graph = None

def get_agent_graph():
    """获取 Agent 图实例"""
    global _graph
    if _graph is None:
        from src.llm import get_llm_gateway
        builder = AgentGraphBuilder(get_llm_gateway())
        _graph = builder.build()
    return _graph
```

### Phase 3: LlamaIndex 知识增强 (Week 5-6)

**目标**: 集成 LlamaIndex，提升检索效果

#### 3.1 文件结构

```
src/knowledge/llama_index/
├── __init__.py
├── service.py              # LlamaIndex 服务
├── indices/
│   ├── __init__.py
│   ├── vector_index.py     # 向量索引
│   ├── keyword_index.py    # 关键词索引
│   └── graph_index.py      # 图索引
├── readers/
│   ├── __init__.py
│   ├── pdf_reader.py       # PDF 读取器
│   ├── docx_reader.py      # Word 读取器
│   └── web_reader.py       # 网页读取器
├── retrievers/
│   ├── __init__.py
│   ├── hybrid_retriever.py # 混合检索器
│   └── graph_retriever.py  # 图谱检索器
└── postprocessors/
    ├── __init__.py
    ├── reranker.py         # 重排序器
    └── filter.py           # 过滤器
```

#### 3.2 核心实现

```python
# src/knowledge/llama_index/service.py

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.flag_embedding import FlagEmbeddingModel
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.postprocessor.cohere_rerank import CohereRerank
from qdrant_client import QdrantClient

class LlamaIndexKnowledgeService:
    """
    LlamaIndex 知识服务
    
    特性:
    1. 多种文档读取器
    2. 智能分块策略
    3. 混合检索 (向量 + 关键词)
    4. 自动重排序
    5. GraphRAG 支持
    """
    
    def __init__(
        self,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        embed_model: str = "BAAI/bge-m3",
    ):
        # 配置全局设置
        Settings.embed_model = FlagEmbeddingModel(model_name=embed_model)
        Settings.node_parser = SentenceSplitter(
            chunk_size=512,
            chunk_overlap=50,
        )
        
        # 初始化向量存储
        self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name="oncall_knowledge_v2",
        )
        
        # 初始化索引
        self.index = VectorStoreIndex.from_vector_store(
            self.vector_store,
        )
        
        # 初始化重排序器
        self.reranker = CohereRerank(
            api_key="...",  # 从配置读取
            top_n=5,
        )
    
    async def ingest_documents(
        self,
        file_paths: list[str],
    ) -> int:
        """
        导入文档
        
        支持: PDF, Word, Markdown, TXT, HTML
        """
        # 读取文档
        documents = SimpleDirectoryReader(
            input_files=file_paths,
        ).load_data()
        
        # 解析节点
        nodes = Settings.node_parser.get_nodes_from_documents(documents)
        
        # 添加到索引
        self.index.insert_nodes(nodes)
        
        return len(nodes)
    
    async def query(
        self,
        query: str,
        mode: str = "hybrid",
        top_k: int = 5,
        use_reranker: bool = True,
    ) -> "Response":
        """
        智能查询
        
        Args:
            query: 查询文本
            mode: 检索模式 (vector, keyword, hybrid, graph)
            top_k: 返回数量
            use_reranker: 是否使用重排序
        """
        # 创建检索器
        if mode == "hybrid":
            retriever = self._create_hybrid_retriever(top_k)
        elif mode == "graph":
            retriever = self._create_graph_retriever(top_k)
        else:
            retriever = self.index.as_retriever(similarity_top_k=top_k)
        
        # 检索
        nodes = retriever.retrieve(query)
        
        # 重排序
        if use_reranker and len(nodes) > 0:
            nodes = self.reranker.postprocess_nodes(
                nodes,
                query_str=query,
            )
        
        # 构建响应
        from llama_index.core import Response
        response_text = "\n\n---\n\n".join([
            f"**来源: {n.node.metadata.get('file_name', '未知')}**\n{n.node.text}"
            for n in nodes
        ])
        
        return Response(
            response=response_text,
            source_nodes=nodes,
        )
    
    def _create_hybrid_retriever(self, top_k: int):
        """创建混合检索器"""
        from llama_index.core.retrievers import VectorIndexRetriever
        from llama_index.retrievers.bm25 import BM25Retriever
        
        vector_retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=top_k,
        )
        
        bm25_retriever = BM25Retriever.from_defaults(
            nodes=list(self.index.docstore.docs.values()),
            similarity_top_k=top_k,
        )
        
        from llama_index.core.retrievers import QueryFusionRetriever
        return QueryFusionRetriever(
            retrievers=[vector_retriever, bm25_retriever],
            similarity_top_k=top_k,
            num_queries=1,
            mode="reciprocal_rerank",
        )
    
    def _create_graph_retriever(self, top_k: int):
        """创建图检索器 (GraphRAG)"""
        # TODO: 实现 GraphRAG
        pass
```

### Phase 4: OpenTelemetry 可观测性 (Week 7)

**目标**: 建立完整的可观测性体系

#### 4.1 文件结构

```
src/observability/
├── __init__.py
├── tracing.py              # 分布式追踪
├── metrics.py              # 指标收集
├── logging.py              # 结构化日志
├── middleware.py           # FastAPI 中间件
└── exporters/
    ├── __init__.py
    ├── otlp_exporter.py    # OTLP 导出器
    └── console_exporter.py # 控制台导出器
```

#### 4.2 核心实现

```python
# src/observability/tracing.py

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

class TracingManager:
    """
    追踪管理器
    
    功能:
    1. Agent 执行追踪
    2. 工具调用追踪
    3. LLM 调用追踪
    4. 自动 span 创建
    """
    
    def __init__(self, service_name: str = "oncall-agent"):
        # 创建资源
        resource = Resource.create({
            "service.name": service_name,
            "service.version": "5.0.0",
        })
        
        # 创建 TracerProvider
        provider = TracerProvider(resource=resource)
        
        # 添加导出器
        otlp_exporter = OTLPSpanExporter(
            endpoint="http://localhost:4317",
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        
        # 设置全局 tracer
        trace.set_tracer_provider(provider)
        self.tracer = trace.get_tracer(__name__)
    
    def trace_agent(self, agent_name: str):
        """Agent 执行追踪装饰器"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                with self.tracer.start_as_current_span(
                    f"agent.{agent_name}",
                    attributes={"agent.name": agent_name}
                ) as span:
                    try:
                        result = await func(*args, **kwargs)
                        span.set_attribute("agent.success", True)
                        return result
                    except Exception as e:
                        span.set_attribute("agent.success", False)
                        span.set_attribute("agent.error", str(e))
                        raise
            return wrapper
        return decorator
    
    def trace_tool(self, tool_name: str):
        """工具调用追踪装饰器"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                with self.tracer.start_as_current_span(
                    f"tool.{tool_name}",
                    attributes={"tool.name": tool_name}
                ) as span:
                    span.set_attribute("tool.params", str(kwargs))
                    result = await func(*args, **kwargs)
                    span.set_attribute("tool.result", str(result)[:500])
                    return result
            return wrapper
        return decorator


# 全局实例
_tracing_manager: Optional[TracingManager] = None

def get_tracing() -> TracingManager:
    global _tracing_manager
    if _tracing_manager is None:
        _tracing_manager = TracingManager()
    return _tracing_manager
```

### Phase 5: RAGAS 评估体系 (Week 8)

**目标**: 建立量化评估体系

#### 5.1 文件结构

```
src/evaluation/
├── __init__.py
├── ragas_evaluator.py      # RAGAS 评估器
├── metrics/
│   ├── __init__.py
│   ├── faithfulness.py     # 忠实度
│   ├── relevance.py        # 相关性
│   ├── context_recall.py   # 上下文召回
│   └── context_precision.py # 上下文精确
├── datasets/
│   ├── __init__.py
│   └── test_cases.py       # 测试数据集
└── reports/
    ├── __init__.py
    └── generator.py        # 报告生成器
```

#### 5.2 核心实现

```python
# src/evaluation/ragas_evaluator.py

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision,
)
from datasets import Dataset

class RAGASEvaluator:
    """
    RAGAS 评估器
    
    评估维度:
    1. Faithfulness (忠实度): 答案是否基于上下文
    2. Answer Relevancy (答案相关性): 答案与问题的相关性
    3. Context Recall (上下文召回): 检索是否完整
    4. Context Precision (上下文精确): 检索是否精确
    """
    
    def __init__(self, llm_gateway):
        self.llm = llm_gateway
        
        # 配置评估指标
        self.metrics = [
            faithfulness,
            answer_relevancy,
            context_recall,
            context_precision,
        ]
    
    async def evaluate(
        self,
        questions: list[str],
        answers: list[str],
        contexts: list[list[str]],
        ground_truths: Optional[list[str]] = None,
    ) -> dict:
        """
        执行评估
        
        Args:
            questions: 问题列表
            answers: 答案列表
            contexts: 上下文列表
            ground_truths: 标准答案 (可选)
        
        Returns:
            评估结果
        """
        # 构建数据集
        data = {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
        }
        
        if ground_truths:
            data["ground_truth"] = ground_truths
        
        dataset = Dataset.from_dict(data)
        
        # 执行评估
        results = evaluate(
            dataset,
            metrics=self.metrics,
        )
        
        return results.to_pandas().to_dict()
    
    async def evaluate_agent_session(
        self,
        session_id: str,
    ) -> dict:
        """
        评估 Agent 会话
        
        从会话历史中提取数据并评估
        """
        from src.api.router.chat import _sessions_db
        
        session = _sessions_db.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # 提取问题和答案
        questions = []
        answers = []
        contexts = []
        
        messages = session.get("messages", [])
        for i in range(0, len(messages) - 1, 2):
            if messages[i]["role"] == "user" and messages[i + 1]["role"] == "assistant":
                questions.append(messages[i]["content"])
                answers.append(messages[i + 1]["content"])
                contexts.append([])  # TODO: 从 trace 中提取 context
        
        return await self.evaluate(questions, answers, contexts)
    
    def generate_report(
        self,
        results: dict,
        output_path: str = "evaluation_report.html",
    ) -> str:
        """
        生成评估报告
        """
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        
        # 创建图表
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("忠实度", "答案相关性", "上下文召回", "上下文精确")
        )
        
        # 添加数据
        # ...
        
        # 保存报告
        fig.write_html(output_path)
        
        return output_path
```

---

## 六、依赖更新

### 6.1 requirements.txt 更新

```txt
# === V5 新增依赖 ===

# LLM Gateway
openai>=1.0.0
anthropic>=0.18.0
tiktoken>=0.5.0

# LangGraph Agent 编排
langgraph>=0.1.0
langchain-core>=0.3.0
langchain-openai>=0.2.0

# LlamaIndex RAG
llama-index-core>=0.10.0
llama-index-vector-stores-qdrant>=0.1.0
llama-index-embeddings-flag>=0.1.0
llama-index-postprocessor-cohere-rerank>=0.1.0
llama-index-retrievers-bm25>=0.1.0

# OpenTelemetry 可观测性
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-exporter-otlp>=1.20.0
opentelemetry-instrumentation-fastapi>=0.41b0

# RAGAS 评估
ragas>=0.1.0
datasets>=2.14.0

# Embedding
FlagEmbedding>=1.2.0
sentence-transformers>=2.2.0

# 其他
cohere>=4.0.0  # 重排序 API
```

### 6.2 frontend/package.json 更新

```json
{
  "dependencies": {
    "@antv/g6": "^5.0.0",
    "reactflow": "^11.0.0",
    "@xyflow/react": "^12.0.0"
  }
}
```

---

## 七、实施时间表

```
Week 1-2: Phase 1 - LLM Gateway
├── Day 1-3:   Adapter 实现 (OpenAI, Claude, Local)
├── Day 4-5:   Router 实现
├── Day 6-7:   API 集成 + 测试
└── Day 8-10:  文档 + Code Review

Week 3-4: Phase 2 - LangGraph Agent 编排
├── Day 1-3:   Graph 结构设计
├── Day 4-6:   Node 实现 (Router, Knowledge, Tools, Reasoning)
├── Day 7-8:   Tool 实现 (Prometheus, ClickHouse, Shell)
├── Day 9-10:  集成测试

Week 5-6: Phase 3 - LlamaIndex 知识增强
├── Day 1-3:   LlamaIndex 集成
├── Day 4-5:   混合检索器
├── Day 6-7:   GraphRAG
├── Day 8-10:  重排序 + 测试

Week 7: Phase 4 - OpenTelemetry 可观测性
├── Day 1-2:   Tracing 实现
├── Day 3-4:   Metrics 实现
├── Day 5:     Logging 实现
└── Day 6-7:   Dashboard 配置

Week 8: Phase 5 - RAGAS 评估体系
├── Day 1-3:   Evaluator 实现
├── Day 4-5:   测试数据集构建
└── Day 6-7:   报告生成器

Week 9-10: 集成测试 + 文档 + 发布
```

---

## 八、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| LLM API 成本超预算 | 高 | 实现智能路由，优先使用便宜模型 |
| LangGraph 学习曲线 | 中 | 先实现简单图，逐步增加复杂度 |
| LlamaIndex 版本兼容性 | 中 | 锁定版本，测试后再升级 |
| OpenTelemetry 性能开销 | 低 | 使用采样策略，生产环境采样率 10% |
| RAGAS 评估数据不足 | 中 | 构建合成数据集 + 人工标注 |

---

## 九、成功指标

| 指标 | V4 | V5 目标 | 验证方式 |
|------|-----|---------|---------|
| 问题理解准确率 | 60% | 85% | 意图分类测试集 |
| 诊断结论准确率 | 50% | 80% | 专家评审 |
| 工具调用成功率 | 0% | 90% | 工具调用日志 |
| 知识检索召回率 | 40% | 75% | RAGAS 评估 |
| 平均响应时间 | - | < 5s | 性能测试 |
| 用户满意度 | - | > 4.0/5.0 | 用户调研 |

---

## 十、附录

### A. 参考文档

- [LlamaIndex 官方文档](https://docs.llamaindex.ai/)
- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [OpenTelemetry 官方文档](https://opentelemetry.io/docs/)
- [RAGAS 官方文档](https://docs.ragas.io/)

### B. 相关 Issue/PR

- #XX: LLM Gateway 实现
- #XX: LangGraph 集成
- #XX: LlamaIndex 集成
- #XX: OpenTelemetry 集成
- #XX: RAGAS 评估集成

---

**文档版本**: v1.0  
**更新日期**: 2026-05-20  
**作者**: Claude Code
