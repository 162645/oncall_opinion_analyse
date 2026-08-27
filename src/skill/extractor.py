"""
Skill 提取器
从成功的对话中提取可复用的 Skill
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import json
import logging
import re

from .models import Skill, SkillStep, SkillParam, SkillTrigger, SkillCategory, SkillStatus, SkillScope
from .service import SkillService, get_skill_service
from src.llm.gateway import LLMGateway, get_llm_gateway

logger = logging.getLogger(__name__)


@dataclass
class SkillExtractionResult:
    """Skill 提取结果"""
    can_extract: bool
    skill_name: str = ""
    description: str = ""
    category: str = "custom"
    tags: List[str] = field(default_factory=list)
    trigger_keywords: List[str] = field(default_factory=list)
    workflow: List[Dict[str, Any]] = field(default_factory=list)
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    reason: str = ""
    confidence: float = 0.0


class SkillExtractor:
    """
    从成功对话中提取 Skill

    工作流程:
    1. 分析对话内容，判断是否可提取
    2. 提取工作流步骤
    3. 识别可参数化的变量
    4. 生成触发关键词
    5. 返回完整的 Skill 定义
    """

    def __init__(self, llm_gateway: Optional[LLMGateway] = None, skill_service: Optional[SkillService] = None):
        self.llm = llm_gateway or get_llm_gateway()
        self.skill_service = skill_service or get_skill_service()

    async def analyze_conversation(
        self,
        messages: List[Dict[str, Any]],
        tool_calls: List[Dict[str, Any]],
        trace: List[Dict[str, Any]],
        result: Dict[str, Any],
    ) -> SkillExtractionResult:
        """
        分析对话是否可以提炼为 Skill

        Args:
            messages: 对话消息列表
            tool_calls: 工具调用列表
            trace: 执行追踪
            result: 最终结果

        Returns:
            SkillExtractionResult
        """
        # 基本检查
        if not messages:
            return SkillExtractionResult(
                can_extract=False,
                reason="对话内容为空",
            )

        # 检查是否成功
        if not result.get("success", True):
            return SkillExtractionResult(
                can_extract=False,
                reason="对话未成功完成",
            )

        # 提取用户问题
        user_messages = [m for m in messages if m.get("role") == "user"]
        if not user_messages:
            return SkillExtractionResult(
                can_extract=False,
                reason="没有用户消息",
            )

        user_query = user_messages[-1].get("content", "")

        # 使用 LLM 分析是否可提取
        extraction_prompt = self._build_extraction_prompt(
            user_query=user_query,
            tool_calls=tool_calls,
            trace=trace,
            result=result,
        )

        try:
            response = await self.llm.generate(
                prompt=extraction_prompt,
                config=self.llm.config,
            )

            # 解析 LLM 响应
            return self._parse_llm_response(response.content, user_query)

        except Exception as e:
            logger.error(f"Skill extraction failed: {e}")
            return SkillExtractionResult(
                can_extract=False,
                reason=f"分析失败: {str(e)}",
            )

    def _build_extraction_prompt(
        self,
        user_query: str,
        tool_calls: List[Dict[str, Any]],
        trace: List[Dict[str, Any]],
        result: Dict[str, Any],
    ) -> str:
        """构建提取提示"""

        tool_calls_str = json.dumps(tool_calls, ensure_ascii=False, indent=2) if tool_calls else "[]"
        trace_str = json.dumps(trace, ensure_ascii=False, indent=2) if trace else "[]"
        result_str = json.dumps(result, ensure_ascii=False, indent=2) if result else "{}"

        return f"""分析以下对话，判断是否可以提炼为可复用的 Skill（技能）。

## 用户问题
{user_query}

## 工具调用
```json
{tool_calls_str}
```

## 执行追踪
```json
{trace_str}
```

## 执行结果
```json
{result_str}
```

## 分析要求

请判断：
1. 是否是成功的对话？
2. 是否具有可复用性？（不是一次性任务）
3. 是否可以通过参数化实现通用化？

如果可以提取，请提供以下信息：
- skill_name: 简洁、描述性的技能名称（中文，3-8个字）
- description: 技能描述（说明这个技能做什么）
- category: 分类，从以下选择：diagnosis（故障诊断）、analysis（数据分析）、operation（运维操作）、visualization（可视化）、custom（自定义）
- tags: 标签列表，用于搜索和分类
- trigger_keywords: 触发关键词列表，用户输入这些词时可以推荐此技能
- workflow: 工作流步骤列表，每步包含 step_type（agent/tool/retrieval）、name、config
- parameters: 可参数化的参数列表，每项包含 name、type（string/number/enum）、description、required
- confidence: 提取置信度（0.0-1.0）

## 输出格式

