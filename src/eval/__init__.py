"""
评估模块
支持诊断评估和 RAGAS 评估
"""

from .evaluator import (
    DiagnosisEvaluator,
    DiagnosisMetrics,
    EvaluationResult,
    BenchmarkRunner,
)
from .metrics import (
    MetricsCollector,
    DiagnosisMetricsCollector,
    get_metrics_collector,
)

# RAGAS 评估组件
from .ragas_evaluator import RAGEvaluator, RAGEvaluationResult, get_rag_evaluator
from .report import EvaluationReport, generate_report, generate_markdown_report
from .network_harness_eval import DEFAULT_CASES, NetworkEvalCase, compare_strategies, evaluate_cases, score_case
from .replay_runtime import ReplayRuntime

__all__ = [
    # 诊断评估
    "DiagnosisEvaluator",
    "DiagnosisMetrics",
    "EvaluationResult",
    "BenchmarkRunner",
    # 指标收集
    "MetricsCollector",
    "DiagnosisMetricsCollector",
    "get_metrics_collector",
    # RAGAS 评估
    "RAGEvaluator",
    "RAGEvaluationResult",
    "get_rag_evaluator",
    # 报告生成
    "EvaluationReport",
    "generate_report",
    "generate_markdown_report",
    "NetworkEvalCase",
    "DEFAULT_CASES",
    "score_case",
    "evaluate_cases",
    "compare_strategies",
    "ReplayRuntime",
]
from .harness_metrics import AgentEvaluationRecord, HarnessEvaluator

__all__ = ["AgentEvaluationRecord", "HarnessEvaluator"]
