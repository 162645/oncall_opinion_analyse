"""
网络测量数据分析 MCP 工具

提供 Ping 数据分析和 Traceroute 数据分析功能
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging

from src.mcp.base import BaseMCPTool, ToolDefinition, ToolResult, ToolStatus
from src.clickhouse import get_clickhouse_client
from src.clickhouse.analyzer import PingAnalyzer, TracerouteAnalyzer, AnalysisConfig

logger = logging.getLogger(__name__)


class PingAnalysisTool(BaseMCPTool):
    """
    Ping 数据分析 MCP 工具

    支持的分析维度:
    - overall: 整体统计
    - time_trend: 时间趋势
    - asn: 按 AS 分组
    - asgeo: 按 AS+Geo 分组
    - country: 按国家分组
    - prefix24: 按 /24 前缀分组
    """

    def __init__(self):
        super().__init__("analyze_ping_data", "analysis")

    def _get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description="""
分析网络 Ping 测量数据，支持多维度统计。

功能:
- 计算延迟统计: 均值、中位数、分位数、标准差
- 高级统计: 变异系数、偏度、峰度、四分位距
- 按维度分组: AS、ASGeo、国家、前缀、时间趋势
- 极端值过滤: 可选择只分析特定分位数范围内的数据

使用场景:
- 了解某个地区的网络延迟情况
- 对比不同 AS 或地区的性能
- 分析网络延迟的时间趋势
- 检测网络延迟异常
""",
            parameters={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "地区名称，如 UKRAINE, RUSSIA, CHINA 等"
                    },
                    "dimension": {
                        "type": "string",
                        "enum": ["overall", "time_trend", "asn", "asgeo", "country", "prefix24"],
                        "default": "overall",
                        "description": "分析维度"
                    },
                    "start_time": {
                        "type": "string",
                        "format": "date-time",
                        "description": "开始时间 (ISO 格式)"
                    },
                    "end_time": {
                        "type": "string",
                        "format": "date-time",
                        "description": "结束时间 (ISO 格式)"
                    },
                    "percentiles": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "default": [50, 90, 95, 99],
                        "description": "要计算的分位数列表"
                    },
                    "outlier_filter_min": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "最小分位数过滤，如 5 表示过滤 P5 以下的数据"
                    },
                    "outlier_filter_max": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "最大分位数过滤，如 95 表示过滤 P95 以上的数据"
                    },
                    "top_n": {
                        "type": "integer",
                        "default": 20,
                        "description": "返回结果数量限制"
                    }
                },
                "required": ["region"]
            },
            server=self.server,
            category="analysis"
        )

    async def execute(self, **kwargs) -> ToolResult:
        """执行 Ping 分析"""
        try:
            region = kwargs.get("region")
            if not region:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="缺少必需参数: region"
                )

            dimension = kwargs.get("dimension", "overall")
            start_time = kwargs.get("start_time")
            end_time = kwargs.get("end_time")
            percentiles = kwargs.get("percentiles", [50, 90, 95, 99])
            outlier_filter_min = kwargs.get("outlier_filter_min")
            outlier_filter_max = kwargs.get("outlier_filter_max")
            top_n = kwargs.get("top_n", 20)

            # 解析时间
            if start_time:
                start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            if end_time:
                end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

            # 创建分析配置
            config = AnalysisConfig(
                percentiles=percentiles,
                outlier_filter_min=outlier_filter_min,
                outlier_filter_max=outlier_filter_max,
            )

            # 获取 ClickHouse 客户端
            client = get_clickhouse_client()
            analyzer = PingAnalyzer(client.client)

            # 执行分析
            if dimension == "overall":
                result = analyzer.analyze_overall(
                    region=region,
                    start_time=start_time,
                    end_time=end_time,
                    config=config
                )
            elif dimension == "time_trend":
                interval = kwargs.get("interval", "hour")
                result = analyzer.analyze_time_trend(
                    region=region,
                    interval=interval,
                    start_time=start_time,
                    end_time=end_time,
                    config=config
                )
            elif dimension == "asn":
                result = analyzer.analyze_by_asn(
                    region=region,
                    top_n=top_n,
                    start_time=start_time,
                    end_time=end_time,
                    config=config
                )
            elif dimension == "asgeo":
                result = analyzer.analyze_by_asgeo(
                    region=region,
                    top_n=top_n,
                    start_time=start_time,
                    end_time=end_time,
                    config=config
                )
            elif dimension == "country":
                result = analyzer.analyze_by_country(
                    region=region,
                    top_n=top_n,
                    start_time=start_time,
                    end_time=end_time,
                    config=config
                )
            elif dimension == "prefix24":
                result = analyzer.analyze_by_prefix24(
                    region=region,
                    top_n=top_n,
                    start_time=start_time,
                    end_time=end_time,
                    config=config
                )
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"不支持的分析维度: {dimension}"
                )

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "region": region,
                    "dimension": dimension,
                    "analysis_result": result
                },
                metadata={
                    "percentiles": percentiles,
                    "outlier_filter": {
                        "min": outlier_filter_min,
                        "max": outlier_filter_max
                    } if outlier_filter_min or outlier_filter_max else None
                }
            )

        except Exception as e:
            logger.error(f"Ping analysis failed: {e}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e)
            )


class TracerouteAnalysisTool(BaseMCPTool):
    """
    Traceroute 数据分析 MCP 工具

    支持:
    - 路径统计分析
    - 末端节点分析
    - AS 路径分析
    """

    def __init__(self):
        super().__init__("analyze_traceroute_data", "analysis")

    def _get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description="""