请以 JSON 格式返回：
```json
{{
    "can_extract": true/false,
    "skill_name": "技能名称",
    "description": "技能描述",
    "category": "分类",
    "tags": ["标签1", "标签2"],
    "trigger_keywords": ["关键词1", "关键词2"],
    "workflow": [
        {{
            "step_type": "agent/tool/retrieval",
            "name": "步骤名称",
            "config": {{}}
        }}
    ],
    "parameters": [
        {{
            "name": "参数名",
            "type": "string/number/enum",
            "description": "参数描述",
            "required": true/false
        }}
    ],
    "confidence": 0.85,
    "reason": "为什么可以/不可以提取"
}}
```

只输出 JSON，不要有其他内容。
"""

    def _parse_llm_response(self, response: str, user_query: str) -> SkillExtractionResult:
        """解析 LLM 响应"""
        try:
            # 提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                return SkillExtractionResult(
                    can_extract=False,
                    reason="无法解析 LLM 响应",
                )

            data = json.loads(json_match.group())

            return SkillExtractionResult(
                can_extract=data.get("can_extract", False),
                skill_name=data.get("skill_name", ""),
                description=data.get("description", ""),
                category=data.get("category", "custom"),
                tags=data.get("tags", []),
                trigger_keywords=data.get("trigger_keywords", []),
                workflow=data.get("workflow", []),
                parameters=data.get("parameters", []),
                reason=data.get("reason", ""),
                confidence=data.get("confidence", 0.0),
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return SkillExtractionResult(
                can_extract=False,
                reason=f"JSON 解析失败: {str(e)}",
            )

    async def extract_and_create(
        self,
        messages: List[Dict[str, Any]],
        tool_calls: List[Dict[str, Any]],
        trace: List[Dict[str, Any]],
        result: Dict[str, Any],
        owner: str,
        name_override: Optional[str] = None,
    ) -> Optional[Skill]:
        """
        提取并创建 Skill

        Args:
            messages: 对话消息列表
            tool_calls: 工具调用列表
            trace: 执行追踪
            result: 执行结果
            owner: 创建者
            name_override: 覆盖名称

        Returns:
            创建的 Skill，如果无法提取则返回 None
        """
        # 分析对话
        extraction_result = await self.analyze_conversation(
            messages=messages,
            tool_calls=tool_calls,
            trace=trace,
            result=result,
        )

        if not extraction_result.can_extract:
            logger.info(f"Cannot extract skill: {extraction_result.reason}")
            return None

        # 检查相似 Skill
        similar_skills = await self.skill_service.find_similar(
            extraction_result.skill_name,
            extraction_result.description,
        )

        if similar_skills and similar_skills[0].score > 0.8:
            logger.warning(f"Similar skill exists: {similar_skills[0].skill.name}")
            # 可以选择更新现有 Skill 或返回 None
            return None

        # 创建 Skill
        skill = await self.skill_service.create(
            name=name_override or extraction_result.skill_name,
            description=extraction_result.description,
            owner=owner,
            workflow=extraction_result.workflow,
            trigger={
                "keywords": extraction_result.trigger_keywords,
            },
            parameters=extraction_result.parameters,
            tags=extraction_result.tags,
            category=extraction_result.category,
            scope="personal",
        )

        logger.info(f"Created skill from conversation: {skill.name} (id={skill.id})")
        return skill

    async def suggest_skill_from_query(
        self,
        query: str,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        根据用户查询建议创建新 Skill

        分析用户的问题模式，建议可能需要的 Skill

        Args:
            query: 用户查询
            user_id: 用户 ID

        Returns:
            建议的 Skill 列表
        """
        suggestions = []

        # 检查常见模式
        patterns = [
            {
                "pattern": r"分析\s+(\S+)\s+(延迟|RTT|延迟)",
                "suggested_name": "延迟分析",
                "category": "analysis",
                "description": "分析指定目标的延迟数据",
            },
            {
                "pattern": r"诊断\s+(\S+)\s+(问题|故障|异常)",
                "suggested_name": "故障诊断",
                "category": "diagnosis",
                "description": "诊断指定目标的故障问题",
            },
            {
                "pattern": r"查询\s+(\S+)\s+(日志|指标|数据)",
                "suggested_name": "数据查询",
                "category": "operation",
                "description": "查询指定类型的数据",
            },
            {
                "pattern": r"画(一个|张)\s+(.+)\s+(图|趋势)",
                "suggested_name": "可视化生成",
                "category": "visualization",
                "description": "生成数据可视化图表",
            },
        ]

        for pattern_info in patterns:
            match = re.search(pattern_info["pattern"], query)
            if match:
                # 检查是否已有类似 Skill
                existing = await self.skill_service.search(
                    query=pattern_info["suggested_name"],
                    user_id=user_id,
                )

                if not existing:
                    suggestions.append({
                        "name": pattern_info["suggested_name"],
                        "description": pattern_info["description"],
                        "category": pattern_info["category"],
                        "example_query": query,
                    })

        return suggestions


# 全局实例
_extractor: Optional[SkillExtractor] = None


def get_skill_extractor() -> SkillExtractor:
    """获取 Skill 提取器实例"""
    global _extractor
    if _extractor is None:
        _extractor = SkillExtractor()
    return _extractor
