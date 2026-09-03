# 思考过程可视化方案

## 一、核心设计

### 1. Trace 数据结构

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

class StepType(Enum):
    ROUTER = "router"           # 意图路由
    RETRIEVAL = "retrieval"     # 知识检索
    TOOL_CALL = "tool_call"     # 工具调用
    REASONING = "reasoning"     # 推理思考
    DECISION = "decision"       # 决策

@dataclass
class TraceStep:
    """单个追踪步骤"""
    step_id: int
    step_type: StepType
    agent_name: str
    action: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    reasoning: str                    # 思考过程
    confidence: float = 0.0
    duration_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    children: List["TraceStep"] = field(default_factory=list)

@dataclass
class ExecutionTrace:
    """完整执行追踪"""
    session_id: str
    query: str
    steps: List[TraceStep] = field(default_factory=list)
    final_result: Any = None
    total_duration_ms: int = 0

    def add_step(self, step: TraceStep):
        self.steps.append(step)

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "query": self.query,
            "steps": [
                {
                    "step_id": s.step_id,
                    "type": s.step_type.value,
                    "agent": s.agent_name,
                    "action": s.action,
                    "input": s.input_data,
                    "output": s.output_data,
                    "reasoning": s.reasoning,
                    "confidence": s.confidence,
                    "duration_ms": s.duration_ms,
                }
                for s in self.steps
            ],
            "total_duration_ms": self.total_duration_ms,
        }
```

### 2. Trace 收集器

```python
import time
from contextlib import contextmanager

class TraceCollector:
    """追踪收集器"""

    def __init__(self):
        self._current_trace: Optional[ExecutionTrace] = None
        self._step_counter = 0

    def start_trace(self, session_id: str, query: str):
        """开始追踪"""
        self._current_trace = ExecutionTrace(
            session_id=session_id,
            query=query,
        )
        self._step_counter = 0

    @contextmanager
    def trace_step(
        self,
        step_type: StepType,
        agent_name: str,
        action: str,
        input_data: Dict = None,
    ):
        """追踪单个步骤 (上下文管理器)"""
        start_time = time.time()
        step_id = self._step_counter
        self._step_counter += 1

        step = TraceStep(
            step_id=step_id,
            step_type=step_type,
            agent_name=agent_name,
            action=action,
            input_data=input_data or {},
        )

        try:
            yield step  # 让调用者填充 output 和 reasoning
        finally:
            step.duration_ms = int((time.time() - start_time) * 1000)
            if self._current_trace:
                self._current_trace.add_step(step)

    def end_trace(self, final_result: Any = None):
        """结束追踪"""
        if self._current_trace:
            self._current_trace.final_result = final_result
        return self._current_trace

    def get_trace(self) -> Optional[ExecutionTrace]:
        return self._current_trace


# 全局实例
trace_collector = TraceCollector()
```

### 3. Agent 集成

```python
class TracingAgent:
    """支持追踪的 Agent 基类"""

    def __init__(self, name: str, collector: TraceCollector = None):
        self.name = name
        self.collector = collector or trace_collector

    async def execute_with_trace(
        self,
        action: str,
        input_data: Dict,
        step_type: StepType = StepType.REASONING,
    ):
        """带追踪的执行"""
        with self.collector.trace_step(
            step_type=step_type,
            agent_name=self.name,
            action=action,
            input_data=input_data,
        ) as step:
            # 执行实际逻辑
            result = await self._do_execute(input_data)

            # 填充输出和思考过程
            step.output_data = result.get("data", {})
            step.reasoning = result.get("reasoning", "")
            step.confidence = result.get("confidence", 0.0)

            return result

    async def _do_execute(self, input_data: Dict) -> Dict:
        """子类实现"""
        raise NotImplementedError
```

### 4. 可视化渲染

```python
class TraceVisualizer:
    """追踪可视化"""

    @staticmethod
    def render_markdown(trace: ExecutionTrace) -> str:
        """渲染为 Markdown"""
        lines = [
            f"# 执行追踪: {trace.session_id}",
            f"",
            f"**查询**: {trace.query}",
            f"",
            "## 执行步骤",
            "",
        ]

        for step in trace.steps:
            emoji = {
                StepType.ROUTER: "🔀",
                StepType.RETRIEVAL: "📚",
                StepType.TOOL_CALL: "🔧",
                StepType.REASONING: "🧠",
                StepType.DECISION: "✅",
            }.get(step.step_type, "•")

            lines.append(f"### {emoji} Step {step.step_id}: {step.action}")
            lines.append(f"")
            lines.append(f"**Agent**: {step.agent_name}")
            lines.append(f"**耗时**: {step.duration_ms}ms")
            lines.append(f"**置信度**: {step.confidence:.2f}")
            lines.append(f"")

            if step.reasoning:
                lines.append(f"**思考过程**:")
                lines.append(f"```")
                lines.append(step.reasoning)
                lines.append(f"```")
                lines.append(f"")

            if step.input_data:
                lines.append(f"**输入**: `{step.input_data}`")
            if step.output_data:
                lines.append(f"**输出**: `{step.output_data}`")
            lines.append(f"---")
            lines.append(f"")

        return "\n".join(lines)

    @staticmethod
    def render_html(trace: ExecutionTrace) -> str:
        """渲染为 HTML (可交互)"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>执行追踪</title>
    <style>
        .step {{
            border-left: 3px solid #4CAF50;
            padding: 10px 20px;
            margin: 10px 0;
            background: #f9f9f9;
        }}
        .reasoning {{
            background: #fff3cd;
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
        }}
        .tool-call {{
            border-left-color: #2196F3;
        }}
        .confidence {{
            color: #4CAF50;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <h1>执行追踪</h1>
    <p><strong>查询</strong>: {trace.query}</p>

    {"".join(f'''
    <div class="step {step.step_type.value}">
        <h3>Step {step.step_id}: {step.action}</h3>
        <p>Agent: {step.agent_name} | 耗时: {step.duration_ms}ms</p>
        <p class="confidence">置信度: {step.confidence:.2f}</p>
        <div class="reasoning">
            <strong>思考过程:</strong><br>
            {step.reasoning}
        </div>
        <details>
            <summary>详细信息</summary>
            <pre>输入: {step.input_data}</pre>
            <pre>输出: {step.output_data}</pre>
        </details>
    </div>
    ''' for step in trace.steps)}
</body>
</html>
        """

    @staticmethod
    def render_json(trace: ExecutionTrace) -> str:
        """渲染为 JSON (API 用)"""
        import json
        return json.dumps(trace.to_dict(), indent=2, default=str)
