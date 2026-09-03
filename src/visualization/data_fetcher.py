"""
数据查询器
根据可视化意图获取数据
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json


@dataclass
class DataPoint:
    """数据点"""
    timestamp: str
    value: float
    label: str = "value"
    metadata: Dict[str, Any] = None


class DataFetcher:
    """
    数据查询器

    根据可视化意图从数据源获取数据
    """

    def __init__(
        self,
        prometheus_url: str = "http://localhost:9090",
        clickhouse_url: str = None,
    ):
        self.prometheus_url = prometheus_url
        self.clickhouse_url = clickhouse_url

    def fetch(
        self,
        intent: "VisualizationIntent",
    ) -> Dict[str, Any]:
        """
        获取数据

        Args:
            intent: 可视化意图

        Returns:
            数据字典，包含 labels, values 等
        """
        # 根据指标选择数据源
        if intent.metric in ["latency", "traffic", "error_rate", "packet_loss"]:
            return self._fetch_metrics(intent)
        else:
            return self._fetch_from_db(intent)

    def _fetch_metrics(
        self,
        intent: "VisualizationIntent",
    ) -> Dict[str, Any]:
        """从监控系统获取指标数据"""
        # 构建 PromQL
        promql = self._build_promql(intent)

        # 计算时间范围
        end_time = datetime.now()
        start_time = self._parse_time_range(intent.time_range)

        # 模拟数据（实际应调用 Prometheus API）
        data_points = self._generate_mock_data(
            intent=intent,
            start_time=start_time,
            end_time=end_time,
        )

        return {
            "labels": [dp.label for dp in data_points],
            "values": [
                {
                    "timestamp": dp.timestamp,
                    "value": dp.value,
                    "label": dp.label,
                }
                for dp in data_points
            ],
            "metric": intent.metric,
            "time_range": intent.time_range,
            "query": promql,
        }

    def _build_promql(self, intent: "VisualizationIntent") -> str:
        """构建 PromQL 查询"""
        metric_map = {
            "latency": "http_request_duration_seconds",
            "traffic": "http_requests_total",
            "error_rate": "http_requests_total{status=~\"5..\"}",
            "packet_loss": "packet_loss_rate",
            "cpu": "process_cpu_usage",
            "memory": "process_resident_memory_bytes",
        }

        base_metric = metric_map.get(intent.metric, "up")

        # 添加聚合
        if intent.aggregation == "avg":
            promql = f"avg({base_metric})"
        elif intent.aggregation == "max":
            promql = f"max({base_metric})"
        elif intent.aggregation == "p99":
            promql = f"histogram_quantile(0.99, {base_metric})"
        else:
            promql = base_metric

        # 添加过滤条件
        if intent.filters:
            labels = []
            for key, value in intent.filters.items():
                labels.append(f'{key}="{value}"')
            promql = promql.replace("(", f"{{{','.join(labels)}}}(", 1)

        return promql

    def _generate_mock_data(
        self,
        intent: "VisualizationIntent",
        start_time: datetime,
        end_time: datetime,
    ) -> List[DataPoint]:
        """生成模拟数据（用于演示）"""
        import random

        data_points = []

        # 计算时间间隔
        duration = (end_time - start_time).total_seconds()
        if duration <= 3600:  # 1小时内
            step = 60  # 1分钟
        elif duration <= 86400:  # 1天内
            step = 300  # 5分钟
        else:
            step = 3600  # 1小时

        current_time = start_time
        base_value = self._get_base_value(intent.metric)

        while current_time <= end_time:
            # 添加一些随机波动
            value = base_value * (1 + random.uniform(-0.3, 0.3))
            value = max(0, value)  # 确保非负

            label = intent.group_by if intent.group_by else "value"
            if intent.filters.get("region"):
                label = intent.filters["region"]

            data_points.append(DataPoint(
                timestamp=current_time.isoformat(),
                value=round(value, 2),
                label=label,
            ))

            current_time += timedelta(seconds=step)

        return data_points

    def _get_base_value(self, metric: str) -> float:
        """获取指标基准值"""
        base_values = {
            "latency": 50.0,      # ms
            "traffic": 1000.0,    # QPS
            "error_rate": 0.01,   # 1%
            "packet_loss": 0.001, # 0.1%
            "cpu": 30.0,          # 30%
            "memory": 1024.0,     # MB
        }
        return base_values.get(metric, 1.0)

    def _fetch_from_db(
        self,
        intent: "VisualizationIntent",
    ) -> Dict[str, Any]:
        """从数据库获取数据"""
        # TODO: 实现 ClickHouse 查询
        return {
            "labels": [],
            "values": [],
            "metric": intent.metric,
            "time_range": intent.time_range,
        }

    def _parse_time_range(self, time_range: str) -> datetime:
        """解析时间范围"""
        ranges = {
            "15m": timedelta(minutes=15),
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
        }
        delta = ranges.get(time_range, timedelta(hours=1))
        return datetime.now() - delta

    def _calculate_step(self, time_range: str) -> str:
        """计算查询步长"""
        steps = {
            "15m": "15s",
            "1h": "1m",
            "6h": "5m",
            "24h": "5m",
            "7d": "1h",
            "30d": "6h",
        }
        return steps.get(time_range, "1m")
