"""
高级数据查询器
支持多数据源、复杂查询、数据关联
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import random
import asyncio

from .advanced_service import (
    MetricSpec,
    DataSource,
    AggregationType,
    DataSeries,
)


class AdvancedDataFetcher:
    """
    高级数据查询器

    支持功能:
    - 多数据源查询（Prometheus, ClickHouse, MySQL, API）
    - 数据关联和合并
    - 时间对齐
    - 数据预处理
    """

    def __init__(
        self,
        prometheus_url: str = "http://localhost:9090",
        clickhouse_url: str = None,
        mysql_url: str = None,
    ):
        self.prometheus_url = prometheus_url
        self.clickhouse_url = clickhouse_url
        self.mysql_url = mysql_url

    async def fetch(
        self,
        intent: "ComplexVisualizationIntent",
    ) -> List[DataSeries]:
        """
        根据意图获取数据

        Args:
            intent: 复杂可视化意图

        Returns:
            数据系列列表
        """
        data_series = []

        # 并行获取多指标数据
        tasks = []
        for metric in intent.metrics:
            task = self._fetch_metric(metric, intent.time_range, intent.filters, intent.group_by)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # 使用模拟数据
                metric = intent.metrics[i]
                data_series.append(self._generate_mock_data(metric, intent.time_range, intent.group_by))
            else:
                data_series.append(result)

        return data_series

    async def _fetch_metric(
        self,
        metric: MetricSpec,
        time_range: str,
        filters: Dict[str, str],
        group_by: List[str],
    ) -> DataSeries:
        """获取单个指标数据"""
        if metric.data_source == DataSource.PROMETHEUS:
            return await self._fetch_from_prometheus(metric, time_range, filters, group_by)
        elif metric.data_source == DataSource.CLICKHOUSE:
            return await self._fetch_from_clickhouse(metric, time_range, filters, group_by)
        elif metric.data_source == DataSource.MYSQL:
            return await self._fetch_from_mysql(metric, time_range, filters, group_by)
        else:
            return self._generate_mock_data(metric, time_range, group_by)

    async def _fetch_from_prometheus(
        self,
        metric: MetricSpec,
        time_range: str,
        filters: Dict[str, str],
        group_by: List[str],
    ) -> DataSeries:
        """从 Prometheus 获取数据"""
        # TODO: 实现真实的 Prometheus API 调用
        # 当前返回模拟数据
        return self._generate_mock_data(metric, time_range, group_by)

    async def _fetch_from_clickhouse(
        self,
        metric: MetricSpec,
        time_range: str,
        filters: Dict[str, str],
        group_by: List[str],
    ) -> DataSeries:
        """从 ClickHouse 获取数据"""
        # TODO: 实现真实的 ClickHouse 查询
        return self._generate_mock_data(metric, time_range, group_by)

    async def _fetch_from_mysql(
        self,
        metric: MetricSpec,
        time_range: str,
        filters: Dict[str, str],
        group_by: List[str],
    ) -> DataSeries:
        """从 MySQL 获取数据"""
        # TODO: 实现真实的 MySQL 查询
        return self._generate_mock_data(metric, time_range, group_by)

    def _generate_mock_data(
        self,
        metric: MetricSpec,
        time_range: str,
        group_by: List[str],
    ) -> DataSeries:
        """生成模拟数据"""
        # 计算时间点和数据点数量
        time_deltas = {
            "15m": (timedelta(minutes=15), 60),
            "1h": (timedelta(hours=1), 60),
            "6h": (timedelta(hours=6), 72),
            "24h": (timedelta(hours=24), 288),
            "7d": (timedelta(days=7), 168),
            "30d": (timedelta(days=30), 360),
        }

        delta, num_points = time_deltas.get(time_range, (timedelta(hours=1), 60))

        # 根据指标类型设置基准值和范围
        base_values = {
            "latency": (50.0, 0.3),
            "traffic": (1000.0, 0.2),
            "error_rate": (0.01, 0.5),
            "packet_loss": (0.001, 0.5),
            "cpu_usage": (30.0, 0.3),
            "memory_usage": (1024.0, 0.2),
            "connections": (500.0, 0.15),
            "order_count": (10000.0, 0.25),
            "transaction_amount": (50000.0, 0.2),
            "user_count": (5000.0, 0.1),
            "latency_p99": (100.0, 0.4),
            "latency_p95": (80.0, 0.35),
            "latency_p90": (70.0, 0.3),
            "latency_p50": (50.0, 0.2),
            "throughput": (500.0, 0.15),
        }

        base, variance = base_values.get(metric.name, (100.0, 0.3))

        # 生成数据点
        values = []
        labels = []
        now = datetime.now()

        # 根据分组生成不同的数据模式
        if group_by:
            # 分组数据
            group_names = {
                "region": ["Singapore", "US-East", "US-West", "Beijing", "Shanghai"],
                "service": ["api-gateway", "user-service", "order-service", "payment-service"],
                "psm": ["shop.order", "shop.payment", "shop.user", "shop.product"],
                "datacenter": ["DC1", "DC2", "DC3"],
                "cluster": ["cluster-a", "cluster-b", "cluster-c"],
            }

            groups = group_names.get(group_by[0], ["Group1", "Group2", "Group3"])

            for group in groups:
                group_base = base * random.uniform(0.8, 1.2)

                for i in range(num_points // len(groups)):
                    timestamp = now - delta + (delta * i / num_points)
                    value = group_base * (1 + random.uniform(-variance, variance))

                    values.append({
                        "timestamp": timestamp.isoformat(),
                        "value": round(max(0, value), 4),
                        "group": group,
                    })
                    labels.append(group)

        else:
            # 单一趋势数据
            for i in range(num_points):
                timestamp = now - delta + (delta * i / num_points)

                # 添加一些趋势和周期性
                trend = 1 + 0.1 * (i / num_points)  # 轻微上升趋势
                seasonal = 0.1 * random.sin(i / 10) if hasattr(random, 'sin') else 0  # 周期性

                value = base * trend * (1 + random.uniform(-variance, variance) + seasonal)

                values.append({
                    "timestamp": timestamp.isoformat(),
                    "value": round(max(0, value), 4),
                })

        return DataSeries(
            name=metric.alias or metric.name,
            values=values,
            metric=metric.name,
            labels=labels,
        )

    def align_time_series(
        self,
        series_list: List[DataSeries],
        method: str = "interpolate",
    ) -> List[DataSeries]:
        """
        对齐多个时间序列

        Args:
            series_list: 数据系列列表
            method: 对齐方法 (interpolate, nearest, pad)

        Returns:
            对齐后的数据系列
        """
        if not series_list:
            return series_list

        # 找到所有时间戳的并集
        all_timestamps = set()
        for series in series_list:
            for v in series.values:
                all_timestamps.add(v.get("timestamp"))

        sorted_timestamps = sorted(all_timestamps)

        # 对每个序列进行对齐
        aligned_series = []
        for series in series_list:
            # 创建时间戳到值的映射
            value_map = {v.get("timestamp"): v.get("value") for v in series.values}

            new_values = []
            for ts in sorted_timestamps:
                if ts in value_map:
                    new_values.append({"timestamp": ts, "value": value_map[ts]})
                else:
                    # 插值或填充
                    new_values.append({"timestamp": ts, "value": None})  # TODO: 实现插值

            aligned_series.append(DataSeries(
                name=series.name,
                values=new_values,
                metric=series.metric,
                labels=series.labels,
            ))

        return aligned_series
