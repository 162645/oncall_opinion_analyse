"""
网络分析工具集
提供 Ping 和 Traceroute 数据的分析和可视化工具
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from src.tools.base import BaseTool, ToolMetadata, ToolResult, ToolCategory


class PingStatsTool(BaseTool):
    """
    Ping 统计分析工具

    查询和分析 Ping 数据的 RTT 统计指标
    """

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="ping_stats",
            description="查询和分析 Ping 数据统计，包括平均 RTT、中位数、百分位数等指标",
            category=ToolCategory.ANALYSIS,
            parameters={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "地区名称，如 UKRAINE",
                    },
                    "dimension": {
                        "type": "string",
                        "enum": ["overall", "asn", "asgeo", "country", "data_center", "prefix24"],
                        "description": "分析维度",
                        "default": "overall",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "开始时间 (ISO 格式，可选)",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "结束时间 (ISO 格式，可选)",
                    },
                    "asn": {
                        "type": "integer",
                        "description": "过滤特定 AS",
                    },
                    "country": {
                        "type": "string",
                        "description": "过滤特定国家",
                    },
                },
                "required": ["region"],
            },
            returns={
                "type": "object",
                "description": "包含统计指标的字典",
            },
            examples=[
                {"region": "UKRAINE", "dimension": "overall"},
                {"region": "UKRAINE", "dimension": "asn"},
                {"region": "UKRAINE", "dimension": "country"},
            ],
            tags=["network", "ping", "rtt", "statistics"],
        )

    async def execute(self, **params) -> ToolResult:
        """执行 Ping 统计查询"""
        try:
            from src.clickhouse import get_clickhouse_client
            from src.clickhouse.analyzer import PingAnalyzer, AnalysisConfig

            client = get_clickhouse_client()
            analyzer = PingAnalyzer(client.client)

            region = params.get("region")
            dimension = params.get("dimension", "overall")

            start_time = None
            end_time = None
            if params.get("start_time"):
                start_time = datetime.fromisoformat(params["start_time"])
            if params.get("end_time"):
                end_time = datetime.fromisoformat(params["end_time"])

            filters = {}
            if params.get("asn"):
                filters["ip_asn"] = params["asn"]
            if params.get("country"):
                filters["ip_geo_country"] = params["country"]

            config = AnalysisConfig(percentiles=[50, 90, 95, 99])

            result = None
            if dimension == "overall":
                result = analyzer.analyze_overall(region, start_time, end_time, config=config, **filters)
            elif dimension == "asn":
                result = analyzer.analyze_by_asn(region, start_time=start_time, end_time=end_time, config=config, **filters)
            elif dimension == "asgeo":
                result = analyzer.analyze_by_asgeo(region, start_time=start_time, end_time=end_time, config=config, **filters)
            elif dimension == "country":
                result = analyzer.analyze_by_country(region, start_time=start_time, end_time=end_time, config=config, **filters)
            elif dimension == "data_center":
                result = analyzer.analyze_by_data_center(region, start_time=start_time, end_time=end_time, config=config, **filters)
            else:
                result = analyzer.analyze_overall(region, start_time, end_time, config=config, **filters)

            return ToolResult(
                status="success",
                data={
                    "region": region,
                    "dimension": dimension,
                    "statistics": result,
                    "supports_visualization": True,
                    "suggested_chart": "bar" if dimension != "overall" else "metric",
                },
            )

        except Exception as e:
            return ToolResult(status="error", error=str(e))


class PingTrendTool(BaseTool):
    """
    Ping 时间趋势分析工具

    分析 RTT 随时间的变化趋势
    """

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="ping_trend",
            description="分析 Ping 数据的时间趋势，查看 RTT 随时间的变化",
            category=ToolCategory.ANALYSIS,
            parameters={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "地区名称",
                    },
                    "interval": {
                        "type": "string",
                        "enum": ["minute", "hour", "day"],
                        "description": "时间粒度",
                        "default": "hour",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "开始时间 (ISO 格式)",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "结束时间 (ISO 格式)",
                    },
                    "asn": {
                        "type": "integer",
                        "description": "过滤特定 AS",
                    },
                },
                "required": ["region"],
            },
            returns={
                "type": "object",
                "description": "时间序列数据",
            },
            examples=[
                {"region": "UKRAINE", "interval": "hour"},
                {"region": "UKRAINE", "interval": "day", "asn": 12345},
            ],
            tags=["network", "ping", "trend", "time-series"],
        )

    async def execute(self, **params) -> ToolResult:
        """执行时间趋势分析"""
        try:
            from src.clickhouse import get_clickhouse_client
            from src.clickhouse.analyzer import PingAnalyzer, AnalysisConfig

            client = get_clickhouse_client()
            analyzer = PingAnalyzer(client.client)

            region = params.get("region")
            interval = params.get("interval", "hour")

            start_time = None
            end_time = None
            if params.get("start_time"):
                start_time = datetime.fromisoformat(params["start_time"])
            if params.get("end_time"):
                end_time = datetime.fromisoformat(params["end_time"])

            filters = {}
            if params.get("asn"):
                filters["ip_asn"] = params["asn"]

            config = AnalysisConfig(percentiles=[50, 90, 95, 99])
            result = analyzer.analyze_time_trend(region, interval, start_time, end_time, config=config, **filters)

            return ToolResult(
                status="success",
                data={
                    "region": region,
                    "interval": interval,
                    "trend_data": result,
                    "supports_visualization": True,
                    "suggested_chart": "line",
                },
            )

        except Exception as e:
            return ToolResult(status="error", error=str(e))


class TracerouteAnalysisTool(BaseTool):
    """
    Traceroute 分析工具

    分析网络路径数据
    """

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="traceroute_analysis",
            description="分析 Traceroute 路径数据，查看 AS 路径、跳数分布等",
            category=ToolCategory.ANALYSIS,
            parameters={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "地区名称",
                    },
                    "analysis_type": {
                        "type": "string",
                        "enum": ["paths", "terminal_nodes", "hop_distribution", "path_to_asn"],
                        "description": "分析类型",
                        "default": "paths",
                    },
                    "path_type": {
                        "type": "string",
                        "enum": ["ip", "as", "asgeo"],
                        "description": "路径类型",
                        "default": "as",
                    },
                    "target_asn": {
                        "type": "integer",
                        "description": "目标 AS（用于 path_to_asn 分析）",
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "返回数量",
                        "default": 50,
                    },
                },
                "required": ["region"],
            },
            returns={
                "type": "object",
                "description": "路径分析结果",
            },
            examples=[
                {"region": "UKRAINE", "analysis_type": "paths", "path_type": "as"},
                {"region": "UKRAINE", "analysis_type": "terminal_nodes"},
                {"region": "UKRAINE", "analysis_type": "path_to_asn", "target_asn": 12345},
            ],
            tags=["network", "traceroute", "path", "as"],
        )

    async def execute(self, **params) -> ToolResult:
        """执行 Traceroute 分析"""
        try:
            from src.clickhouse import get_clickhouse_client
            from src.clickhouse.analyzer import TracerouteAnalyzer

            client = get_clickhouse_client()
            analyzer = TracerouteAnalyzer(client.client)

            region = params.get("region")
            analysis_type = params.get("analysis_type", "paths")
            path_type = params.get("path_type", "as")
            top_n = params.get("top_n", 50)

            result = {}
            suggested_chart = "table"

            if analysis_type == "paths":
                result = analyzer.analyze_path_statistics(region, path_type=path_type, top_n=top_n)
                result["hop_distribution"] = analyzer.analyze_hop_distribution(region)
                suggested_chart = "sankey"

            elif analysis_type == "terminal_nodes":
                result = analyzer.analyze_terminal_nodes(region, terminal_type="asgeo", top_n=top_n)
                suggested_chart = "treemap"

            elif analysis_type == "hop_distribution":
                result = analyzer.analyze_hop_distribution(region)
                suggested_chart = "histogram"

            elif analysis_type == "path_to_asn":
                target_asn = params.get("target_asn")
                if not target_asn:
                    return ToolResult(status="error", error="target_asn is required for path_to_asn analysis")
                result = analyzer.analyze_paths_to_target(region, target_asn=target_asn, top_n=top_n)
                suggested_chart = "flow"

            return ToolResult(
                status="success",
                data={
                    "region": region,
                    "analysis_type": analysis_type,
                    "result": result,
                    "supports_visualization": True,
                    "suggested_chart": suggested_chart,
                },
            )

        except Exception as e:
            return ToolResult(status="error", error=str(e))


class DrillDownAnalysisTool(BaseTool):
    """
    下钻分析工具

    支持从高层级逐步下钻到细节
    """

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="drill_down_analysis",
            description="下钻分析：从整体统计逐步深入到 AS、国家、前缀等细节",
            category=ToolCategory.ANALYSIS,
            parameters={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "地区名称",
                    },
                    "level": {
                        "type": "string",
                        "enum": ["overall", "asn", "asgeo", "country", "data_center"],
                        "description": "当前层级",
                    },
                    "level_value": {
                        "type": "string",
                        "description": "当前层级的值（overall 时可为空）",
                    },
                    "next_level": {
                        "type": "string",
                        "enum": ["asn", "asgeo", "country", "prefix24", "data_center"],
                        "description": "下一层级",
                    },
                },
                "required": ["region", "level", "next_level"],
            },
            returns={
                "type": "object",
                "description": "下一层级的统计数据",
            },
            examples=[
                {"region": "UKRAINE", "level": "overall", "next_level": "asn"},
                {"region": "UKRAINE", "level": "asn", "level_value": "12345", "next_level": "country"},
            ],
            tags=["network", "analysis", "drill-down", "hierarchical"],
        )

    async def execute(self, **params) -> ToolResult:
        """执行下钻分析"""
        try:
            from src.clickhouse import get_clickhouse_client
            from src.clickhouse.analyzer import PingAnalyzer, AnalysisConfig

            client = get_clickhouse_client()
            analyzer = PingAnalyzer(client.client)

            region = params.get("region")
            level = params.get("level")
            level_value = params.get("level_value")
            next_level = params.get("next_level")

            config = AnalysisConfig(percentiles=[50, 90, 95, 99])
            result = analyzer.drill_down(
                region=region,
                level=level,
                level_value=level_value,
                next_level=next_level,
                config=config,
            )

            return ToolResult(
                status="success",
                data={
                    "region": region,
                    "level": level,
                    "level_value": level_value,
                    "next_level": next_level,
                    "children": result.get("children", []),
                    "supports_visualization": True,
                    "suggested_chart": "bar",
                },
            )

        except Exception as e:
            return ToolResult(status="error", error=str(e))


class AnomalyDetectionTool(BaseTool):
    """
    异常检测工具

    检测网络数据中的异常值
    """

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="anomaly_detection",
            description="检测网络数据中的异常值，基于统计方法识别延迟突增等异常",
            category=ToolCategory.ANALYSIS,
            parameters={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "地区名称",
                    },
                    "threshold_std": {
                        "type": "number",
                        "description": "标准差阈值倍数",
                        "default": 3.0,
                    },
                    "asn": {
                        "type": "integer",
                        "description": "过滤特定 AS",
                    },
                },
                "required": ["region"],
            },
            returns={
                "type": "object",
                "description": "异常检测结果",
            },
            examples=[
                {"region": "UKRAINE"},
                {"region": "UKRAINE", "threshold_std": 2.5},
            ],
            tags=["network", "anomaly", "detection"],
        )

    async def execute(self, **params) -> ToolResult:
        """执行异常检测"""
        try:
            from src.clickhouse import get_clickhouse_client
            from src.clickhouse.analyzer import PingAnalyzer

            client = get_clickhouse_client()
            analyzer = PingAnalyzer(client.client)

            region = params.get("region")
            threshold_std = params.get("threshold_std", 3.0)

            filters = {}
            if params.get("asn"):
                filters["ip_asn"] = params["asn"]

            result = analyzer.detect_anomalies(
                region=region,
                threshold_std=threshold_std,
                **filters
            )

            return ToolResult(
                status="success",
                data={
                    "region": region,
                    "threshold_std": threshold_std,
                    **result,
                    "supports_visualization": True,
                    "suggested_chart": "scatter",
                },
            )

        except Exception as e:
            return ToolResult(status="error", error=str(e))


class CorrelationAnalysisTool(BaseTool):
    """
    关联分析工具

    分析 Ping 和 Traceroute 数据之间的关联
    """

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="correlation_analysis",
            description="分析 Ping 和 Traceroute 数据之间的关联，通过 prefix24 关联",
            category=ToolCategory.ANALYSIS,
            parameters={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "地区名称",
                    },
                    "prefix24": {
                        "type": "string",
                        "description": "/24 前缀",
                    },
                },
                "required": ["region", "prefix24"],
            },
            returns={
                "type": "object",
                "description": "关联分析结果",
            },
            examples=[
                {"region": "UKRAINE", "prefix24": "192.168.1.0/24"},
            ],
            tags=["network", "correlation", "ping", "traceroute"],
        )

    async def execute(self, **params) -> ToolResult:
        """执行关联分析"""
        try:
            from src.clickhouse import get_clickhouse_client
            from src.clickhouse.analyzer import TracerouteAnalyzer

            client = get_clickhouse_client()
            analyzer = TracerouteAnalyzer(client.client)

            region = params.get("region")
            prefix24 = params.get("prefix24")

            result = analyzer.correlate_ping_trace(region=region, prefix24=prefix24)

            return ToolResult(
                status="success",
                data={
                    "region": region,
                    "prefix24": prefix24,
                    **result,
                    "supports_visualization": True,
                    "suggested_chart": "combined",
                },
            )

        except Exception as e:
            return ToolResult(status="error", error=str(e))


class VisualizationTool(BaseTool):
    """
    可视化工具

    根据数据生成图表
    """

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="create_visualization",
            description="根据分析数据创建可视化图表，支持柱状图、折线图、饼图等",
            category=ToolCategory.UTILITY,
            parameters={
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "enum": ["bar", "line", "pie", "scatter", "histogram", "treemap", "sankey"],
                        "description": "图表类型",
                    },
                    "title": {
                        "type": "string",
                        "description": "图表标题",
                    },
                    "data": {
                        "type": "object",
                        "description": "图表数据",
                    },
                    "x_axis": {
                        "type": "string",
                        "description": "X轴字段名",
                    },
                    "y_axis": {
                        "type": "string",
                        "description": "Y轴字段名",
                    },
                },
                "required": ["chart_type", "data"],
            },
            returns={
                "type": "object",
                "description": "图表配置或 HTML",
            },
            examples=[
                {
                    "chart_type": "bar",
                    "title": "各 AS 平均延迟",
                    "data": {"x": ["AS1", "AS2"], "y": [10, 20]},
                    "x_axis": "AS",
                    "y_axis": "延迟(ms)",
                },
            ],
            tags=["visualization", "chart", "graph"],
        )

    async def execute(self, **params) -> ToolResult:
        """生成可视化"""
        try:
            chart_type = params.get("chart_type")
            title = params.get("title", "")
            data = params.get("data")
            x_axis = params.get("x_axis", "")
            y_axis = params.get("y_axis", "")

            # 构建图表配置
            chart_config = {
                "title": title,
                "chartType": chart_type,
                "data": data,
                "xAxisName": x_axis,
                "yAxisName": y_axis,
            }

            return ToolResult(
                status="success",
                data={
                    "chart_config": chart_config,
                    "render_ready": True,
                },
            )

        except Exception as e:
            return ToolResult(status="error", error=str(e))


class CompareRegionsTool(BaseTool):
    """
    区域对比工具

    对比多个区域的数据
    """

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="compare_regions",
            description="对比多个区域的网络性能数据",
            category=ToolCategory.ANALYSIS,
            parameters={
                "type": "object",
                "properties": {
                    "regions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要对比的区域列表",
                    },
                    "metric": {
                        "type": "string",
                        "enum": ["mean_rtt", "median_rtt", "p95_rtt", "sample_count"],
                        "description": "对比指标",
                        "default": "mean_rtt",
                    },
                },
                "required": ["regions"],
            },
            returns={
                "type": "object",
                "description": "对比结果",
            },
            examples=[
                {"regions": ["UKRAINE", "RUSSIA"], "metric": "mean_rtt"},
            ],
            tags=["network", "comparison", "regions"],
        )

    async def execute(self, **params) -> ToolResult:
        """执行区域对比"""
        try:
            from src.clickhouse import get_clickhouse_client
            from src.clickhouse.analyzer import PingAnalyzer, AnalysisConfig

            client = get_clickhouse_client()
            analyzer = PingAnalyzer(client.client)

            regions = params.get("regions", [])
            metric = params.get("metric", "mean_rtt")

            config = AnalysisConfig(percentiles=[50, 90, 95, 99])

            results = {}
            for region in regions:
                try:
                    stats = analyzer.analyze_overall(region=region, config=config)
                    results[region] = stats
                except Exception as e:
                    results[region] = {"error": str(e)}

            # 提取对比数据
            comparison_data = {
                "regions": regions,
                "metric": metric,
                "values": {
                    region: results.get(region, {}).get(metric)
                    for region in regions
                },
                "details": results,
            }

            return ToolResult(
                status="success",
                data={
                    **comparison_data,
                    "supports_visualization": True,
                    "suggested_chart": "bar",
                },
            )

        except Exception as e:
            return ToolResult(status="error", error=str(e))


# 注册所有工具
def register_network_tools(registry):
    """注册网络分析工具"""
    tools = [
        PingStatsTool(),
        PingTrendTool(),
        TracerouteAnalysisTool(),
        DrillDownAnalysisTool(),
        AnomalyDetectionTool(),
        CorrelationAnalysisTool(),
        VisualizationTool(),
        CompareRegionsTool(),
    ]

    for tool in tools:
        registry.register(tool)

    return len(tools)
