"""
统计分析工具
提供常用的统计计算函数
"""

import math
from typing import List, Dict, Any, Optional, Callable
from functools import lru_cache


def calculate_percentile(values: List[float], percentile: float) -> float:
    """
    计算百分位数

    Args:
        values: 数值列表
        percentile: 百分位 (0-100)

    Returns:
        百分位数值
    """
    if not values:
        return 0.0

    sorted_values = sorted(values)
    n = len(sorted_values)

    # 计算索引
    index = (percentile / 100) * (n - 1)
    lower = int(math.floor(index))
    upper = int(math.ceil(index))

    if lower == upper:
        return sorted_values[lower]

    # 线性插值
    weight = index - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def calculate_statistics(
    values: List[float],
    percentiles: Optional[List[float]] = None
) -> Dict[str, float]:
    """
    计算统计指标

    Args:
        values: 数值列表
        percentiles: 要计算的百分位列表

    Returns:
        统计指标字典
    """
    if not values:
        return {
            'count': 0,
            'mean': 0,
            'median': 0,
            'std': 0,
            'min': 0,
            'max': 0,
        }

    n = len(values)

    # 基本统计
    total = sum(values)
    mean = total / n

    # 中位数
    sorted_values = sorted(values)
    if n % 2 == 0:
        median = (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
    else:
        median = sorted_values[n // 2]

    # 标准差
    variance = sum((x - mean) ** 2 for x in values) / n
    std = math.sqrt(variance)

    result = {
        'count': n,
        'mean': mean,
        'median': median,
        'std': std,
        'min': sorted_values[0],
        'max': sorted_values[-1],
    }

    # 百分位数
    if percentiles:
        for p in percentiles:
            result[f'p{int(p)}'] = calculate_percentile(values, p)

    return result


class StatisticsCalculator:
    """统计计算器类"""

    def __init__(self):
        self._values: List[float] = []

    def add_value(self, value: float) -> None:
        """添加值"""
        self._values.append(value)

    def add_values(self, values: List[float]) -> None:
        """添加多个值"""
        self._values.extend(values)

    def clear(self) -> None:
        """清空"""
        self._values = []

    def calculate(self, percentiles: Optional[List[float]] = None) -> Dict[str, float]:
        """计算统计指标"""
        result = calculate_statistics(self._values, percentiles or [50, 90, 95, 99])
        result['count'] = len(self._values)
        return result

    def get_histogram(
        self,
        bucket_size: float = 10,
        max_value: Optional[float] = None
    ) -> Dict[str, int]:
        """
        计算直方图

        Args:
            bucket_size: 桶大小
            max_value: 最大值（超过的归入最后一个桶）

        Returns:
            直方图字典
        """
        if not self._values:
            return {}

        if max_value is None:
            max_value = max(self._values)

        histogram = {}
        for value in self._values:
            if value > max_value:
                bucket = f">{max_value}"
            else:
                bucket_start = int(value // bucket_size) * bucket_size
                bucket = f"{bucket_start}-{bucket_start + bucket_size}"

            histogram[bucket] = histogram.get(bucket, 0) + 1

        return dict(sorted(histogram.items(), key=lambda x: float(x[0].split('-')[0].replace('>', ''))))


def compare_periods(
    period1_values: List[float],
    period2_values: List[float]
) -> Dict[str, Any]:
    """
    比较两个周期的数据

    Args:
        period1_values: 第一周期数据
        period2_values: 第二周期数据

    Returns:
        比较结果
    """
    stats1 = calculate_statistics(period1_values)
    stats2 = calculate_statistics(period2_values)

    return {
        'period1': stats1,
        'period2': stats2,
        'diff': {
            'mean': stats2['mean'] - stats1['mean'],
            'median': stats2['median'] - stats1['median'],
            'mean_percent': ((stats2['mean'] - stats1['mean']) / stats1['mean'] * 100) if stats1['mean'] else 0,
            'median_percent': ((stats2['median'] - stats1['median']) / stats1['median'] * 100) if stats1['median'] else 0,
        }
    }


def detect_anomalies(
    values: List[float],
    threshold: float = 2.0
) -> List[Dict[str, Any]]:
    """
    检测异常值

    使用 Z-score 方法

    Args:
        values: 数值列表
        threshold: Z-score 阈值

    Returns:
        异常值列表
    """
    if len(values) < 3:
        return []

    stats = calculate_statistics(values)
    mean = stats['mean']
    std = stats['std']

    if std == 0:
        return []

    anomalies = []
    for i, value in enumerate(values):
        z_score = abs(value - mean) / std
        if z_score > threshold:
            anomalies.append({
                'index': i,
                'value': value,
                'z_score': z_score,
                'type': 'high' if value > mean else 'low',
            })

    return anomalies


def calculate_correlation(
    values1: List[float],
    values2: List[float]
) -> float:
    """
    计算两组数据的相关系数

    Args:
        values1: 第一组数据
        values2: 第二组数据

    Returns:
        相关系数 (-1 到 1)
    """
    if len(values1) != len(values2) or len(values1) < 2:
        return 0.0

    n = len(values1)
    mean1 = sum(values1) / n
    mean2 = sum(values2) / n

    numerator = sum((values1[i] - mean1) * (values2[i] - mean2) for i in range(n))

    denominator1 = math.sqrt(sum((x - mean1) ** 2 for x in values1))
    denominator2 = math.sqrt(sum((x - mean2) ** 2 for x in values2))

    if denominator1 == 0 or denominator2 == 0:
        return 0.0

    return numerator / (denominator1 * denominator2)
