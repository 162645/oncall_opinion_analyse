"""
高级可视化服务
支持复杂可视化指令的智能解析和执行
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import json
import re


class DataSource(Enum):
    """数据源类型"""
    PROMETHEUS = "prometheus"
    CLICKHOUSE = "clickhouse"
    MYSQL = "mysql"
    API = "api"
    MOCK = "mock"


class ChartType(Enum):
    """图表类型"""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    GAUGE = "gauge"
    TABLE = "table"
    AREA = "area"
    COMBO = "combo"  # 组合图
    MULTI_AXIS = "multi_axis"  # 多Y轴


class AggregationType(Enum):
    """聚合类型"""
    AVG = "avg"
    SUM = "sum"
    MAX = "max"
    MIN = "min"
    COUNT = "count"
    P50 = "p50"
    P90 = "p90"
    P95 = "p95"
    P99 = "p99"
    RATE = "rate"
    DERIVATIVE = "derivative"


@dataclass
class MetricSpec:
    """指标规格"""
    name: str                           # 指标名: latency, error_rate, etc.
    alias: Optional[str] = None         # 别名，用于图例
    aggregation: AggregationType = AggregationType.AVG
    data_source: DataSource = DataSource.PROMETHEUS
    query: Optional[str] = None         # 原始查询语句
    filters: Dict[str, str] = field(default_factory=dict)
    group_by: List[str] = field(default_factory=list)
    unit: Optional[str] = None          # 单位


@dataclass
class AxisSpec:
    """坐标轴规格"""
    label: str
    metric: MetricSpec
    position: str = "left"  # left, right
    min: Optional[float] = None
    max: Optional[float] = None
    unit: Optional[str] = None


@dataclass
class ComplexVisualizationIntent:
    """复杂可视化意图"""
    chart_type: ChartType
    title: str

    # 多指标支持
    metrics: List[MetricSpec] = field(default_factory=list)

    # 多轴支持
    axes: List[AxisSpec] = field(default_factory=list)

    # 时间范围
    time_range: str = "1h"
    start_time: Optional[str] = None
    end_time: Optional[str] = None

    # 分组和筛选
    group_by: List[str] = field(default_factory=list)
    filters: Dict[str, str] = field(default_factory=dict)
    having: Optional[str] = None

    # 图表配置
    show_legend: bool = True
    show_grid: bool = True
    stacked: bool = False

    # 原始查询
    raw_query: str = ""

    # 置信度
    confidence: float = 0.0

    # 执行计划
    execution_plan: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DataSeries:
    """数据系列"""
    name: str
    values: List[Dict[str, Any]]
    metric: str
    labels: List[str] = field(default_factory=list)


@dataclass
class ComplexVisualizationResult:
    """复杂可视化结果"""
    success: bool
    chart_base64: Optional[str] = None
    chart_html: Optional[str] = None
    title: str = ""
    description: str = ""
    intent: Optional[ComplexVisualizationIntent] = None
    data_series: List[DataSeries] = field(default_factory=list)
    error: Optional[str] = None


class AdvancedVisualizationParser:
    """
    高级可视化解析器

    支持复杂查询如:
    - "对比新加坡和美国区域的延迟和错误率趋势"
    - "显示上周故障期间CPU、内存、网络流量的相关性"
    - "按服务分组，显示P99延迟和错误率的散点图"
    - "最近30天每日订单量与延迟的关系，按是否高峰期分色"
    """

    # 指标映射
    METRIC_MAPPINGS = {
        # 性能指标
        "延迟": {"name": "latency", "unit": "ms", "source": "prometheus"},
        "响应时间": {"name": "latency", "unit": "ms", "source": "prometheus"},
        "rtt": {"name": "latency", "unit": "ms", "source": "prometheus"},
        "耗时": {"name": "latency", "unit": "ms", "source": "prometheus"},

        "流量": {"name": "traffic", "unit": "QPS", "source": "prometheus"},
        "qps": {"name": "traffic", "unit": "QPS", "source": "prometheus"},
        "请求量": {"name": "traffic", "unit": "QPS", "source": "prometheus"},
        "吞吐": {"name": "throughput", "unit": "MB/s", "source": "prometheus"},

        "错误率": {"name": "error_rate", "unit": "%", "source": "prometheus"},
        "失败率": {"name": "error_rate", "unit": "%", "source": "prometheus"},

        "丢包": {"name": "packet_loss", "unit": "%", "source": "prometheus"},
        "丢包率": {"name": "packet_loss", "unit": "%", "source": "prometheus"},

        # 系统指标
        "cpu": {"name": "cpu_usage", "unit": "%", "source": "prometheus"},
        "CPU使用率": {"name": "cpu_usage", "unit": "%", "source": "prometheus"},
        "处理器": {"name": "cpu_usage", "unit": "%", "source": "prometheus"},

        "内存": {"name": "memory_usage", "unit": "MB", "source": "prometheus"},
        "内存使用率": {"name": "memory_usage", "unit": "%", "source": "prometheus"},

        "连接数": {"name": "connections", "unit": "个", "source": "prometheus"},

        # 业务指标
        "订单量": {"name": "order_count", "unit": "个", "source": "clickhouse"},
        "订单数": {"name": "order_count", "unit": "个", "source": "clickhouse"},
        "交易额": {"name": "transaction_amount", "unit": "元", "source": "clickhouse"},
        "用户数": {"name": "user_count", "unit": "人", "source": "clickhouse"},

        # 百分位指标
        "p99": {"name": "latency_p99", "unit": "ms", "source": "prometheus", "agg": "p99"},
        "p95": {"name": "latency_p95", "unit": "ms", "source": "prometheus", "agg": "p95"},
        "p90": {"name": "latency_p90", "unit": "ms", "source": "prometheus", "agg": "p90"},
        "p50": {"name": "latency_p50", "unit": "ms", "source": "prometheus", "agg": "p50"},
    }

    # 图表类型映射
    CHART_TYPE_MAPPINGS = {
        "趋势": ChartType.LINE,
        "趋势图": ChartType.LINE,
        "变化": ChartType.LINE,
        "走势": ChartType.LINE,
        "折线": ChartType.LINE,

        "对比": ChartType.BAR,
        "比较": ChartType.BAR,
        "柱状": ChartType.BAR,
        "排名": ChartType.BAR,
        "条形": ChartType.BAR,

        "占比": ChartType.PIE,
        "分布": ChartType.PIE,
        "饼图": ChartType.PIE,
        "比例": ChartType.PIE,

        "散点": ChartType.SCATTER,
        "关系": ChartType.SCATTER,
        "相关性": ChartType.SCATTER,

        "热力": ChartType.HEATMAP,
        "热点": ChartType.HEATMAP,

        "面积": ChartType.AREA,
        "堆叠": ChartType.AREA,

        "组合": ChartType.COMBO,
        "混合": ChartType.COMBO,

        "表格": ChartType.TABLE,
        "明细": ChartType.TABLE,
    }

    # 时间范围映射
    TIME_RANGE_MAPPINGS = {
        "最近15分钟": "15m",
        "15分钟": "15m",
        "最近1小时": "1h",
        "1小时": "1h",
        "一小时": "1h",
        "最近6小时": "6h",
        "6小时": "6h",
        "最近24小时": "24h",
        "24小时": "24h",
        "1天": "24h",
        "今天": "24h",
        "最近3天": "3d",
        "最近7天": "7d",
        "一周": "7d",
        "最近14天": "14d",
        "最近30天": "30d",
        "一个月": "30d",
        "上周": "7d",
        "本周": "7d",
    }

    # 区域映射
    REGION_MAPPINGS = {
        "新加坡": "Singapore",
        "Singapore": "Singapore",
        "美国": "US",
        "US": "US",
        "美东": "US-East",
        "美西": "US-West",
        "北京": "Beijing",
        "上海": "Shanghai",
        "广州": "Guangzhou",
        "深圳": "Shenzhen",
        "东京": "Tokyo",
        "欧洲": "Europe",
        "EU": "Europe",
    }

    def __init__(self, llm_client=None):
        """
        初始化解析器

        Args:
            llm_client: LLM 客户端（用于复杂查询解析）
        """
        self.llm_client = llm_client

    def parse(self, query: str) -> ComplexVisualizationIntent:
        """
        解析复杂可视化查询

        Args:
            query: 自然语言查询

        Returns:
            ComplexVisualizationIntent
        """
        query_lower = query.lower()

        # 1. 提取图表类型
        chart_type = self._detect_chart_type(query)

        # 2. 提取时间范围
        time_range = self._detect_time_range(query)

        # 3. 提取指标（支持多指标）
        metrics = self._detect_metrics(query)

        # 4. 提取筛选条件
        filters = self._detect_filters(query)

        # 5. 提取分组
        group_by = self._detect_group_by(query)

        # 6. 提取聚合方式
        aggregation = self._detect_aggregation(query)

        # 7. 生成标题
        title = self._generate_title(chart_type, metrics, time_range, filters)

        # 8. 构建坐标轴
        axes = self._build_axes(metrics)

        # 9. 构建执行计划
        execution_plan = self._build_execution_plan(metrics, time_range, filters, group_by)

        return ComplexVisualizationIntent(
            chart_type=chart_type,
            title=title,
            metrics=metrics,
            axes=axes,
            time_range=time_range,
            group_by=group_by,
            filters=filters,
            raw_query=query,
            confidence=self._calculate_confidence(query, metrics, chart_type),
            execution_plan=execution_plan,
        )

    def _detect_chart_type(self, query: str) -> ChartType:
        """检测图表类型"""
        # 复杂查询检测
        if any(kw in query for kw in ["关系", "相关性", "散点"]):
            return ChartType.SCATTER

        if any(kw in query for kw in ["组合", "混合"]) or \
           query.count("和") >= 1 and query.count("与") >= 0:
            # 多指标场景，可能需要组合图或多轴
            return ChartType.COMBO

        # 简单关键词匹配
        scores = {ct: 0 for ct in ChartType}
        for chart_type, keywords in self.CHART_TYPE_MAPPINGS.items():
            if isinstance(chart_type, str):
                chart_type_enum = ChartType(chart_type) if chart_type in [e.value for e in ChartType] else None
                if chart_type_enum:
                    for kw in keywords if isinstance(keywords, list) else [keywords]:
                        if kw in query:
                            scores[chart_type_enum] += 1

        max_score = max(scores.values())
        if max_score > 0:
            for ct, score in scores.items():
                if score == max_score:
                    return ct

        # 默认：有"和"/"与"连接多指标时用组合图
        if "和" in query or "与" in query or "、" in query:
            return ChartType.COMBO

        return ChartType.LINE

    def _detect_time_range(self, query: str) -> str:
        """检测时间范围"""
        for pattern, range_val in self.TIME_RANGE_MAPPINGS.items():
            if pattern in query:
                return range_val
        return "1h"

    def _detect_metrics(self, query: str) -> List[MetricSpec]:
        """检测指标（支持多指标）"""
        metrics = []
        detected_names = set()

        # 分词提取指标
        for keyword, spec in self.METRIC_MAPPINGS.items():
            if keyword in query and spec["name"] not in detected_names:
                detected_names.add(spec["name"])

                agg = AggregationType.AVG
                if "agg" in spec:
                    agg_map = {
                        "p99": AggregationType.P99,
                        "p95": AggregationType.P95,
                        "p90": AggregationType.P90,
                        "p50": AggregationType.P50,
                    }
                    agg = agg_map.get(spec["agg"], AggregationType.AVG)

                metrics.append(MetricSpec(
                    name=spec["name"],
                    alias=keyword,
                    aggregation=agg,
                    data_source=DataSource(spec.get("source", "prometheus")),
                    unit=spec.get("unit"),
                ))

        return metrics

    def _detect_filters(self, query: str) -> Dict[str, str]:
        """检测筛选条件"""
        filters = {}

        # 区域过滤
        for cn_name, en_name in self.REGION_MAPPINGS.items():
            if cn_name in query:
                filters["region"] = en_name
                break

        # PSM 过滤
        psm_match = re.search(r"psm[：:\s]*([a-zA-Z0-9_.-]+)", query, re.I)
        if psm_match:
            filters["psm"] = psm_match.group(1)

        # 服务过滤
        service_match = re.search(r"服务[：:\s]*([a-zA-Z0-9_-]+)", query)
        if service_match:
            filters["service"] = service_match.group(1)

        # 状态过滤
        if "故障期间" in query or "异常期间" in query:
            filters["status"] = "incident"

        # 高峰期过滤
        if "高峰期" in query:
            filters["peak_hours"] = "true"

        return filters

    def _detect_group_by(self, query: str) -> List[str]:
        """检测分组"""
        groups = []

        patterns = [
            (r"按区域|各区域|按地区", "region"),
            (r"按服务|各服务", "service"),
            (r"按时间|按小时|按天|按日", "time"),
            (r"按PSM|各PSM", "psm"),
            (r"按机房|各机房", "datacenter"),
            (r"按集群|各集群", "cluster"),
        ]

        for pattern, group in patterns:
            if re.search(pattern, query, re.I):
                groups.append(group)

        return groups

    def _detect_aggregation(self, query: str) -> AggregationType:
        """检测聚合方式"""
        agg_mappings = {
            "平均": AggregationType.AVG,
            "avg": AggregationType.AVG,
            "最大": AggregationType.MAX,
            "峰值": AggregationType.MAX,
            "max": AggregationType.MAX,
            "最小": AggregationType.MIN,
            "min": AggregationType.MIN,
            "总和": AggregationType.SUM,
            "累计": AggregationType.SUM,
            "sum": AggregationType.SUM,
            "p99": AggregationType.P99,
            "p95": AggregationType.P95,
            "p90": AggregationType.P90,
            "p50": AggregationType.P50,
            "计数": AggregationType.COUNT,
            "count": AggregationType.COUNT,
        }

        for keyword, agg in agg_mappings.items():
            if keyword in query.lower():
                return agg

        return AggregationType.AVG

    def _build_axes(self, metrics: List[MetricSpec]) -> List[AxisSpec]:
        """构建坐标轴"""
        if not metrics:
            return []

        axes = []

        # 第一个指标在左轴
        axes.append(AxisSpec(
            label=metrics[0].alias or metrics[0].name,
            metric=metrics[0],
            position="left",
            unit=metrics[0].unit,
        ))

        # 多指标时，第二个在右轴
        if len(metrics) > 1:
            axes.append(AxisSpec(
                label=metrics[1].alias or metrics[1].name,
                metric=metrics[1],
                position="right",
                unit=metrics[1].unit,
            ))

        return axes

    def _build_execution_plan(
        self,
        metrics: List[MetricSpec],
        time_range: str,
        filters: Dict[str, str],
        group_by: List[str],
    ) -> List[Dict[str, Any]]:
        """构建执行计划"""
        plan = []

        for i, metric in enumerate(metrics):
            step = {
                "step": i + 1,
                "action": "query",
                "data_source": metric.data_source.value,
                "metric": metric.name,
                "aggregation": metric.aggregation.value,
                "time_range": time_range,
                "filters": filters,
                "group_by": group_by,
            }

            # 构建 PromQL 或 SQL
            if metric.data_source == DataSource.PROMETHEUS:
                step["query"] = self._build_promql(metric, time_range, filters, group_by)
            elif metric.data_source == DataSource.CLICKHOUSE:
                step["query"] = self._build_sql(metric, time_range, filters, group_by)

            plan.append(step)

        return plan

    def _build_promql(
        self,
        metric: MetricSpec,
        time_range: str,
        filters: Dict[str, str],
        group_by: List[str],
    ) -> str:
        """构建 PromQL 查询"""
        metric_names = {
            "latency": "http_request_duration_seconds",
            "traffic": "http_requests_total",
            "error_rate": "http_requests_total{status=~\"5..\"}",
            "cpu_usage": "process_cpu_usage",
            "memory_usage": "process_resident_memory_bytes",
            "packet_loss": "packet_loss_rate",
            "connections": "active_connections",
        }

        base_metric = metric_names.get(metric.name, metric.name)

        # 添加标签过滤
        labels = []
        for key, value in filters.items():
            labels.append(f'{key}="{value}"')

        if labels:
            base_metric = f"{base_metric}{{{','.join(labels)}}}"

        # 添加聚合
        agg_func_map = {
            AggregationType.AVG: "avg",
            AggregationType.MAX: "max",
            AggregationType.MIN: "min",
            AggregationType.SUM: "sum",
            AggregationType.P99: "histogram_quantile(0.99,",
            AggregationType.P95: "histogram_quantile(0.95,",
        }

        agg_func = agg_func_map.get(metric.aggregation, "")

        if metric.aggregation in [AggregationType.P99, AggregationType.P95]:
            promql = f"{agg_func}{base_metric})"
        elif agg_func:
            if group_by:
                by_clause = f"by ({', '.join(group_by)})"
                promql = f"{agg_func}({base_metric}) {by_clause}"
            else:
                promql = f"{agg_func}({base_metric})"
        else:
            promql = base_metric

        return promql

    def _build_sql(
        self,
        metric: MetricSpec,
        time_range: str,
        filters: Dict[str, str],
        group_by: List[str],
    ) -> str:
        """构建 SQL 查询"""
        # 时间范围转换
        time_clause = {
            "1h": "now() - INTERVAL 1 HOUR",
            "6h": "now() - INTERVAL 6 HOUR",
            "24h": "now() - INTERVAL 1 DAY",
            "7d": "now() - INTERVAL 7 DAY",
            "30d": "now() - INTERVAL 30 DAY",
        }.get(time_range, "now() - INTERVAL 1 HOUR")

        # 基础查询
        sql = f"""
        SELECT
            toStartOfInterval(timestamp, INTERVAL 5 MINUTE) as time,
            {metric.aggregation.value}(value) as {metric.name}
        FROM metrics
        WHERE metric = '{metric.name}'
            AND timestamp >= {time_clause}
        """

        # 添加过滤条件
        for key, value in filters.items():
            sql += f" AND {key} = '{value}'"

        # 添加分组
        if group_by:
            sql += f"\n        GROUP BY time, {', '.join(group_by)}"
        else:
            sql += "\n        GROUP BY time"

        sql += "\n        ORDER BY time"

        return sql

    def _generate_title(
        self,
        chart_type: ChartType,
        metrics: List[MetricSpec],
        time_range: str,
        filters: Dict[str, str],
    ) -> str:
        """生成标题"""
        parts = []

        # 区域
        if "region" in filters:
            parts.append(filters["region"])

        # 指标名称
        if metrics:
            metric_names = [m.alias or m.name for m in metrics[:3]]
            if len(metrics) > 3:
                metric_names.append("...")
            parts.append("、".join(metric_names))

        # 时间范围
        time_names = {
            "15m": "最近15分钟",
            "1h": "最近1小时",
            "6h": "最近6小时",
            "24h": "最近24小时",
            "7d": "最近7天",
            "30d": "最近30天",
        }
        parts.append(time_names.get(time_range, time_range))

        # 图表类型
        chart_names = {
            ChartType.LINE: "趋势图",
            ChartType.BAR: "对比图",
            ChartType.PIE: "分布图",
            ChartType.SCATTER: "关系图",
            ChartType.AREA: "面积图",
            ChartType.COMBO: "组合图",
        }
        parts.append(chart_names.get(chart_type, ""))

        return " ".join(filter(None, parts))

    def _calculate_confidence(
        self,
        query: str,
        metrics: List[MetricSpec],
        chart_type: ChartType,
    ) -> float:
        """计算置信度"""
        confidence = 0.5

        # 有指标识别
        if metrics:
            confidence += 0.2

        # 有图表类型关键词
        chart_keywords = ["趋势", "对比", "分布", "散点", "柱状", "饼图"]
        if any(kw in query for kw in chart_keywords):
            confidence += 0.1

        # 有时间范围
        if any(kw in query for kw in ["最近", "小时", "天", "周"]):
            confidence += 0.1

        # 有分组
        if "按" in query or "各" in query:
            confidence += 0.05

        # 多指标（复杂查询）
        if len(metrics) >= 2:
            confidence += 0.05

        return min(confidence, 1.0)

    def get_supported_complex_queries(self) -> List[Dict[str, str]]:
        """获取支持的复杂查询示例"""
        return [
            {
                "query": "对比新加坡和美国区域的延迟趋势",
                "description": "多区域对比的折线图",
            },
            {
                "query": "显示最近24小时CPU和内存使用率的组合图",
                "description": "多指标组合展示",
            },
            {
                "query": "按服务分组，显示P99延迟和错误率的散点图",
                "description": "分组散点图分析相关性",
            },
            {
                "query": "最近7天每日订单量与延迟的关系",
                "description": "业务与技术指标关联分析",
            },
            {
                "query": "新加坡区域上周故障期间CPU、内存、网络流量的趋势",
                "description": "特定时间段多指标分析",
            },
            {
                "query": "各机房的请求量和错误率对比柱状图",
                "description": "多维度分组对比",
            },
            {
                "query": "最近1小时高峰期的延迟分布热力图",
                "description": "条件过滤热力图",
            },
            {
                "query": "对比P99和P95延迟的变化趋势",
                "description": "多百分位指标对比",
            },
        ]
