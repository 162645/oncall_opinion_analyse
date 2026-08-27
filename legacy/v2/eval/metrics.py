"""
指标收集模块
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json


@dataclass
class MetricPoint:
    """指标数据点"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """
    指标收集器

    收集并聚合各类指标
    """

    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        self._metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}

    def counter(self, name: str, value: float = 1, tags: Optional[Dict[str, str]] = None):
        """计数器"""
        self._counters[name] += value
        self._record(name, value, tags or {})

    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """仪表盘"""
        self._gauges[name] = value
        self._record(name, value, tags or {})

    def histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """直方图"""
        self._record(name, value, tags or {})

    def timing(self, name: str, value_ms: float, tags: Optional[Dict[str, str]] = None):
        """计时"""
        self._record(f"{name}_ms", value_ms, tags or {})

    def _record(self, name: str, value: float, tags: Dict[str, str]):
        """记录指标"""
        point = MetricPoint(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags,
        )
        self._metrics[name].append(point)

        # 清理过期数据
        self._cleanup(name)

    def _cleanup(self, name: str):
        """清理过期数据"""
        cutoff = datetime.now() - timedelta(hours=self.retention_hours)
        self._metrics[name] = [
            p for p in self._metrics[name]
            if p.timestamp >= cutoff
        ]

    def get_counter(self, name: str) -> float:
        """获取计数器值"""
        return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> float:
        """获取仪表盘值"""
        return self._gauges.get(name, 0)

    def get_stats(self, name: str) -> Dict[str, float]:
        """获取统计信息"""
        points = self._metrics.get(name, [])

        if not points:
            return {}

        values = [p.value for p in points]

        return {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "latest": values[-1],
        }

    def get_percentile(self, name: str, p: float) -> float:
        """获取百分位数"""
        points = self._metrics.get(name, [])

        if not points:
            return 0

        values = sorted([p.value for p in points])
        idx = int(len(values) * p / 100)

        return values[min(idx, len(values) - 1)]

    def export(self) -> Dict[str, Any]:
        """导出所有指标"""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "stats": {
                name: self.get_stats(name)
                for name in self._metrics
            },
            "exported_at": datetime.now().isoformat(),
        }

    def export_prometheus(self) -> str:
        """导出 Prometheus 格式"""
        lines = []

        # Counters
        for name, value in self._counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")

        # Gauges
        for name, value in self._gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")

        return "\n".join(lines)


class DiagnosisMetricsCollector:
    """诊断指标收集器"""

    def __init__(self):
        self.collector = MetricsCollector()

    def record_diagnosis_start(self, session_id: str):
        """记录诊断开始"""
        self.collector.counter("diagnosis_total", tags={"session_id": session_id})

    def record_diagnosis_end(
        self,
        session_id: str,
        success: bool,
        duration_ms: float,
    ):
        """记录诊断结束"""
        self.collector.timing("diagnosis_duration", duration_ms)
        self.collector.counter(
            "diagnosis_success" if success else "diagnosis_failure",
            tags={"session_id": session_id}
        )

    def record_agent_execution(
        self,
        agent_name: str,
        success: bool,
        duration_ms: float,
    ):
        """记录 Agent 执行"""
        self.collector.timing(
            f"agent_{agent_name}_duration",
            duration_ms,
            tags={"agent": agent_name}
        )
        self.collector.counter(
            f"agent_{agent_name}_{'success' if success else 'failure'}"
        )

    def record_retrieval(
        self,
        query: str,
        results_count: int,
        duration_ms: float,
    ):
        """记录检索"""
        self.collector.timing("retrieval_duration", duration_ms)
        self.collector.gauge("retrieval_results_count", results_count)
        self.collector.counter("retrieval_total")

    def record_feedback(
        self,
        session_id: str,
        rating: int,
    ):
        """记录用户反馈"""
        self.collector.counter("feedback_total")
        self.collector.gauge("feedback_rating", rating)

    def get_summary(self) -> Dict[str, Any]:
        """获取摘要"""
        return {
            "diagnosis": {
                "total": self.collector.get_counter("diagnosis_total"),
                "success_rate": self._compute_success_rate(),
                "avg_duration_ms": self.collector.get_stats("diagnosis_duration_ms").get("avg", 0),
                "p99_duration_ms": self.collector.get_percentile("diagnosis_duration_ms", 99),
            },
            "retrieval": {
                "total": self.collector.get_counter("retrieval_total"),
                "avg_results": self.collector.get_stats("retrieval_results_count").get("avg", 0),
            },
            "feedback": {
                "total": self.collector.get_counter("feedback_total"),
                "avg_rating": self.collector.get_stats("feedback_rating").get("avg", 0),
            },
        }

    def _compute_success_rate(self) -> float:
        """计算成功率"""
        success = self.collector.get_counter("diagnosis_success")
        failure = self.collector.get_counter("diagnosis_failure")
        total = success + failure

        return success / total if total > 0 else 0


# 全局指标收集器
_global_collector: Optional[DiagnosisMetricsCollector] = None


def get_metrics_collector() -> DiagnosisMetricsCollector:
    """获取全局指标收集器"""
    global _global_collector
    if _global_collector is None:
        _global_collector = DiagnosisMetricsCollector()
    return _global_collector
