"""
ClickHouse 工具
供 Agent 调用的网络测量数据查询工具
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from src.tools.base import BaseTool, ToolMetadata, ToolResult, ToolCategory
from src.clickhouse import get_clickhouse_client, QueryFilters
from src.analysis import PingAnalyzer, TraceAnalyzer


class ClickHouseQueryTool(BaseTool):
    """
    ClickHouse 查询工具

    提供网络测量数据的查询功能
    """

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="clickhouse_query",
            description="查询网络测量数据（Ping、Traceroute）",
            category=ToolCategory.DATABASE,
            parameters={
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": ["ping_stats", "ping_trend", "trace_stats", "path_analysis", "correlation"],
                        "description": "查询类型",
                    },
                    "region": {
                        "type": "string",
                        "description": "地区名称，如 UKRAINE",
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
                        "description": "AS 号",
                    },
                    "prefix24": {
                        "type": "string",
                        "description": "/24 前缀",
                    },
                    "group_by": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "分组字段",
                    },
                    "interval": {
                        "type": "string",
                        "enum": ["minute", "hour", "day"],
                        "description": "时间间隔",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量限制",
                        "default": 100,
                    },
                },
                "required": ["query_type", "region"],
            },
            returns={
                "type": "object",
                "description": "查询结果",
            },
            examples=[
                {
                    "query_type": "ping_stats",
                    "region": "UKRAINE",
                    "group_by": ["ip_asn"],
                },
                {
                    "query_type": "ping_trend",
                    "region": "UKRAINE",
                    "interval": "hour",
                },
            ],
            tags=["database", "network", "measurement"],
        )

    async def execute(self, **params) -> ToolResult:
        """执行查询"""
        try:
            client = get_clickhouse_client()
            query_type = params.get("query_type")
            region = params.get("region")

            # 解析时间
            start_time = None
            end_time = None
            if params.get("start_time"):
                start_time = datetime.fromisoformat(params["start_time"])
            if params.get("end_time"):
                end_time = datetime.fromisoformat(params["end_time"])

            # 默认时间范围：最近 24 小时
            if not start_time and not end_time:
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(hours=24)

            filters = QueryFilters(
                region=region,
                start_time=start_time,
                end_time=end_time,
                asn=params.get("asn"),
                prefix24=params.get("prefix24"),
                limit=params.get("limit", 100),
            )

            if query_type == "ping_stats":
                group_by = params.get("group_by")
                result = client.query_ping_stats(filters, group_by)

                return ToolResult(
                    success=True,
                    data={
                        "query_type": query_type,
                        "region": region,
                        "statistics": result,
                    },
                )

            elif query_type == "ping_trend":
                interval = params.get("interval", "hour")
                result = client.query_ping_trend(filters, interval)

                return ToolResult(
                    success=True,
                    data={
                        "query_type": query_type,
                        "region": region,
                        "interval": interval,
                        "trend_data": result,
                    },
                )

            elif query_type == "trace_stats":
                result = client.query_path_stats(filters)

                return ToolResult(
                    success=True,
                    data={
                        "query_type": query_type,
                        "region": region,
                        "path_stats": result,
                    },
                )

            elif query_type == "path_analysis":
                target_asn = params.get("asn")
                if target_asn:
                    result = client.query_paths_to_target(filters, target_asn)
                else:
                    result = client.query_path_stats(filters)

                return ToolResult(
                    success=True,
                    data={
                        "query_type": query_type,
                        "region": region,
                        "paths": result,
                    },
                )

            elif query_type == "correlation":
                prefix24 = params.get("prefix24")
                if not prefix24:
                    return ToolResult(
                        status="error",
                        error="prefix24 is required for correlation query",
                    )

                result = client.query_ping_trace_correlation(filters, prefix24)

                return ToolResult(
                    success=True,
                    data={
                        "query_type": query_type,
                        "region": region,
                        "prefix24": prefix24,
                        "correlation": result,
                    },
                )

            else:
                return ToolResult(
                    status="error",
                    error=f"Unknown query type: {query_type}",
                )

        except Exception as e:
            return ToolResult(
                status="error",
                error=str(e),
            )


class PingAnalysisTool(BaseTool):
    """
    Ping 数据分析工具

    提供 RTT 统计分析、异常检测等功能
    """

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="ping_analysis",
            description="分析 Ping 数据，计算 RTT 统计指标",
            category=ToolCategory.ANALYSIS,
            parameters={
                "type": "object",
                "properties": {
                    "analysis_type": {
                        "type": "string",
                        "enum": ["statistics", "distribution", "by_asn", "by_asgeo", "by_country", "anomalies"],
                        "description": "分析类型",
                    },
                    "data": {
                        "type": "array",
                        "description": "Ping 数据列表",
                    },
                },
                "required": ["analysis_type", "data"],
            },
            returns={
                "type": "object",
                "description": "分析结果",
            },
            tags=["analysis", "network", "rtt"],
        )

    async def execute(self, **params) -> ToolResult:
        """执行分析"""
        try:
            analyzer = PingAnalyzer()
            analyzer.load_data(params.get("data", []))

            analysis_type = params.get("analysis_type")

            if analysis_type == "statistics":
                result = analyzer.calculate_rtt_statistics()
            elif analysis_type == "distribution":
                result = analyzer.calculate_rtt_distribution()
            elif analysis_type == "by_asn":
                result = analyzer.analyze_by_asn()
            elif analysis_type == "by_asgeo":
                result = analyzer.analyze_by_asgeo()
            elif analysis_type == "by_country":
                result = analyzer.analyze_by_country()
            elif analysis_type == "anomalies":
                result = analyzer.detect_rtt_anomalies()
            else:
                return ToolResult(
                    status="error",
                    error=f"Unknown analysis type: {analysis_type}",
                )

            return ToolResult(
                success=True,
                data={
                    "analysis_type": analysis_type,
                    "result": result,
                },
            )

        except Exception as e:
            return ToolResult(
                status="error",
                error=str(e),
            )


class TraceAnalysisTool(BaseTool):
    """
    Traceroute 分析工具

    提供路径分析、AS 路径分析等功能
    """

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="trace_analysis",
            description="分析 Traceroute 数据，提取路径信息",
            category=ToolCategory.ANALYSIS,
            parameters={
                "type": "object",
                "properties": {
                    "analysis_type": {
                        "type": "string",
                        "enum": ["statistics", "ip_paths", "as_paths", "asgeo_paths", "variability", "report"],
                        "description": "分析类型",
                    },
                    "data": {
                        "type": "array",
                        "description": "Traceroute 数据列表",
                    },
                },
                "required": ["analysis_type", "data"],
            },
            returns={
                "type": "object",
                "description": "分析结果",
            },
            tags=["analysis", "network", "traceroute", "path"],
        )

    async def execute(self, **params) -> ToolResult:
        """执行分析"""
        try:
            analyzer = TraceAnalyzer()
            analyzer.load_data(params.get("data", []))

            analysis_type = params.get("analysis_type")

            if analysis_type == "statistics":
                result = analyzer.analyze_path_statistics()
            elif analysis_type == "ip_paths":
                result = analyzer.analyze_ip_paths()
            elif analysis_type == "as_paths":
                result = analyzer.analyze_as_paths()
            elif analysis_type == "asgeo_paths":
                result = analyzer.analyze_asgeo_paths()
            elif analysis_type == "variability":
                result = analyzer.analyze_path_variability()
            elif analysis_type == "report":
                result = analyzer.generate_report()
            else:
                return ToolResult(
                    status="error",
                    error=f"Unknown analysis type: {analysis_type}",
                )

            return ToolResult(
                success=True,
                data={
                    "analysis_type": analysis_type,
                    "result": result,
                },
            )

        except Exception as e:
            return ToolResult(
                status="error",
                error=str(e),
            )


# 工具注册函数
def register_clickhouse_tools(registry):
    """注册 ClickHouse 相关工具"""
    registry.register(ClickHouseQueryTool())
    registry.register(PingAnalysisTool())
    registry.register(TraceAnalysisTool())