```

## 二、使用示例

```python
# 初始化
collector = TraceCollector()

# 开始追踪
collector.start_trace("session-001", "新加坡区域网络延迟异常")

# Agent 执行 (自动追踪)
agent = KnowledgeAgent(collector=collector)
result = await agent.execute_with_trace(
    action="search_similar_cases",
    input_data={"query": "网络延迟", "top_k": 5},
    step_type=StepType.RETRIEVAL,
)

# 结束追踪
trace = collector.end_trace(result)

# 渲染
print(TraceVisualizer.render_markdown(trace))
# 或保存 HTML
with open("trace.html", "w") as f:
    f.write(TraceVisualizer.render_html(trace))
```

## 三、实时流式输出

```python
import asyncio
from typing import AsyncGenerator

class StreamingTrace:
    """流式追踪输出"""

    def __init__(self, collector: TraceCollector):
        self.collector = collector

    async def stream_steps(self) -> AsyncGenerator[str, None]:
        """流式输出每个步骤"""
        while True:
            trace = self.collector.get_trace()
            if trace:
                for step in trace.steps:
                    yield f"data: {TraceVisualizer.render_json(step)}\n\n"
            await asyncio.sleep(0.1)

            if trace and trace.final_result is not None:
                break

# FastAPI 集成
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.get("/trace/{session_id}/stream")
async def stream_trace(session_id: str):
    streaming = StreamingTrace(trace_collector)
    return StreamingResponse(
        streaming.stream_steps(),
        media_type="text/event-stream"
    )
```

## 四、与 Langfuse 集成 (LLM 可观测性)

```python
from langfuse import Langfuse

class LangfuseTracer:
    """Langfuse 追踪集成"""

    def __init__(self, public_key: str, secret_key: str):
        self.client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
        )

    def trace_execution(self, trace: ExecutionTrace):
        """上传追踪到 Langfuse"""
        langfuse_trace = self.client.trace(
            id=trace.session_id,
            name=trace.query,
        )

        for step in trace.steps:
            langfuse_trace.span(
                name=f"{step.agent_name}: {step.action}",
                metadata={
                    "reasoning": step.reasoning,
                    "confidence": step.confidence,
                    "input": step.input_data,
                    "output": step.output_data,
                },
            )

        self.client.flush()
```

## 五、效果展示

### Markdown 输出

```markdown
# 执行追踪: session-001

**查询**: 新加坡区域网络延迟异常

## 执行步骤

### 🔀 Step 0: 路由到诊断 Agent
**Agent**: RouterAgent
**耗时**: 15ms
**置信度**: 0.92

**思考过程**:
检测到关键词 "网络延迟"、"异常"，路由到故障诊断流程

---

### 📚 Step 1: 检索相似案例
**Agent**: KnowledgeAgent
**耗时**: 234ms
**置信度**: 0.88

**思考过程**:
1. 向量检索查询: "网络延迟异常 新加坡"
2. 找到 3 个相似案例
3. 最佳匹配 TK-12345 (延迟突增导致)

**输出**: `{"cases": ["TK-12345", "TK-67890"], "best_match": "TK-12345"}`

---

### 🔧 Step 2: 查询网络延迟数据
**Agent**: AnalysisAgent
**耗时**: 456ms

**思考过程**:
调用 query_network_latency 工具，发现 P99 延迟从 45ms 突增到 150ms

**输入**: `{"region": "Singapore", "time_range": "1h"}`
**输出**: `{"p99_latency_ms": 150, "baseline_ms": 45}`

---

### 🧠 Step 3: 综合诊断
**Agent**: DiagnosisAgent
**耗时**: 89ms
**置信度**: 0.85

**思考过程**:
综合分析:
1. 历史案例 TK-12345 显示类似症状由链路拥塞导致
2. 网络数据显示 P99 延迟突增 233%
3. 判断根因: 链路拥塞

**输出**: `{"root_cause": "链路拥塞", "confidence": 0.85}`
```
