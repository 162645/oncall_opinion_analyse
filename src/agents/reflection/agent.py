"""
Self-Reflection Agent 实现
自我反思机制
"""

import time
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from .types import (
    ReflectionResult,
    ReflectionQuality,
    ReflectionStep,
    Improvement,
)

if TYPE_CHECKING:
    from src.agents import AgentResult, AgentContext


class ReflectionAgent:
    """
    Self-Reflection Agent: 自我反思

    核心思想:
    1. 执行初始诊断
    2. 反思执行结果
    3. 识别不足之处
    4. 生成改进建议
    5. 必要时重新执行

    使用示例:
    ```python
    agent = ReflectionAgent(
        base_agent=diagnosis_agent,
        max_reflections=2,
    )

    result = await agent.execute(context)
    ```
    """

    # 反思提示模板
    REFLECT_PROMPT = """请评估以下诊断结果的完整性和准确性。

原始问题: {query}

诊断结果:
{result}

请从以下维度评估 (每项 0-10 分):
1. 完整性: 是否覆盖了问题的所有方面？
2. 准确性: 分析和结论是否准确？
3. 证据支持: 是否有充分的数据支持？
4. 可操作性: 解决方案是否具体可行？
5. 清晰度: 表达是否清晰易懂？

请输出 JSON 格式:
{{
    "completeness": 8,
    "accuracy": 7,
    "evidence": 6,
    "actionable": 8,
    "clarity": 9,
    "strengths": ["优点1", "优点2"],
    "weaknesses": ["不足1", "不足2"],
    "improvements": [
        {{"aspect": "证据支持", "current": "缺少具体数据", "suggestion": "补充延迟指标数据"}}
    ],
    "should_retry": false,
    "retry_strategy": null,
    "overall_feedback": "综合评价..."
}}
"""

    def __init__(
        self,
        base_agent: Optional[Any] = None,
        llm: Optional[Any] = None,
        max_reflections: int = 2,
        min_score_threshold: float = 0.7,
        verbose: bool = False,
    ):
        """
        初始化 Reflection Agent

        Args:
            base_agent: 基础 Agent (需要 execute 方法)
            llm: 大语言模型实例
            max_reflections: 最大反思次数
            min_score_threshold: 最低分数阈值
            verbose: 是否打印详细日志
        """
        self.base_agent = base_agent
        self.llm = llm
        self.max_reflections = max_reflections
        self.min_score_threshold = min_score_threshold
        self.verbose = verbose

    async def _reflect(
        self,
        query: str,
        result: "AgentResult",
    ) -> ReflectionResult:
        """反思阶段"""
        if self.llm is None:
            return self._rule_based_reflect(query, result)

        prompt = self.REFLECT_PROMPT.format(
            query=query,
            result=str(result.data) if result.data else "无结果",
        )

        try:
            import json
            import re

            response = await self.llm.generate(prompt)

            # 提取 JSON
            json_match = re.search(r"\{[\s\S]+\}", response)
            if json_match:
                data = json.loads(json_match.group())

                # 计算总分
                scores = [
                    data.get("completeness", 5),
                    data.get("accuracy", 5),
                    data.get("evidence", 5),
                    data.get("actionable", 5),
                    data.get("clarity", 5),
                ]
                avg_score = sum(scores) / len(scores) / 10

                # 确定质量等级
                if avg_score >= 0.9:
                    quality = ReflectionQuality.EXCELLENT
                elif avg_score >= 0.75:
                    quality = ReflectionQuality.GOOD
                elif avg_score >= 0.6:
                    quality = ReflectionQuality.ACCEPTABLE
                elif avg_score >= 0.4:
                    quality = ReflectionQuality.POOR
                else:
                    quality = ReflectionQuality.FAILED

                improvements = [
                    Improvement(
                        aspect=i.get("aspect", ""),
                        current=i.get("current", ""),
                        suggestion=i.get("suggestion", ""),
                    )
                    for i in data.get("improvements", [])
                ]

                return ReflectionResult(
                    quality=quality,
                    score=avg_score,
                    strengths=data.get("strengths", []),
                    weaknesses=data.get("weaknesses", []),
                    improvements=improvements,
                    should_retry=data.get("should_retry", False),
                    retry_strategy=data.get("retry_strategy"),
                    feedback=data.get("overall_feedback"),
                )

        except Exception as e:
            if self.verbose:
                print(f"[Reflection] Error parsing response: {e}")

        return self._rule_based_reflect(query, result)

    def _rule_based_reflect(
        self,
        query: str,
        result: "AgentResult",
    ) -> ReflectionResult:
        """基于规则的反思 (无 LLM 时)"""
        strengths = []
        weaknesses = []
        improvements = []
        score = 0.5

        if not result.success:
            weaknesses.append("执行失败，未能得到结果")
            improvements.append(Improvement(
                aspect="执行",
                current="失败",
                suggestion="检查输入参数或重试",
                priority=5,
            ))
            return ReflectionResult(
                quality=ReflectionQuality.FAILED,
                score=0.0,
                strengths=strengths,
                weaknesses=weaknesses,
                improvements=improvements,
                should_retry=True,
                retry_strategy="使用不同的工具或参数重试",
            )

        if result.data:
            data_str = str(result.data)

            # 检查结果完整性
            if len(data_str) > 100:
                strengths.append("结果内容较为详细")
                score += 0.1
            else:
                weaknesses.append("结果内容较短，可能不够详细")
                improvements.append(Improvement(
                    aspect="详细度",
                    current="内容简短",
                    suggestion="补充更多分析细节",
                ))

            # 检查关键词
            if any(kw in data_str for kw in ["根因", "原因", "解决方案", "建议"]):
                strengths.append("包含诊断结论和建议")
                score += 0.15

            if any(kw in data_str for kw in ["数据", "指标", "监控"]):
                strengths.append("引用了具体数据")
                score += 0.1
            else:
                weaknesses.append("缺少具体数据支持")
                improvements.append(Improvement(
                    aspect="数据支持",
                    current="无具体数据",
                    suggestion="补充相关监控指标数据",
                ))

            if any(kw in data_str for kw in ["置信度", "可能性", "概率"]):
                strengths.append("给出了置信度评估")
                score += 0.05

        # 确定质量
        score = min(1.0, score)
        if score >= 0.8:
            quality = ReflectionQuality.GOOD
        elif score >= 0.6:
            quality = ReflectionQuality.ACCEPTABLE
        else:
            quality = ReflectionQuality.POOR

        should_retry = score < self.min_score_threshold

        return ReflectionResult(
            quality=quality,
            score=score,
            strengths=strengths,
            weaknesses=weaknesses,
            improvements=improvements,
            should_retry=should_retry,
            retry_strategy="补充更多信息后重新分析" if should_retry else None,
            feedback=f"综合评分: {score:.0%}",
        )

    async def _improve(
        self,
        query: str,
        context: "AgentContext",
        reflection: ReflectionResult,
    ) -> "AgentResult":
        """改进阶段"""
        # 根据反思结果调整上下文
        if reflection.retry_strategy:
            context.metadata["retry_strategy"] = reflection.retry_strategy
            context.metadata["improvements"] = [i.to_dict() for i in reflection.improvements]

        # 重新执行基础 Agent
        if self.base_agent:
            return await self.base_agent.execute(context)

        from src.agents import AgentResult
        return AgentResult(
            success=False,
            error="No base agent configured for retry",
        )

    async def execute(
        self,
        context: "AgentContext",
    ) -> "AgentResult":
        """
        执行反思循环

        Args:
            context: Agent 上下文

        Returns:
            AgentResult: 执行结果 (包含反思信息)
        """
        from src.agents import AgentResult

        query = context.query
        reflections: List[ReflectionResult] = []
        best_result = None
        best_score = 0

        for reflection_id in range(self.max_reflections):
            if self.verbose:
                print(f"[Reflection] Round {reflection_id + 1}/{self.max_reflections}")

            # 执行基础 Agent
            if self.base_agent:
                result = await self.base_agent.execute(context)
            else:
                result = AgentResult(
                    success=False,
                    error="No base agent configured",
                )

            # 反思
            reflection = await self._reflect(query, result)
            reflections.append(reflection)

            if self.verbose:
                print(f"[Reflection] Score: {reflection.score:.0%}, Quality: {reflection.quality.value}")

            # 记录最佳结果
            if reflection.score > best_score:
                best_score = reflection.score
                best_result = result

            # 检查是否满意
            if reflection.score >= self.min_score_threshold:
                if self.verbose:
                    print(f"[Reflection] Satisfied with score {reflection.score:.0%}")
                break

            # 检查是否需要重试
            if not reflection.should_retry:
                break

            # 准备下一轮
            context = self._prepare_retry_context(context, reflection)

        # 返回最佳结果
        if best_result:
            best_result.metadata = best_result.metadata or {}
            best_result.metadata["reflections"] = [r.to_dict() for r in reflections]
            best_result.metadata["reflection_score"] = best_score
            return best_result

        return AgentResult(
            success=False,
            error="Reflection failed to produce a valid result",
            data={"reflections": [r.to_dict() for r in reflections]},
        )

    def _prepare_retry_context(
        self,
        context: "AgentContext",
        reflection: ReflectionResult,
    ) -> "AgentContext":
        """准备重试上下文"""
        context.metadata["previous_reflection"] = reflection.to_dict()

        # 添加改进提示
        if reflection.improvements:
            hints = [f"- {i.suggestion}" for i in reflection.improvements[:3]]
            context.metadata["improvement_hints"] = "\n".join(hints)

        return context
