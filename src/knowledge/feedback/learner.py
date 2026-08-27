"""
反馈闭环模块
实现在线学习和持续改进
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum


class FeedbackType(Enum):
    """反馈类型"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    CORRECTION = "correction"
    RATING = "rating"


@dataclass
class Feedback:
    """用户反馈"""
    session_id: str
    feedback_type: FeedbackType
    rating: Optional[int] = None  # 1-5
    comment: Optional[str] = None
    correct_root_cause: Optional[str] = None
    correct_solution: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class LearningSample:
    """学习样本"""
    query: str
    diagnosis_result: Dict[str, Any]
    feedback: Feedback
    created_at: datetime = field(default_factory=datetime.now)


class FeedbackLoop:
    """
    反馈闭环

    流程:
    1. 收集用户反馈
    2. 分析失败原因
    3. 生成改进样本
    4. 更新知识库
    """

    def __init__(
        self,
        knowledge_updater=None,
        feedback_storage=None,
    ):
        self.knowledge_updater = knowledge_updater
        self.feedback_storage = feedback_storage or InMemoryFeedbackStorage()
        self._learners: List["OnlineLearner"] = []

    def register_learner(self, learner: "OnlineLearner"):
        """注册学习者"""
        self._learners.append(learner)

    async def collect_feedback(
        self,
        session_id: str,
        feedback: Feedback,
    ) -> bool:
        """
        收集用户反馈

        Args:
            session_id: 会话ID
            feedback: 用户反馈

        Returns:
            是否成功
        """
        # 存储反馈
        await self.feedback_storage.save(session_id, feedback)

        # 通知学习者
        for learner in self._learners:
            await learner.on_feedback(session_id, feedback)

        return True

    async def analyze_failure(
        self,
        session_id: str,
        feedback: Feedback,
    ) -> Dict[str, Any]:
        """
        分析失败原因

        对于负面反馈，分析:
        1. 哪个环节出错
        2. 为什么出错
        3. 如何改进
        """
        if feedback.feedback_type not in [FeedbackType.NEGATIVE, FeedbackType.CORRECTION]:
            return {}

        analysis = {
            "session_id": session_id,
            "feedback_type": feedback.feedback_type.value,
            "issues": [],
            "improvements": [],
        }

        # 如果有正确的根因，说明根因识别错误
        if feedback.correct_root_cause:
            analysis["issues"].append({
                "type": "root_cause_error",
                "expected": feedback.correct_root_cause,
                "improvement": "需要优化根因识别逻辑或增加相关案例",
            })

        # 如果有正确的解决方案，说明推荐方案不合适
        if feedback.correct_solution:
            analysis["issues"].append({
                "type": "solution_error",
                "expected": feedback.correct_solution,
                "improvement": "需要更新解决方案库或调整推荐权重",
            })

        return analysis

    async def generate_improvement(
        self,
        session_id: str,
        original_diagnosis: Dict[str, Any],
        feedback: Feedback,
    ) -> Optional[LearningSample]:
        """
        生成改进样本

        基于用户反馈生成新的训练样本
        """
        # 获取原始诊断结果
        diagnosis = original_diagnosis

        # 创建学习样本
        sample = LearningSample(
            query=diagnosis.get("query", ""),
            diagnosis_result=diagnosis,
            feedback=feedback,
        )

        # 如果有修正信息，创建新的知识条目
        if feedback.correct_root_cause or feedback.correct_solution:
            new_knowledge = {
                "source": "user_feedback",
                "session_id": session_id,
                "query": sample.query,
                "correct_root_cause": feedback.correct_root_cause,
                "correct_solution": feedback.correct_solution,
                "original_diagnosis": diagnosis,
                "timestamp": datetime.now().isoformat(),
            }

            # 存储到知识库
            if self.knowledge_updater:
                await self.knowledge_updater.add_knowledge(new_knowledge)

        return sample

    async def get_feedback_stats(
        self,
        time_range_days: int = 30,
    ) -> Dict[str, Any]:
        """获取反馈统计"""
        feedbacks = await self.feedback_storage.get_recent(time_range_days)

        if not feedbacks:
            return {"total": 0}

        ratings = [f.rating for f in feedbacks if f.rating]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0

        positive = sum(1 for f in feedbacks if f.feedback_type == FeedbackType.POSITIVE)
        negative = sum(1 for f in feedbacks if f.feedback_type == FeedbackType.NEGATIVE)

        return {
            "total": len(feedbacks),
            "average_rating": round(avg_rating, 2),
            "positive_count": positive,
            "negative_count": negative,
            "satisfaction_rate": positive / len(feedbacks) if feedbacks else 0,
        }


class OnlineLearner:
    """
    在线学习器

    从反馈中持续学习改进
    """

    def __init__(self):
        self.samples: List[LearningSample] = []
        self.update_count = 0

    async def on_feedback(
        self,
        session_id: str,
        feedback: Feedback,
    ):
        """处理反馈"""
        # 根据反馈类型决定学习策略
        if feedback.feedback_type == FeedbackType.POSITIVE:
            # 正面反馈：增强当前策略
            await self._reinforce(session_id, feedback)

        elif feedback.feedback_type == FeedbackType.NEGATIVE:
            # 负面反馈：分析并改进
            await self._correct(session_id, feedback)

        elif feedback.feedback_type == FeedbackType.CORRECTION:
            # 修正反馈：直接学习正确答案
            await self._learn_correction(session_id, feedback)

    async def _reinforce(self, session_id: str, feedback: Feedback):
        """增强正确行为"""
        # 增加相关案例的权重
        pass

    async def _correct(self, session_id: str, feedback: Feedback):
        """纠正错误行为"""
        # 降低错误案例的权重
        # 可能需要补充新案例
        pass

    async def _learn_correction(self, session_id: str, feedback: Feedback):
        """学习修正内容"""
        if feedback.correct_root_cause:
            # 学习正确的根因识别
            self.update_count += 1

        if feedback.correct_solution:
            # 学习正确的解决方案
            self.update_count += 1

    def get_learning_stats(self) -> Dict[str, Any]:
        """获取学习统计"""
        return {
            "total_samples": len(self.samples),
            "update_count": self.update_count,
            "last_update": self.samples[-1].created_at if self.samples else None,
        }


class InMemoryFeedbackStorage:
    """内存反馈存储"""

    def __init__(self):
        self._storage: Dict[str, List[Feedback]] = {}

    async def save(self, session_id: str, feedback: Feedback):
        """保存反馈"""
        if session_id not in self._storage:
            self._storage[session_id] = []
        self._storage[session_id].append(feedback)

    async def get(self, session_id: str) -> List[Feedback]:
        """获取反馈"""
        return self._storage.get(session_id, [])

    async def get_recent(self, days: int = 30) -> List[Feedback]:
        """获取最近反馈"""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        all_feedback = []

        for feedbacks in self._storage.values():
            for f in feedbacks:
                if f.timestamp >= cutoff:
                    all_feedback.append(f)

        return all_feedback
