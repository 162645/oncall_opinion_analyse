"""
数据库元数据查询工具
用于查询数据库结构、表信息、数据概况等
"""

from typing import Any, Dict, Optional
from dataclasses import dataclass

from src.tools.base import BaseTool, ToolMetadata, ToolCategory, ToolResult


@dataclass
class DatabaseSchemaResult:
    """数据库结构查询结果"""
    regions: list
    region_details: list
    total_tables: int
    total_records: int


class DatabaseSchemaTool(BaseTool):
    """
    数据库元数据查询工具

    支持的操作:
    - list_regions: 列出所有地区
    - get_region_info: 获取指定地区的详细信息
    - get_overview: 获取数据库整体概况
    - list_data_centers: 列出数据中心
    """

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="database_schema",
            description="数据库元数据查询工具，用于查询数据库中有哪些数据、表结构、地区信息等",
            category=ToolCategory.DATABASE,
            parameters={
                "action": {
                    "type": "string",
                    "description": "操作类型",
                    "enum": ["list_regions", "get_region_info", "get_overview", "list_data_centers"],
                    "default": "get_overview",
                },
                "region": {
                    "type": "string",
                    "description": "地区名称（仅 get_region_info 操作需要）",
                },
            },
            tags=["database", "schema", "metadata", "clickhouse"],
            examples=[
                {"action": "get_overview", "description": "获取数据库整体概况"},
                {"action": "list_regions", "description": "列出所有可用地区"},
                {"action": "get_region_info", "region": "UKRAINE", "description": "获取 UKRAINE 地区详情"},
            ],
        )

    async def execute(self, **params) -> ToolResult:
        """执行数据库元数据查询"""
        action = params.get("action", "get_overview")
        region = params.get("region")

        try:
            from src.clickhouse import get_clickhouse_client

            client = get_clickhouse_client()

            if action == "list_regions":
                return await self._list_regions(client)
            elif action == "get_region_info":
                return await self._get_region_info(client, region)
            elif action == "list_data_centers":
                return await self._list_data_centers(client, region)
            else:
                return await self._get_overview(client)

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                data=None,
            )

    async def _list_regions(self, client) -> ToolResult:
        """列出所有地区"""
        regions = client.get_regions()

        return ToolResult(
            success=True,
            data={
                "regions": regions,
                "count": len(regions),
                "summary": f"数据库中共有 {len(regions)} 个地区: {', '.join(regions)}",
            },
        )

    async def _get_region_info(self, client, region: str) -> ToolResult:
        """获取指定地区详情"""
        if not region:
            return ToolResult(
                success=False,
                error="请指定地区名称",
            )

        info = client.get_region_info(region)
        if not info:
            return ToolResult(
                success=False,
                error=f"未找到地区 {region} 的信息",
            )

        # 获取时间范围
        min_time, max_time = client.get_time_range(region)

        # 获取 AS 数量
        as_list = client.get_available_asns(region, limit=1000)

        return ToolResult(
            success=True,
            data={
                "region": region,
                "ping_table": info.ping_table,
                "trace_table": info.trace_table,
                "total_ping_rows": info.total_ping_rows,
                "data_centers": info.data_centers,
                "min_time": str(min_time) if min_time else None,
                "max_time": str(max_time) if max_time else None,
                "unique_as_count": len(as_list),
                "summary": f"{region} 地区: {info.total_ping_rows:,} 条 Ping 记录, {len(info.data_centers)} 个数据中心, {len(as_list)} 个 AS",
            },
        )

    async def _list_data_centers(self, client, region: str) -> ToolResult:
        """列出数据中心"""
        if not region:
            # 获取所有地区的数据中心
            regions = client.get_regions()
            all_dcs = {}
            for r in regions:
                dcs = client.get_available_data_centers(r)
                all_dcs[r] = [dc["data_center"] for dc in dcs]
            return ToolResult(
                success=True,
                data={"data_centers_by_region": all_dcs, "summary": f"共 {len(all_dcs)} 个地区的数据中心信息"},
            )

        dcs = client.get_available_data_centers(region)
        return ToolResult(
            success=True,
            data={
                "region": region,
                "data_centers": dcs,
                "summary": f"{region} 地区共 {len(dcs)} 个数据中心",
            },
        )

    async def _get_overview(self, client) -> ToolResult:
        """获取数据库整体概况"""
        regions = client.get_regions()

        region_details = []
        total_records = 0

        for region in regions:
            info = client.get_region_info(region)
            if info:
                min_time, max_time = client.get_time_range(region)
                records = info.total_ping_rows or 0
                total_records += records

                region_details.append({
                    "region": region,
                    "total_records": records,
                    "data_centers": info.data_centers[:5] if info.data_centers else [],
                    "min_time": str(min_time)[:10] if min_time else None,
                    "max_time": str(max_time)[:10] if max_time else None,
                })

        # 构建结构化数据
        summary_parts = [f"数据库中有 {len(regions)} 个地区"]
        if region_details:
            for rd in region_details:
                summary_parts.append(
                    f"{rd['region']}: {rd['total_records']:,} 条记录, "
                    f"{len(rd['data_centers'])} 个数据中心"
                )

        data = {
            "total_regions": len(regions),
            "total_records": total_records,
            "regions": region_details,
            "summary": " | ".join(summary_parts),
        }

        return ToolResult(
            success=True,
            data=data,
        )
