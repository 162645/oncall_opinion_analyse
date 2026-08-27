"""
v2 评估模块
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

__all__ = [
    "DiagnosisEvaluator",
    "DiagnosisMetrics",
    "EvaluationResult",
    "BenchmarkRunner",
    "MetricsCollector",
    "DiagnosisMetricsCollector",
    "get_metrics_collector",
]
