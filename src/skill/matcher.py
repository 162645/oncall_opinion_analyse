"""
Skill 匹配器
将用户查询匹配到合适的 Skill
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging
import re

from .models import Skill
from .service import SkillService, get_skill_service

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """匹配结果"""
    skill: Skill
    score: float
    match_type: str  # keyword, intent, semantic, pattern
    matched_terms: List[str]
    params: Dict[str, Any]


class SkillMatcher:
    """
    Skill 匹配器

    支持多种匹配策略:
    1. 关键词匹配 - 匹配触发关键词
    2. 意图匹配 - 匹配识别的意图
    3. 语义匹配 - 使用向量相似度
    4. 模式匹配 - 使用正则表达式
    """

    def __init__(self, skill_service: Optional[SkillService] = None):
        self.skill_service = skill_service or get_skill_service()

    async def match(
        self,
        query: str,
        intent: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        team_id: Optional[str] = None,
        top_k: int = 5,
    ) -> List[MatchResult]:
        """
        匹配用户查询到 Skill

        Args:
            query: 用户查询
            intent: 识别的意图
            entities: 提取的实体
            user_id: 用户 ID
            team_id: 团队 ID
            top_k: 返回数量

        Returns:
            匹配结果列表
        """
        results = []

        # 获取可见的 Skills
        visible_skills = await self.skill_service._get_visible_skills(user_id, team_id)

        for skill in visible_skills:
            match_result = self._match_skill(
                skill=skill,
                query=query,
                intent=intent,
                entities=entities or {},
            )

            if match_result:
                results.append(match_result)

        # 按分数排序
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def _match_skill(
        self,
        skill: Skill,
        query: str,
        intent: Optional[str],
        entities: Dict[str, Any],
    ) -> Optional[MatchResult]:
        """匹配单个 Skill"""
        query_lower = query.lower()
        matched_terms = []
        scores = []

        # 1. 关键词匹配
        keyword_score, keyword_matches = self._match_keywords(skill, query_lower)
        if keyword_score > 0:
            scores.append(("keyword", keyword_score))
            matched_terms.extend(keyword_matches)

        # 2. 意图匹配
        intent_score = self._match_intent(skill, intent)
        if intent_score > 0:
            scores.append(("intent", intent_score))

        # 3. 模式匹配
        pattern_score, pattern_matches = self._match_pattern(skill, query)
        if pattern_score > 0:
            scores.append(("pattern", pattern_score))
            matched_terms.extend(pattern_matches)

        # 计算总分
        if not scores:
            return None

        # 加权平均
        weights = {
            "keyword": 0.4,
            "intent": 0.3,
            "pattern": 0.3,
        }

        total_score = sum(
            score * weights.get(match_type, 0.2)
            for match_type, score in scores
        )

        # 考虑 Skill 质量分数
        final_score = total_score * 0.7 + skill.quality_score * 0.3

        # 提取参数
        params = self._extract_params(skill, query, entities)

        # 确定主要匹配类型
        match_type = max(scores, key=lambda x: x[1])[0] if scores else "keyword"

        return MatchResult(
            skill=skill,
            score=final_score,
            match_type=match_type,
            matched_terms=list(set(matched_terms)),
            params=params,
        )

    def _match_keywords(self, skill: Skill, query: str) -> tuple[float, List[str]]:
        """关键词匹配"""
        matches = []
        for keyword in skill.trigger.keywords:
            if keyword.lower() in query:
                matches.append(keyword)

        if not matches:
            return 0.0, []

        # 匹配比例
        score = len(matches) / max(len(skill.trigger.keywords), 1)
        return min(score, 1.0), matches

    def _match_intent(self, skill: Skill, intent: Optional[str]) -> float:
        """意图匹配"""
        if not intent or not skill.trigger.intent:
            return 0.0

        if intent == skill.trigger.intent:
            return 1.0

        # 相似意图
        similar_intents = {
            "diagnosis": ["troubleshoot", "debug", "investigate"],
            "analysis": ["analyze", "examine", "study"],
            "operation": ["execute", "run", "perform"],
            "query": ["search", "find", "lookup"],
        }

        for main_intent, similar in similar_intents.items():
            if skill.trigger.intent == main_intent and intent in similar:
                return 0.7
            if intent == main_intent and skill.trigger.intent in similar:
                return 0.7

        return 0.0

    def _match_pattern(self, skill: Skill, query: str) -> tuple[float, List[str]]:
        """模式匹配"""
        if not skill.trigger.pattern:
            return 0.0, []

        try:
            match = re.search(skill.trigger.pattern, query, re.IGNORECASE)
            if match:
                return 1.0, [match.group(0)]
        except re.error:
            pass

        return 0.0, []

    def _extract_params(
        self,
        skill: Skill,
        query: str,
        entities: Dict[str, Any],
    ) -> Dict[str, Any]:
        """提取参数"""
        params = {}

        for param in skill.parameters:
            # 首先检查实体
            if param.name in entities:
                params[param.name] = entities[param.name]
                continue

            # 尝试从查询中提取
            if param.type == "string":
                # 查找参数名附近的值
                pattern = rf"{param.name}[:\s]+(\S+)"
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    params[param.name] = match.group(1)
                    continue

            elif param.type == "number":
                # 查找数字
                pattern = rf"{param.name}[:\s]+(\d+\.?\d*)"
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    params[param.name] = float(match.group(1))
                    continue

            # 使用默认值
            if param.default is not None:
                params[param.name] = param.default

        return params

    async def find_best_match(
        self,
        query: str,
        intent: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        team_id: Optional[str] = None,
        min_score: float = 0.5,
    ) -> Optional[MatchResult]:
        """
        找到最佳匹配

        Args:
            query: 用户查询
            intent: 意图
            entities: 实体
            user_id: 用户 ID
            team_id: 团队 ID
            min_score: 最低分数

        Returns:
            最佳匹配结果，如果没有则返回 None
        """
        results = await self.match(
            query=query,
            intent=intent,
            entities=entities,
            user_id=user_id,
            team_id=team_id,
            top_k=1,
        )

        if results and results[0].score >= min_score:
            return results[0]

        return None

    async def get_skill_recommendation(
        self,
        query: str,
        intent: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取 Skill 推荐

        返回更详细的推荐信息，包括是否推荐创建新 Skill

        Args:
            query: 用户查询
            intent: 意图
            user_id: 用户 ID

        Returns:
            推荐信息
        """
        matches = await self.match(
            query=query,
            intent=intent,
            user_id=user_id,
            top_k=3,
        )

        recommendation = {
            "has_match": len(matches) > 0,
            "best_match": None,
            "alternatives": [],
            "suggest_create": False,
            "message": "",
        }

        if matches:
            best = matches[0]
            recommendation["best_match"] = {
                "skill_id": best.skill.id,
                "skill_name": best.skill.name,
                "description": best.skill.description,
                "score": best.score,
                "matched_terms": best.matched_terms,
                "extracted_params": best.params,
            }

            if len(matches) > 1:
                recommendation["alternatives"] = [
                    {
                        "skill_id": m.skill.id,
                        "skill_name": m.skill.name,
                        "score": m.score,
                    }
                    for m in matches[1:]
                ]

            if best.score < 0.7:
                recommendation["suggest_create"] = True
                recommendation["message"] = "找到部分匹配的技能，但建议创建新技能"
            else:
                recommendation["message"] = f"推荐使用技能: {best.skill.name}"

        else:
            recommendation["suggest_create"] = True
            recommendation["message"] = "未找到匹配的技能，建议创建新技能"

        return recommendation


# 全局实例
_matcher: Optional[SkillMatcher] = None


def get_skill_matcher() -> SkillMatcher:
    """获取 Skill 匹配器实例"""
    global _matcher
    if _matcher is None:
        _matcher = SkillMatcher()
    return _matcher
