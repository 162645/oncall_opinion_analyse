"""
RAGAS RAG 评估器
量化评估 RAG 系统效果
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class RAGEvaluationResult:
    """RAG 评估结果"""
    query: str
    response: str
    contexts: List[str]
    ground_truth: Optional[str] = None

    # 评估分数 (0-1)
    faithfulness: float = 0.0
    answer_relevancy: float = 0.0
    context_recall: float = 0.0
    context_precision: float = 0.0

    # 综合分数
    overall_score: float = 0.0

    # 元数据
    latency_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class RAGEvaluator:
    """
    RAG 评估器

    基于 RAGAS 框架的评估指标:
    1. Faithfulness (忠实度) - 回答是否基于检索内容
    2. Answer Relevancy (答案相关性) - 回答是否回答了问题
    3. Context Recall (上下文召回) - 检索内容是否完整
    4. Context Precision (上下文精确度) - 检索内容是否精确

    注意: 完整 RAGAS 功能需要安装 ragas 包
    """

    def __init__(self, llm_gateway: Any = None):
        self.llm_gateway = llm_gateway
        self._ragas_available = self._check_ragas()

    def _check_ragas(self) -> bool:
        """检查 RAGAS 是否可用"""
        try:
            import ragas
            return True
        except ImportError:
            logger.debug(
                "Ragas not installed. "
                "Install with: pip install ragas"
            )
            return False

    async def evaluate(
        self,
        query: str,
        response: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
    ) -> RAGEvaluationResult:
        """
        评估单个查询

        Args:
            query: 用户查询
            response: 系统响应
            contexts: 检索的上下文
            ground_truth: 标准答案（可选）

        Returns:
            RAGEvaluationResult
        """
        start_time = time.time()

        result = RAGEvaluationResult(
            query=query,
            response=response,
            contexts=contexts,
            ground_truth=ground_truth,
        )

        if self._ragas_available:
            # 使用 RAGAS 进行评估
            try:
                scores = await self._evaluate_with_ragas(
                    query, response, contexts, ground_truth
                )
                result.faithfulness = scores.get("faithfulness", 0.0)
                result.answer_relevancy = scores.get("answer_relevancy", 0.0)
                result.context_recall = scores.get("context_recall", 0.0)
                result.context_precision = scores.get("context_precision", 0.0)

            except Exception as e:
                logger.error(f"RAGAS evaluation failed: {e}")
                # 使用简化评估
                result.faithfulness = self._simple_faithfulness(response, contexts)
                result.answer_relevancy = self._simple_relevancy(query, response)

        else:
            # 使用简化评估
            result.faithfulness = self._simple_faithfulness(response, contexts)
            result.answer_relevancy = self._simple_relevancy(query, response)

        # 计算综合分数
        result.overall_score = self._calculate_overall(result)
        result.latency_ms = int((time.time() - start_time) * 1000)

        return result

    async def evaluate_batch(
        self,
        samples: List[Dict[str, Any]],
    ) -> List[RAGEvaluationResult]:
        """
        批量评估

        Args:
            samples: 样本列表

        Returns:
            List[RAGEvaluationResult]
        """
        results = []

        for sample in samples:
            result = await self.evaluate(
                query=sample.get("query", ""),
                response=sample.get("response", ""),
                contexts=sample.get("contexts", []),
                ground_truth=sample.get("ground_truth"),
            )
            results.append(result)

        return results

    async def _evaluate_with_ragas(
        self,
        query: str,
        response: str,
        contexts: List[str],
        ground_truth: Optional[str],
    ) -> Dict[str, float]:
        """使用 RAGAS 进行评估"""
        try:
            from ragas.metrics import (
                faithfulness,
                answer_relevancy,
                context_recall,
                context_precision,
            )
            from ragas.dataset_schema import SingleTurnSample

            sample = SingleTurnSample(
                user_input=query,
                response=response,
                retrieved_contexts=contexts,
                reference=ground_truth,
            )

            scores = {}

            # 计算各项指标
            try:
                scores["faithfulness"] = await faithfulness.single_turn_ascore(sample)
            except Exception:
                scores["faithfulness"] = 0.0

            try:
                scores["answer_relevancy"] = await answer_relevancy.single_turn_ascore(sample)
            except Exception:
                scores["answer_relevancy"] = 0.0

            if ground_truth:
                try:
                    scores["context_recall"] = await context_recall.single_turn_ascore(sample)
                except Exception:
                    scores["context_recall"] = 0.0

                try:
                    scores["context_precision"] = await context_precision.single_turn_ascore(sample)
                except Exception:
                    scores["context_precision"] = 0.0

            return scores

        except Exception as e:
            logger.error(f"RAGAS evaluation error: {e}")
            return {}

    def _simple_faithfulness(self, response: str, contexts: List[str]) -> float:
        """简化的忠实度评估"""
        if not contexts:
            return 0.0

        context_text = " ".join(contexts).lower()
        response_lower = response.lower()

        words = response_lower.split()
        matches = sum(1 for w in words if w in context_text)

        return min(matches / max(len(words), 1), 1.0)

    def _simple_relevancy(self, query: str, response: str) -> float:
        """简化的相关性评估"""
        query_lower = query.lower()
        response_lower = response.lower()

        query_words = [w for w in query_lower.split() if len(w) > 2]
        if not query_words:
            return 0.5

        matches = sum(1 for w in query_words if w in response_lower)
        return min(matches / len(query_words), 1.0)

    def _calculate_overall(self, result: RAGEvaluationResult) -> float:
        """计算综合分数"""
        scores = [
            result.faithfulness,
            result.answer_relevancy,
        ]

        if result.context_recall > 0:
            scores.append(result.context_recall)
        if result.context_precision > 0:
            scores.append(result.context_precision)

        return sum(scores) / len(scores) if scores else 0.0


# 全局评估器实例
_rag_evaluator: Optional[RAGEvaluator] = None


def get_rag_evaluator() -> RAGEvaluator:
    """获取 RAG 评估器实例"""
    global _rag_evaluator
    if _rag_evaluator is None:
        _rag_evaluator = RAGEvaluator()
    return _rag_evaluator
