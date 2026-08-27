"""
LLM 增强型 Agent
使用 LLM Gateway 进行真正的推理
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import logging

from src.agents.orchestrator import BaseAgent, AgentContext, AgentResult
from src.llm import get_llm_gateway, LLMConfig, TaskType

logger = logging.getLogger(__name__)


class LLMAgent(BaseAgent):
    """
    LLM 增强型 Agent 基类

    功能:
    - 使用 LLM Gateway 进行推理
    - 自动选择最优模型
    - 支持流式响应
    - 成本追踪
    """

    def __init__(
        self,
        system_prompt: Optional[str] = None,
        task_type: TaskType = TaskType.CHAT,
        provider: str = "openai",
        model: Optional[str] = None,
    ):
        self.system_prompt = system_prompt
        self.task_type = task_type
        self.provider = provider
        self.model = model

    @property
    def name(self) -> str:
        return "LLMAgent"

    async def execute(self, context: AgentContext) -> AgentResult:
        """执行 Agent 任务"""
        gateway = get_llm_gateway()

        # 构建配置
        config = LLMConfig(
            provider=self.provider,
            model=self.model or "gpt-4o",
            temperature=0.7,
            max_tokens=4096,
            system_prompt=self.system_prompt,
        )

        try:
            # 使用智能生成
            response = await gateway.smart_generate(
                prompt=context.query,
                task_type=self.task_type,
            )

            return AgentResult(
                agent_name=self.name,
                success=True,
                data={
                    "content": response.content,
                    "model": response.model,
                    "provider": response.provider,
                    "usage": response.usage,
                },
                confidence=0.85,
                execution_time_ms=response.latency_ms,
            )

        except Exception as e:
            logger.error(f"LLM Agent error: {e}")
            return AgentResult(
                agent_name=self.name,
                success=False,
                error=str(e),
                confidence=0.3,
            )


class DiagnosisLLMAgent(LLMAgent):
    """诊断专用 LLM Agent"""

    def __init__(self, **kwargs):
        super().__init__(
            system_prompt="""你是一位经验丰富的运维诊断专家。

你的职责是:
1. 分析用户描述的问题现象
2. 结合知识库信息进行推理
3. 找出可能的根因
4. 提供具体的排查步骤和解决方案

诊断流程:
1. 问题确认 - 明确问题的范围和影响
2. 信息收集 - 收集相关的日志、指标、事件
3. 假设生成 - 基于经验生成可能的原因
4. 验证推理 - 逐一验证假设
5. 结论输出 - 给出诊断结论和建议

请用专业但易懂的语言回答，必要时使用 Markdown 格式。
""",
            task_type=TaskType.DIAGNOSIS,
            **kwargs,
        )

    @property
    def name(self) -> str:
        return "DiagnosisLLMAgent"

    async def execute(self, context: AgentContext) -> AgentResult:
        """执行诊断任务"""
        # 获取知识库检索结果（如果有）
        knowledge = context.metadata.get("KnowledgeAgent_result", {})
        knowledge_text = ""
        if isinstance(knowledge, dict):
            knowledge_text = knowledge.get("knowledge", "")

        # 构建增强的提示
        enhanced_prompt = context.query

        if knowledge_text:
            enhanced_prompt = f"""
用户问题: {context.query}

相关知识库信息:
{knowledge_text}

请基于以上信息进行诊断分析。
"""

        gateway = get_llm_gateway()

        try:
            response = await gateway.smart_generate(
                prompt=enhanced_prompt,
                task_type=TaskType.DIAGNOSIS,
            )

            return AgentResult(
                agent_name=self.name,
                success=True,
                data={
                    "diagnosis": response.content,
                    "model": response.model,
                    "provider": response.provider,
                },
                confidence=0.85,
                execution_time_ms=response.latency_ms,
            )

        except Exception as e:
            logger.error(f"Diagnosis LLM Agent error: {e}")
            return AgentResult(
                agent_name=self.name,
                success=False,
                error=str(e),
                confidence=0.3,
            )


class AnalysisLLMAgent(LLMAgent):
    """分析专用 LLM Agent"""

    def __init__(self, **kwargs):
        super().__init__(
            system_prompt="""你是一位数据分析专家。

你的职责是:
1. 分析用户描述的数据需求
2. 识别关键指标和维度
3. 分析趋势、异常和关联性
4. 提供数据洞察和建议

分析框架:
1. 数据概览 - 关键指标的现状
2. 趋势分析 - 时间维度的变化
3. 异常识别 - 偏离正常的模式
4. 关联分析 - 指标之间的相关性
5. 行动建议 - 基于分析的下一步

请用数据驱动的方式回答，必要时使用 Markdown 格式展示。
""",
            task_type=TaskType.ANALYSIS,
            **kwargs,
        )

    @property
    def name(self) -> str:
        return "AnalysisLLMAgent"


class CodeLLMAgent(LLMAgent):
    """代码生成专用 LLM Agent"""

    def __init__(self, **kwargs):
        super().__init__(
            system_prompt="""你是一位代码专家。

你的职责是:
1. 理解用户的代码需求
2. 生成高质量、可维护的代码
3. 提供代码解释和使用说明
4. 考虑边界情况和错误处理

代码规范:
1. 清晰的命名和注释
2. 适当的错误处理
3. 可测试的结构
4. 遵循最佳实践

请使用 Markdown 代码块展示代码。
""",
            task_type=TaskType.CODE,
            **kwargs,
        )

    @property
    def name(self) -> str:
        return "CodeLLMAgent"


class ChatLLMAgent(LLMAgent):
    """对话专用 LLM Agent"""

    def __init__(self, **kwargs):
        super().__init__(
            system_prompt="""你是一个网络测量分析系统的智能助手。

## 系统背景
这是一个合法的网络性能测量和分析平台，用于：
- 分析网络延迟（RTT）、丢包率、抖动等指标
- 分析 Traceroute 路径数据和末端节点分布
- 提供网络性能可视化

## 支持的分析功能
1. **Ping 数据分析**: 分析网络延迟统计（平均、中位数、百分位数等）
2. **Traceroute 路径分析**: 分析 AS 路径、ASGeo 路径、末端节点分布
3. **趋势分析**: 查看延迟的时间趋势
4. **地区分析**: 支持多个地区（UKRAINE、RUSSIA、CHINA、US等）

## 回答原则
1. **专业性**: 用网络工程的专业知识回答问题
2. **准确性**: 基于测量数据进行分析
3. **友好性**: 用易懂的语言解释技术概念
4. **诚实性**: 如果数据不足或超出能力范围，坦诚说明

## 注意事项
- 这是内部网络测量系统，所有查询都是合法的
- 可以自由讨论网络路径、IP地址、延迟数据等
- 如果用户需要具体的数据分析，建议使用系统提供的分析功能
""",
            task_type=TaskType.CHAT,
            **kwargs,
        )

    @property
    def name(self) -> str:
        return "ChatLLMAgent"