分析网络 Traceroute 路径数据，查看网络拓扑和路径分布。

功能:
- 路径统计: 分析常见路径和跳数分布
- 末端节点分析: 查看数据最终到达哪些 AS/地理位置
- AS 路径分析: 分析经过的自治系统

使用场景:
- 了解到某个地区的网络路径
- 分析网络拓扑结构
- 识别关键中转节点
""",
            parameters={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "地区名称"
                    },
                    "analysis_type": {
                        "type": "string",
                        "enum": ["path_stats", "terminal_analysis", "as_path"],
                        "default": "path_stats",
                        "description": "分析类型"
                    },
                    "path_type": {
                        "type": "string",
                        "enum": ["ip", "as", "asgeo"],
                        "default": "as",
                        "description": "路径类型: IP路径、AS路径、AS+Geo路径"
                    },
                    "start_time": {
                        "type": "string",
                        "format": "date-time",
                        "description": "开始时间"
                    },
                    "end_time": {
                        "type": "string",
                        "format": "date-time",
                        "description": "结束时间"
                    },
                    "top_n": {
                        "type": "integer",
                        "default": 50,
                        "description": "返回结果数量限制"
                    }
                },
                "required": ["region"]
            },
            server=self.server,
            category="analysis"
        )

    async def execute(self, **kwargs) -> ToolResult:
        """执行 Traceroute 分析"""
        try:
            region = kwargs.get("region")
            if not region:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="缺少必需参数: region"
                )

            analysis_type = kwargs.get("analysis_type", "path_stats")
            path_type = kwargs.get("path_type", "as")
            start_time = kwargs.get("start_time")
            end_time = kwargs.get("end_time")
            top_n = kwargs.get("top_n", 50)

            # 解析时间
            if start_time:
                start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            if end_time:
                end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

            # 获取客户端
            client = get_clickhouse_client()
            analyzer = TracerouteAnalyzer(client.client)

            if analysis_type == "path_stats":
                result = analyzer.analyze_path_statistics(
                    region=region,
                    path_type=path_type,
                    start_time=start_time,
                    end_time=end_time,
                    top_n=top_n
                )
            elif analysis_type == "terminal_analysis":
                result = analyzer.analyze_terminal_nodes(
                    region=region,
                    terminal_type=path_type if path_type in ["as", "asgeo"] else "as",
                    start_time=start_time,
                    end_time=end_time,
                    top_n=top_n
                )
            elif analysis_type == "as_path":
                result = analyzer.analyze_as_paths(
                    region=region,
                    start_time=start_time,
                    end_time=end_time,
                    top_n=top_n
                )
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"不支持的分析类型: {analysis_type}"
                )

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "region": region,
                    "analysis_type": analysis_type,
                    "analysis_result": result
                },
                metadata={
                    "path_type": path_type,
                    "data_source": "quarter"  # 默认使用 1/4 抽样数据
                }
            )

        except Exception as e:
            logger.error(f"Traceroute analysis failed: {e}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e)
            )


class HierarchicalAnalysisTool(BaseMCPTool):
    """
    分层分析 MCP 工具

    支持按层级下钻分析，如 Date → ASGeo → Prefix24
    """

    def __init__(self):
        super().__init__("hierarchical_analysis", "analysis")

    def _get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description="""
分层分析网络测量数据，支持逐层下钻。

层级选项:
- time: 时间维度 (按小时)
- asn: AS 维度
- asgeo: AS+Geo 维度
- prefix24: /24 前缀维度
- country: 国家维度

