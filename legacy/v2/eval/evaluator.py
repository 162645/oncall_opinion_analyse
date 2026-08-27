"""
诊断评估模块
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum


class MetricType(Enum):
    """指标类型"""
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    LATENCY = "latency"
    MTTR = "mttr"


@dataclass
class DiagnosisMetrics:
    """诊断指标"""
    session_id: str
    root_cause_accuracy: float = 0.0
    solution_relevance: float = 0.0
    time_to_diagnosis_ms: int = 0
    knowledge_hit_rate: float = 0.0
    agent_count: int = 0
    retrieval_count: int = 0


@dataclass
class EvaluationResult:
    """评估结果"""
    session_id: str
    overall_score: float
    metrics: DiagnosisMetrics
    details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class DiagnosisEvaluator:
    """
    诊断评估器

    评估维度:
    1. 根因准确率: 预测根因与实际根因的匹配度
    2. 解决方案有效性: 推荐方案与实际方案的相似度
    3. 时间效率: 诊断时间 vs 基线时间
    4. 知识命中率: 是否命中相关历史案例
    """

    def __init__(self, baseline_mttr_minutes: float = 120):
        self.baseline_mttr_minutes = baseline_mttr_minutes
        self._history: List[EvaluationResult] = []

    def evaluate(
        self,
        diagnosis_result: Dict[str, Any],
        ground_truth: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """
        评估诊断结果

        Args:
            diagnosis_result: 诊断结果
            ground_truth: 真实结果（可选，用于准确率评估）

        Returns:
            评估结果
        """
        session_id = diagnosis_result.get("session_id", "")

        metrics = DiagnosisMetrics(
            session_id=session_id,
            time_to_diagnosis_ms=diagnosis_result.get("time_ms", 0),
            agent_count=diagnosis_result.get("agent_count", 0),
            retrieval_count=diagnosis_result.get("retrieval_count", 0),
        )

        # 如果有真实结果，计算准确率
        if ground_truth:
            metrics.root_cause_accuracy = self._compute_root_cause_accuracy(
                diagnosis_result.get("root_cause", {}),
                ground_truth.get("root_cause", {}),
            )

            metrics.solution_relevance = self._compute_solution_relevance(
                diagnosis_result.get("recommendations", []),
                ground_truth.get("solutions", []),
            )

            metrics.knowledge_hit_rate = self._compute_knowledge_hit_rate(
                diagnosis_result.get("knowledge_results", []),
                ground_truth.get("related_cases", []),
            )

        # 计算综合得分
        overall_score = self._compute_overall_score(metrics)

        # 生成改进建议
        recommendations = self._generate_recommendations(metrics, diagnosis_result)

        result = EvaluationResult(
            session_id=session_id,
            overall_score=overall_score,
            metrics=metrics,
            details={
                "diagnosis_time_efficiency": self._compute_time_efficiency(
                    metrics.time_to_diagnosis_ms
                ),
            },
            recommendations=recommendations,
        )

        self._history.append(result)

        return result

    def _compute_root_cause_accuracy(
        self,
        predicted: Dict[str, Any],
        actual: Dict[str, Any],
    ) -> float:
        """计算根因准确率"""
        if not predicted or not actual:
            return 0.0

        # 类别匹配
        category_match = predicted.get("category") == actual.get("category")

        # 子类别匹配
        subcategory_match = predicted.get("subcategory") == actual.get("subcategory")

        # 描述相似度（简单关键词匹配）
        pred_desc = predicted.get("description", "").lower()
        actual_desc = actual.get("description", "").lower()

        pred_words = set(pred_desc.split())
        actual_words = set(actual_desc.split())

        word_overlap = len(pred_words & actual_words) / max(len(actual_words), 1)

        # 综合分数
        score = (
            0.4 * (1.0 if category_match else 0.0) +
            0.3 * (1.0 if subcategory_match else 0.0) +
            0.3 * word_overlap
        )

        return round(score, 2)

    def _compute_solution_relevance(
        self,
        predicted_solutions: List[str],
        actual_solutions: List[str],
    ) -> float:
        """计算解决方案相关性"""
        if not predicted_solutions or not actual_solutions:
            return 0.0

        # 计算预测方案与实际方案的关键词重叠
        pred_words = set()
        for sol in predicted_solutions:
            pred_words.update(sol.lower().split())

        actual_words = set()
        for sol in actual_solutions:
            actual_words.update(sol.lower().split())

        if not actual_words:
            return 0.0

        overlap = len(pred_words & actual_words) / len(actual_words)

        return round(overlap, 2)

    def _compute_knowledge_hit_rate(
        self,
        knowledge_results: List[Dict],
        related_cases: List[str],
    ) -> float:
        """计算知识命中率"""
        if not related_cases:
            return 1.0  # 没有相关案例时，跳过此项

        if not knowledge_results:
            return 0.0

        # 检查检索结果中是否包含相关案例
        retrieved_ids = {
            r.get("doc_id", r.get("case_id", ""))
            for r in knowledge_results
        }

        hits = len(set(related_cases) & retrieved_ids)

        return round(hits / len(related_cases), 2)

    def _compute_time_efficiency(self, time_ms: int) -> float:
        """计算时间效率"""
        if time_ms == 0:
            return 1.0

        time_minutes = time_ms / 60000
        efficiency = self.baseline_mttr_minutes / time_minutes

        return round(min(efficiency, 2.0), 2)

    def _compute_overall_score(self, metrics: DiagnosisMetrics) -> float:
        """计算综合得分"""
        weights = {
            "root_cause": 0.4,
            "solution": 0.3,
            "time": 0.2,
            "knowledge": 0.1,
        }

        time_score = min(
            metrics.time_to_diagnosis_ms / (self.baseline_mttr_minutes * 60000),
            1.0
        )

        score = (
            weights["root_cause"] * metrics.root_cause_accuracy +
            weights["solution"] * metrics.solution_relevance +
            weights["time"] * (1 - time_score) +  # 时间越短越好
            weights["knowledge"] * metrics.knowledge_hit_rate
        )

        return round(score, 2)

    def _generate_recommendations(
        self,
        metrics: DiagnosisMetrics,
        diagnosis_result: Dict[str, Any],
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        if metrics.root_cause_accuracy < 0.7:
            recommendations.append(
                "根因准确率较低，建议增加更多历史案例到知识库"
            )

        if metrics.solution_relevance < 0.6:
            recommendations.append(
                "解决方案相关性较低，建议优化方案推荐逻辑"
            )

        if metrics.knowledge_hit_rate < 0.5:
            recommendations.append(
                "知识命中率较低，建议检查知识库覆盖范围"
            )

        if metrics.time_to_diagnosis_ms > 30000:  # 30秒
            recommendations.append(
                "诊断时间较长，建议优化 Agent 并行执行"
            )

        return recommendations

    def get_aggregate_metrics(self) -> Dict[str, Any]:
        """获取聚合指标"""
        if not self._history:
            return {"total_evaluations": 0}

        avg_accuracy = sum(
            r.metrics.root_cause_accuracy for r in self._history
        ) / len(self._history)

        avg_solution = sum(
            r.metrics.solution_relevance for r in self._history
        ) / len(self._history)

        avg_time = sum(
            r.metrics.time_to_diagnosis_ms for r in self._history
        ) / len(self._history)

        return {
            "total_evaluations": len(self._history),
            "average_root_cause_accuracy": round(avg_accuracy, 2),
            "average_solution_relevance": round(avg_solution, 2),
            "average_time_to_diagnosis_ms": round(avg_time, 0),
            "improvement_trend": self._compute_trend(),
        }

    def _compute_trend(self) -> str:
        """计算改进趋势"""
        if len(self._history) < 5:
            return "insufficient_data"

        # 比较最近 5 次和之前 5 次
        recent = self._history[-5:]
        previous = self._history[-10:-5] if len(self._history) >= 10 else []

        if not previous:
            return "no_baseline"

        recent_avg = sum(r.overall_score for r in recent) / len(recent)
        previous_avg = sum(r.overall_score for r in previous) / len(previous)

        if recent_avg > previous_avg + 0.05:
            return "improving"
        elif recent_avg < previous_avg - 0.05:
            return "declining"
        else:
            return "stable"


class BenchmarkRunner:
    """基准测试运行器"""

    def __init__(self, evaluator: DiagnosisEvaluator):
        self.evaluator = evaluator

    async def run_benchmark(
        self,
        test_cases: List[Dict[str, Any]],
        diagnosis_func: Callable,
    ) -> Dict[str, Any]:
        """
        运行基准测试

        Args:
            test_cases: 测试用例列表
            diagnosis_func: 诊断函数

        Returns:
            基准测试结果
        """
        results = []

        for case in test_cases:
            # 执行诊断
            diagnosis = await diagnosis_func(case)

            # 评估
            evaluation = self.evaluator.evaluate(
                diagnosis,
                case.get("ground_truth"),
            )

            results.append({
                "case_id": case.get("id"),
                "diagnosis": diagnosis,
                "evaluation": evaluation,
            })

        # 汇总统计
        aggregate = self.evaluator.get_aggregate_metrics()

        return {
            "total_cases": len(test_cases),
            "results": results,
            "aggregate": aggregate,
        }
