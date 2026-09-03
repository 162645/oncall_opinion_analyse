"""
可视化意图解析器
从自然语言描述中提取可视化参数
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import re


class ChartType(Enum):
    """图表类型"""
    LINE = "line"           # 折线图 - 趋势
    BAR = "bar"             # 柱状图 - 对比
    PIE = "pie"             # 饼图 - 占比
    SCATTER = "scatter"     # 散点图 - 分布
    HEATMAP = "heatmap"     # 热力图 - 密度
    GAUGE = "gauge"         # 仪表盘 - 单值
    TABLE = "table"         # 表格 - 详情
    AREA = "area"           # 面积图 - 趋势


@dataclass
class VisualizationIntent:
    """可视化意图"""
    chart_type: ChartType
    metric: str                    # 指标: latency, traffic, error_rate
    time_range: str                # 时间范围: 1h, 24h, 7d, 30d
    group_by: Optional[str] = None  # 分组: region, service
    filters: Dict[str, str] = field(default_factory=dict)
    title: Optional[str] = None
    raw_query: str = ""
    aggregation: str = "avg"       # 聚合方式: avg, sum, max, min, p99


class VisualizationIntentParser:
    """
    可视化意图解析器

    从自然语言中提取:
    - 图表类型
    - 指标
    - 时间范围
    - 过滤条件
    """

    def __init__(self):
        # 图表类型关键词
        self.chart_keywords: Dict[ChartType, List[str]] = {
            ChartType.LINE: ["趋势", "变化", "走势", "折线", "曲线", "trend", "line", "随时间"],
            ChartType.BAR: ["对比", "比较", "柱状", "条形", "compare", "bar", "排名"],
            ChartType.PIE: ["占比", "比例", "分布", "饼图", "pie", "percentage", "百分比"],
            ChartType.SCATTER: ["散点", "scatter", "分布情况"],
            ChartType.HEATMAP: ["热力", "密度", "heatmap", "热点"],
            ChartType.GAUGE: ["仪表", "进度", "当前值", "gauge", "实时"],
            ChartType.TABLE: ["表格", "列表", "详情", "明细", "table"],
            ChartType.AREA: ["面积", "堆叠", "area"],
        }

        # 指标关键词
        self.metric_keywords: Dict[str, List[str]] = {
            "latency": ["延迟", "latency", "rtt", "响应时间", "耗时", "延迟时间"],
            "traffic": ["流量", "吞吐", "qps", "traffic", "throughput", "请求量", "访问量"],
            "error_rate": ["错误率", "失败率", "error", "failure", "报错率"],
            "packet_loss": ["丢包", "loss", "丢包率"],
            "cpu": ["cpu", "处理器", "cpu使用率", "cpu利用率"],
            "memory": ["内存", "memory", "内存使用率", "内存利用率"],
            "connection": ["连接", "connection", "连接数"],
            "latency_p99": ["p99", "p95", "p99延迟", "百分位"],
        }

        # 时间范围关键词
        self.time_keywords: Dict[str, List[str]] = {
            "15m": ["最近15分钟", "15分钟", "15min", "past 15 min"],
            "1h": ["最近1小时", "1小时", "一小时", "past 1 hour", "last hour"],
            "6h": ["最近6小时", "6小时", "past 6 hours"],
            "24h": ["最近24小时", "24小时", "1天", "今天", "past 24 hours", "today", "一天"],
            "7d": ["最近7天", "7天", "一周", "本周", "past 7 days", "this week"],
            "30d": ["最近30天", "30天", "一个月", "本月", "past 30 days"],
        }

        # 聚合方式关键词
        self.aggregation_keywords: Dict[str, List[str]] = {
            "avg": ["平均", "avg", "average"],
            "max": ["最大", "max", "maximum", "峰值"],
            "min": ["最小", "min", "minimum"],
            "sum": ["总和", "sum", "total", "累计"],
            "p99": ["p99", "p95", "百分位"],
        }

    def parse(self, query: str) -> VisualizationIntent:
        """
        解析自然语言查询

        Args:
            query: 自然语言查询，如 "画一个最近24小时的延迟趋势图"

        Returns:
            VisualizationIntent: 解析出的可视化意图
        """
        query_lower = query.lower()

        # 1. 识别图表类型
        chart_type = self._detect_chart_type(query_lower)

        # 2. 识别指标
        metric = self._detect_metric(query_lower)

        # 3. 识别时间范围
        time_range = self._detect_time_range(query_lower)

        # 4. 提取过滤条件
        filters = self._extract_filters(query)

        # 5. 识别分组
        group_by = self._detect_group_by(query_lower)

        # 6. 识别聚合方式
        aggregation = self._detect_aggregation(query_lower)

        # 7. 生成标题
        title = self._generate_title(chart_type, metric, time_range, filters)

        return VisualizationIntent(
            chart_type=chart_type,
            metric=metric,
            time_range=time_range,
            group_by=group_by,
            filters=filters,
            title=title,
            raw_query=query,
            aggregation=aggregation,
        )

    def _detect_chart_type(self, query: str) -> ChartType:
        """检测图表类型"""
        scores: Dict[ChartType, int] = {ct: 0 for ct in ChartType}

        for chart_type, keywords in self.chart_keywords.items():
            for kw in keywords:
                if kw in query:
                    scores[chart_type] += 1

        # 找最高分
        max_score = max(scores.values())
        if max_score > 0:
            for chart_type, score in scores.items():
                if score == max_score:
                    return chart_type

        # 默认规则
        if any(kw in query for kw in ["趋势", "变化", "走势"]):
            return ChartType.LINE
        if any(kw in query for kw in ["对比", "比较"]):
            return ChartType.BAR

        return ChartType.LINE

    def _detect_metric(self, query: str) -> str:
        """检测指标"""
        for metric, keywords in self.metric_keywords.items():
            for kw in keywords:
                if kw in query:
                    return metric
        return "latency"

    def _detect_time_range(self, query: str) -> str:
        """检测时间范围"""
        for time_range, keywords in self.time_keywords.items():
            for kw in keywords:
                if kw in query:
                    return time_range
        return "1h"

    def _extract_filters(self, query: str) -> Dict[str, str]:
        """提取过滤条件"""
        filters: Dict[str, str] = {}

        # 区域
        region_patterns = [
            (r"(新加坡|Singapore)[-_]?(Central)?", "Singapore"),
            (r"(美国|US)[-_]?(East)?", "US-East"),
            (r"(美国|US)[-_]?West", "US-West"),
            (r"(北京|Beijing)", "Beijing"),
            (r"(上海|Shanghai)", "Shanghai"),
        ]
        for pattern, region_name in region_patterns:
            if re.search(pattern, query, re.I):
                filters["region"] = region_name
                break

        # PSM
        psm_match = re.search(r"psm[：:\s]*([a-zA-Z0-9_.-]+)", query, re.I)
        if psm_match:
            filters["psm"] = psm_match.group(1)

        # 服务名
        service_match = re.search(r"服务[：:\s]*([a-zA-Z0-9_-]+)", query)
        if service_match:
            filters["service"] = service_match.group(1)

        return filters

    def _detect_group_by(self, query: str) -> Optional[str]:
        """检测分组"""
        patterns = [
            (r"按区域|by region|各区域", "region"),
            (r"按服务|by service|各服务", "service"),
            (r"按时间|by time|各时间", "time"),
            (r"按PSM|各PSM", "psm"),
        ]
        for pattern, group in patterns:
            if re.search(pattern, query, re.I):
                return group
        return None

    def _detect_aggregation(self, query: str) -> str:
        """检测聚合方式"""
        for agg, keywords in self.aggregation_keywords.items():
            for kw in keywords:
                if kw in query:
                    return agg
        return "avg"

    def _generate_title(
        self,
        chart_type: ChartType,
        metric: str,
        time_range: str,
        filters: Dict[str, str],
    ) -> str:
        """生成标题"""
        metric_names = {
            "latency": "网络延迟",
            "traffic": "网络流量",
            "error_rate": "错误率",
            "packet_loss": "丢包率",
            "cpu": "CPU使用率",
            "memory": "内存使用率",
            "connection": "连接数",
            "latency_p99": "P99延迟",
        }

        time_names = {
            "15m": "最近15分钟",
            "1h": "最近1小时",
            "6h": "最近6小时",
            "24h": "最近24小时",
            "7d": "最近7天",
            "30d": "最近30天",
        }

        chart_names = {
            ChartType.LINE: "趋势图",
            ChartType.BAR: "对比图",
            ChartType.PIE: "分布图",
            ChartType.AREA: "面积图",
            ChartType.TABLE: "数据表",
        }

        parts = []

        # 区域过滤
        if "region" in filters:
            parts.append(filters["region"])

        # 指标
        parts.append(metric_names.get(metric, metric))

        # 时间范围
        parts.append(time_names.get(time_range, time_range))

        # 图表类型
        parts.append(chart_names.get(chart_type, ""))

        return " ".join(filter(None, parts))

    def get_supported_queries(self) -> List[str]:
        """获取支持的查询示例"""
        return [
            "画一个最近24小时的延迟趋势图",
            "帮我生成一个各区域流量对比的柱状图",
            "显示错误率的占比饼图",
            "最近7天的CPU使用率变化",
            "新加坡区域P99延迟趋势",
            "各服务的请求量排名",
            "最近1小时的内存使用率",
        ]