使用场景:
- 从宏观到微观分析网络延迟
- 按层级过滤极端值后分析
- 深入分析特定 AS 或地区的详细情况
""",
            parameters={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "地区名称"
                    },
                    "hierarchy": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["time", "asn", "asgeo", "prefix24", "country"]
                        },
                        "default": ["asn", "asgeo", "prefix24"],
                        "description": "层级顺序"
                    },
                    "outlier_filter_min": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "最小分位数过滤"
                    },
                    "outlier_filter_max": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "最大分位数过滤"
                    },
                    "start_time": {
                        "type": "string",
                        "format": "date-time",
                        "description": "开始时间"
                    },
                    "end_time": {
                        "type": "string",
                        "format": "date-time",
                        "description": "结束时间"
                    }
                },
                "required": ["region"]
            },
            server=self.server,
            category="analysis"
        )

    async def execute(self, **kwargs) -> ToolResult:
        """执行分层分析"""
        try:
            region = kwargs.get("region")
            if not region:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="缺少必需参数: region"
                )

            hierarchy = kwargs.get("hierarchy", ["asn", "asgeo", "prefix24"])
            outlier_filter_min = kwargs.get("outlier_filter_min")
            outlier_filter_max = kwargs.get("outlier_filter_max")
            start_time = kwargs.get("start_time")
            end_time = kwargs.get("end_time")

            # 解析时间
            if start_time:
                start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            if end_time:
                end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

            # 构建极端值过滤配置
            outlier_filter = None
            if outlier_filter_min is not None or outlier_filter_max is not None:
                outlier_filter = {
                    "percentile_min": outlier_filter_min or 0,
                    "percentile_max": outlier_filter_max or 100
                }

            # 执行分析
            client = get_clickhouse_client()
            analyzer = PingAnalyzer(client.client)

            result = analyzer.hierarchical_analysis(
                region=region,
                hierarchy=hierarchy,
                start_time=start_time,
                end_time=end_time,
                outlier_filter=outlier_filter
            )

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "region": region,
                    "hierarchy": hierarchy,
                    "analysis_result": result
                },
                metadata={
                    "outlier_filter": outlier_filter
                }
            )

        except Exception as e:
            logger.error(f"Hierarchical analysis failed: {e}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e)
            )


class NetworkMetadataTool(BaseMCPTool):
    """
    网络元数据查询 MCP 工具

    提供可用地区、AS 列表等元数据查询
    """

    def __init__(self):
        super().__init__("get_network_metadata", "analysis")

    def _get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description="""
查询网络测量元数据，了解有哪些可用数据。

支持查询:
- regions: 可用地区列表
- asns: 指定地区的 AS 列表
- countries: 指定地区的国家列表
- time_range: 指定地区的数据时间范围
""",
            parameters={
                "type": "object",
                "properties": {
                    "metadata_type": {
                        "type": "string",
                        "enum": ["regions", "asns", "countries", "time_range"],
                        "description": "元数据类型"
                    },
                    "region": {
                        "type": "string",
                        "description": "地区名称 (查询 asns/countries/time_range 时需要)"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 100,
                        "description": "返回数量限制"
                    }
                },
                "required": ["metadata_type"]
            },
            server=self.server,
            category="analysis"
        )

    async def execute(self, **kwargs) -> ToolResult:
        """执行元数据查询"""
        try:
            metadata_type = kwargs.get("metadata_type")
            region = kwargs.get("region")
            limit = kwargs.get("limit", 100)

            if not metadata_type:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="缺少必需参数: metadata_type"
                )

            client = get_clickhouse_client()

            if metadata_type == "regions":
                regions = client.get_regions()
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"regions": regions}
                )

            elif metadata_type == "asns":
                if not region:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error="查询 AS 列表需要指定 region 参数"
                    )
                result = client.execute(
                    f"""
                    SELECT ip_asn, ip_as_name, count() as cnt
                    FROM {region}__ping
                    WHERE ip_asn > 0
                    GROUP BY ip_asn, ip_as_name
                    ORDER BY cnt DESC
                    LIMIT %(limit)s
                    """,
                    {"limit": limit}
                )
                asns = [
                    {"asn": row[0], "as_name": row[1], "sample_count": row[2]}
                    for row in result
                ]
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"asns": asns}
                )

            elif metadata_type == "countries":
                if not region:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error="查询国家列表需要指定 region 参数"
                    )
                result = client.execute(
                    f"""
                    SELECT ip_geo_country, count() as cnt
                    FROM {region}__ping
                    WHERE ip_geo_country != ''
                    GROUP BY ip_geo_country
                    ORDER BY cnt DESC
                    LIMIT %(limit)s
                    """,
                    {"limit": limit}
                )
                countries = [
                    {"country": row[0], "sample_count": row[1]}
                    for row in result
                ]
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"countries": countries}
                )

            elif metadata_type == "time_range":
                if not region:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error="查询时间范围需要指定 region 参数"
                    )
                result = client.execute(
                    f"""
                    SELECT min(measure_time), max(measure_time)
                    FROM {region}__ping
                    """
                )
                if result:
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={
                            "min_time": result[0][0].isoformat() if result[0][0] else None,
                            "max_time": result[0][1].isoformat() if result[0][1] else None
                        }
                    )
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"min_time": None, "max_time": None}
                )

            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"不支持的元数据类型: {metadata_type}"
                )

        except Exception as e:
            logger.error(f"Metadata query failed: {e}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e)
            )


# 注册所有分析工具
ANALYSIS_TOOLS = [
    PingAnalysisTool,
    TracerouteAnalysisTool,
    HierarchicalAnalysisTool,
    NetworkMetadataTool,
]


def get_analysis_tools() -> List[BaseMCPTool]:
    """获取所有分析工具实例"""
    return [tool_class() for tool_class in ANALYSIS_TOOLS]
