"""
ClickHouse API 路由
提供网络测量数据查询接口
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from src.clickhouse import (
    ClickHouseClient,
    get_clickhouse_client,
    QueryFilters,
)
from src.clickhouse.analyzer import (
    PingAnalyzer,
    TracerouteAnalyzer,
    AnalysisConfig,
)

router = APIRouter()


# ===== 请求/响应模型 =====

class PingStatsRequest(BaseModel):
    """Ping 统计请求"""
    region: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    asn: Optional[int] = None
    prefix24: Optional[str] = None
    data_center: Optional[str] = None
    country: Optional[str] = None
    isp: Optional[str] = None  # 运营商筛选
    group_by: Optional[List[str]] = None
    limit: int = Field(default=100, ge=1, le=10000)


class PingStatsResponse(BaseModel):
    """Ping 统计响应"""
    success: bool
    region: str
    total_samples: int
    statistics: Dict[str, Any]
    grouped_stats: Optional[List[Dict[str, Any]]] = None


class PathStatsRequest(BaseModel):
    """路径统计请求"""
    region: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    target_asn: Optional[int] = None
    limit: int = Field(default=100, ge=1, le=10000)


class PathStatsResponse(BaseModel):
    """路径统计响应"""
    success: bool
    region: str
    total_traces: int
    unique_paths: int
    top_paths: List[Dict[str, Any]]


class TimeSeriesRequest(BaseModel):
    """时间序列请求"""
    region: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    asn: Optional[int] = None
    isp: Optional[str] = None  # 运营商筛选
    interval: str = Field(default="hour", description="minute, hour, day")
    limit: int = Field(default=1000, ge=1, le=10000)


class TimeSeriesResponse(BaseModel):
    """时间序列响应"""
    success: bool
    region: str
    interval: str
    data: List[Dict[str, Any]]


class CorrelationRequest(BaseModel):
    """关联查询请求"""
    region: str
    prefix24: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class CorrelationResponse(BaseModel):
    """关联查询响应"""
    success: bool
    prefix24: str
    ping_stats: Dict[str, Any]
    trace_paths: List[Dict[str, Any]]


class EnhancedPingStatsRequest(BaseModel):
    """增强版 Ping 统计请求"""
    region: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    analysis_dimension: str = Field(default="overall", description="overall, asn, asgeo, country, region, city, data_center, prefix24")
    asn: Optional[int] = None
    asgeo: Optional[str] = None
    prefix24: Optional[str] = None
    data_center: Optional[str] = None
    country: Optional[str] = None
    isp: Optional[str] = None  # 运营商筛选
    percentiles: List[int] = Field(default=[50, 90, 95, 99])
    interval: str = Field(default="hour", description="minute, hour, day")
    top_n: int = Field(default=50, ge=1, le=500)
    # 极端值过滤
    outlier_filter_min: Optional[float] = Field(default=None, ge=0, le=100, description="最小分位数过滤，如 5 表示过滤 P5 以下的数据")
    outlier_filter_max: Optional[float] = Field(default=None, ge=0, le=100, description="最大分位数过滤，如 95 表示过滤 P95 以上的数据")
    # 分位数范围模式
    percentile_range_mode: bool = Field(default=False, description="是否为分位数范围查询模式，会计算所有指定分位数")


class EnhancedTraceStatsRequest(BaseModel):
    """增强版 Traceroute 统计请求"""
    region: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    path_type: str = Field(default="as", description="ip, as, asgeo")
    target_asn: Optional[int] = None
    prefix24: Optional[str] = None
    top_n: int = Field(default=50, ge=1, le=500)


class AnomalyDetectionRequest(BaseModel):
    """异常检测请求"""
    region: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    threshold_std: float = Field(default=3.0, ge=1.0, le=10.0)
    asn: Optional[int] = None
    prefix24: Optional[str] = None


class TerminalAnalysisRequest(BaseModel):
    """末端节点分析请求"""
    region: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    terminal_type: str = Field(default="as", description="as 或 asgeo")
    top_n: int = Field(default=50, ge=1, le=500)
    include_paths: bool = Field(default=True, description="是否包含示例路径")
    # 新增：末端节点过滤
    terminal_filter: Optional[str] = Field(default=None, description="末端节点模糊搜索过滤")
    # 新增：数据中心筛选
    data_center: Optional[str] = Field(default=None, description="数据中心筛选")
    # 新增：数据类型
    trace_type: str = Field(default="quarter", description="quarter 或 full")


class TerminalPrefix24Request(BaseModel):
    """末端节点的 Prefix24 请求"""
    region: str
    terminal: str
    terminal_type: str = Field(default="asgeo", description="as 或 asgeo")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    top_n: int = Field(default=100, ge=1, le=500)


class PingTraceCorrelationRequest(BaseModel):
    """Ping-Trace 关联请求"""
    region: str
    prefix24: str
    recent_hours: int = Field(default=24, ge=1, le=168, description="查找最近 N 小时的 Ping 数据")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class HierarchicalAnalysisRequest(BaseModel):
    """分层分析请求"""
    region: str
    hierarchy: List[str] = Field(default=["time", "asgeo", "prefix24"], description="层级顺序")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    percentiles: List[int] = Field(default=[50, 90, 95, 99])
    outlier_filter_min: Optional[float] = Field(default=None, ge=0, le=100)
    outlier_filter_max: Optional[float] = Field(default=None, ge=0, le=100)
    asn: Optional[int] = None
    country: Optional[str] = None


class DrillDownRequest(BaseModel):
    """下钻分析请求"""
    region: str
    level: str = Field(..., description="当前层级: overall, asn, asgeo, prefix24, country")
    level_value: Optional[str] = Field(default=None, description="当前层级的值，overall 层级可为空")
    next_level: str = Field(..., description="下一层级")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    percentiles: List[int] = Field(default=[50, 90, 95, 99])


# ===== API 端点 =====

@router.get("/regions")
async def list_regions():
    """获取所有地区列表"""
    try:
        client = get_clickhouse_client()
        regions = client.get_regions()

        region_infos = []
        for region in regions:
            info = client.get_region_info(region)
            if info:
                region_infos.append(info.to_dict())

        return {
            "success": True,
            "regions": region_infos,
            "total": len(region_infos),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regions/{region}")
async def get_region_detail(region: str):
    """获取地区详细信息"""
    try:
        client = get_clickhouse_client()
        info = client.get_region_info(region)

        if not info:
            raise HTTPException(status_code=404, detail=f"Region {region} not found")

        return {
            "success": True,
            "region": info.to_dict(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ping/stats", response_model=PingStatsResponse)
async def query_ping_stats(request: PingStatsRequest):
    """查询 Ping 统计数据"""
    try:
        client = get_clickhouse_client()

        filters = QueryFilters(
            region=request.region,
            start_time=request.start_time,
            end_time=request.end_time,
            asn=request.asn,
            prefix24=request.prefix24,
            data_center=request.data_center,
            ip_geo_country=request.country,
            isp_domain=request.isp,
            limit=request.limit,
        )

        # 获取总体统计
        overall_stats = client.query_ping_stats(filters)

        # 获取分组统计
        grouped_stats = None
        if request.group_by:
            grouped_stats = client.query_ping_stats(filters, request.group_by)

        return PingStatsResponse(
            success=True,
            region=request.region,
            total_samples=overall_stats[0].get('sample_count', 0) if overall_stats else 0,
            statistics=overall_stats[0] if overall_stats else {},
            grouped_stats=grouped_stats,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ping/trend", response_model=TimeSeriesResponse)
async def query_ping_trend(request: TimeSeriesRequest):
    """查询 Ping 时间趋势"""
    try:
        client = get_clickhouse_client()

        filters = QueryFilters(
            region=request.region,
            start_time=request.start_time,
            end_time=request.end_time,
            asn=request.asn,
            isp_domain=request.isp,
            limit=request.limit,
        )

        trend_data = client.query_ping_trend(filters, request.interval)

        return TimeSeriesResponse(
            success=True,
            region=request.region,
            interval=request.interval,
            data=trend_data,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trace/stats", response_model=PathStatsResponse)
async def query_trace_stats(request: PathStatsRequest):
    """查询 Traceroute 统计数据"""
    try:
        client = get_clickhouse_client()

        filters = QueryFilters(
            region=request.region,
            start_time=request.start_time,
            end_time=request.end_time,
            limit=request.limit,
        )

        # 获取路径统计
        path_stats = client.query_path_stats(filters)

        # 获取总体统计
        overall_stats = client.query_path_stats(filters, group_by_path=False)

        total_traces = overall_stats[0].get('total_traces', 0) if overall_stats else 0
        unique_paths = overall_stats[0].get('unique_paths', 0) if overall_stats else 0

        return PathStatsResponse(
            success=True,
            region=request.region,
            total_traces=total_traces,
            unique_paths=unique_paths,
            top_paths=path_stats,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trace/paths-to-asn")
async def find_paths_to_asn(
    region: str,
    target_asn: int,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(default=100, ge=1, le=1000)
):
    """查找到特定 AS 的路径"""
    try:
        client = get_clickhouse_client()

        filters = QueryFilters(
            region=region,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

        paths = client.query_paths_to_target(filters, target_asn)

        return {
            "success": True,
            "region": region,
            "target_asn": target_asn,
            "paths": paths,
            "total": len(paths),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/correlation", response_model=CorrelationResponse)
async def query_correlation(request: CorrelationRequest):
    """关联查询 Ping 和 Traceroute 数据"""
    try:
        client = get_clickhouse_client()

        filters = QueryFilters(
            region=request.region,
            start_time=request.start_time,
            end_time=request.end_time,
        )

        result = client.query_ping_trace_correlation(filters, request.prefix24)

        return CorrelationResponse(
            success=True,
            prefix24=request.prefix24,
            ping_stats=result['ping_stats'],
            trace_paths=result['trace_paths'],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== 增强版分析端点 =====

@router.post("/ping/analyze")
async def analyze_ping_data(request: EnhancedPingStatsRequest):
    """
    增强版 Ping 数据分析

    支持多种分析维度:
    - overall: 整体统计
    - asn: 按 AS 分析
    - asgeo: 按 AS+Geo 分析
    - country: 按国家分析
    - region: 按地区分析
    - data_center: 按数据中心分析
    - prefix24: 按 /24 前缀分析
    - time_trend: 时间趋势分析
    """
    try:
        client = get_clickhouse_client()
        analyzer = PingAnalyzer(client.client)

        config = AnalysisConfig(
            percentiles=request.percentiles,
            include_stats=True,
            include_distribution=True,
            outlier_filter_min=request.outlier_filter_min,
            outlier_filter_max=request.outlier_filter_max,
        )

        filters = {}
        if request.asn:
            filters['ip_asn'] = request.asn
        if request.prefix24:
            filters['prefix24'] = request.prefix24
        if request.data_center:
            filters['data_center'] = request.data_center
        if request.country:
            filters['ip_geo_country'] = request.country
        if request.isp:
            filters['ip_isp_domain'] = request.isp

        # 处理 asgeo 筛选 - 解析为 asn 和 country
        # ASGeo 格式: AS198227_乌克兰
        if request.asgeo:
            asgeo_value = request.asgeo.replace('AS', '')
            parts = asgeo_value.split('_', 1)
            if len(parts) >= 1 and parts[0].isdigit():
                filters['ip_asn'] = int(parts[0])
            if len(parts) >= 2:
                filters['ip_geo_country'] = parts[1]

        result = None

        if request.analysis_dimension == 'overall':
            result = analyzer.analyze_overall(
                region=request.region,
                start_time=request.start_time,
                end_time=request.end_time,
                config=config,
                **filters
            )
            result['dimension'] = 'overall'

        elif request.analysis_dimension == 'asn':
            result = analyzer.analyze_by_asn(
                region=request.region,
                top_n=request.top_n,
                start_time=request.start_time,
                end_time=request.end_time,
                config=config,
                **filters
            )

        elif request.analysis_dimension == 'asgeo':
            result = analyzer.analyze_by_asgeo(
                region=request.region,
                top_n=request.top_n,
                start_time=request.start_time,
                end_time=request.end_time,
                config=config,
                **filters
            )

        elif request.analysis_dimension == 'country':
            result = analyzer.analyze_by_country(
                region=request.region,
                top_n=request.top_n,
                start_time=request.start_time,
                end_time=request.end_time,
                config=config,
                **filters
            )

        elif request.analysis_dimension == 'data_center':
            result = analyzer.analyze_by_data_center(
                region=request.region,
                start_time=request.start_time,
                end_time=request.end_time,
                config=config,
                **filters
            )

        elif request.analysis_dimension == 'time_trend':
            result = analyzer.analyze_time_trend(
                region=request.region,
                interval=request.interval,
                start_time=request.start_time,
                end_time=request.end_time,
                config=config,
                **filters
            )

        else:
            # 默认返回整体统计
            result = analyzer.analyze_overall(
                region=request.region,
                start_time=request.start_time,
                end_time=request.end_time,
                config=config,
                **filters
            )
            result['dimension'] = 'overall'

        return {
            "success": True,
            "region": request.region,
            "dimension": request.analysis_dimension,
            "percentiles": request.percentiles,
            "statistics": result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ping/anomalies")
async def detect_ping_anomalies(request: AnomalyDetectionRequest):
    """
    Ping 数据异常检测

    检测 RTT 异常值（基于标准差）
    """
    try:
        client = get_clickhouse_client()
        analyzer = PingAnalyzer(client.client)

        filters = {}
        if request.asn:
            filters['ip_asn'] = request.asn
        if request.prefix24:
            filters['prefix24'] = request.prefix24

        result = analyzer.detect_anomalies(
            region=request.region,
            threshold_std=request.threshold_std,
            start_time=request.start_time,
            end_time=request.end_time,
            **filters
        )

        return {
            "success": True,
            "region": request.region,
            "threshold_std": request.threshold_std,
            **result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trace/analyze")
async def analyze_trace_data(request: EnhancedTraceStatsRequest):
    """
    增强版 Traceroute 数据分析

    支持多种分析:
    - 路径统计（IP路径、AS路径、ASGeo路径）
    - 到特定 AS 的路径分析
    - 跳数分布分析
    """
    try:
        client = get_clickhouse_client()
        analyzer = TracerouteAnalyzer(client.client)

        if request.target_asn:
            # 分析到特定 AS 的路径
            result = analyzer.analyze_paths_to_target(
                region=request.region,
                target_asn=request.target_asn,
                start_time=request.start_time,
                end_time=request.end_time,
                top_n=request.top_n,
            )
            return {
                "success": True,
                "region": request.region,
                "analysis_type": "paths_to_target",
                "target_asn": request.target_asn,
                "paths": result,
                "total_paths": len(result),
            }

        elif request.prefix24:
            # 分析路径-Ping 关联
            result = analyzer.analyze_path_ping_correlation(
                region=request.region,
                prefix24=request.prefix24,
                start_time=request.start_time,
                end_time=request.end_time,
            )
            return {
                "success": True,
                "region": request.region,
                "analysis_type": "path_ping_correlation",
                **result,
            }

        else:
            # 路径统计分析
            result = analyzer.analyze_path_statistics(
                region=request.region,
                path_type=request.path_type,
                start_time=request.start_time,
                end_time=request.end_time,
                top_n=request.top_n,
            )

            # 获取跳数分布
            hop_distribution = analyzer.analyze_hop_distribution(
                region=request.region,
                start_time=request.start_time,
                end_time=request.end_time,
            )

            return {
                "success": True,
                "region": request.region,
                "path_type": request.path_type,
                "paths": result,
                "total_paths": len(result),
                "hop_distribution": hop_distribution,
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare/regions")
async def compare_regions(
    regions: List[str],
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    percentiles: List[int] = Query(default=[50, 90, 95, 99])
):
    """
    多地区对比分析
    """
    try:
        client = get_clickhouse_client()
        analyzer = PingAnalyzer(client.client)

        config = AnalysisConfig(percentiles=percentiles)

        results = {}
        for region in regions:
            try:
                stats = analyzer.analyze_overall(
                    region=region,
                    start_time=start_time,
                    end_time=end_time,
                    config=config,
                )
                results[region] = stats
            except Exception as e:
                results[region] = {"error": str(e)}

        return {
            "success": True,
            "regions": regions,
            "comparison": results,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare/asns")
async def compare_asns(
    region: str,
    asns: List[int],
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    percentiles: List[int] = Query(default=[50, 90, 95, 99])
):
    """
    多 AS 对比分析
    """
    try:
        client = get_clickhouse_client()
        analyzer = PingAnalyzer(client.client)

        config = AnalysisConfig(percentiles=percentiles)

        results = {}
        for asn in asns:
            try:
                stats = analyzer.analyze_overall(
                    region=region,
                    start_time=start_time,
                    end_time=end_time,
                    config=config,
                    ip_asn=asn,
                )
                results[f"AS{asn}"] = stats
            except Exception as e:
                results[f"AS{asn}"] = {"error": str(e)}

        return {
            "success": True,
            "region": region,
            "asns": asns,
            "comparison": results,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata/asns")
async def list_available_asns(
    region: str,
    search: Optional[str] = Query(default=None, description="模糊搜索 AS 号或名称"),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """获取地区可用的 AS 列表，支持模糊搜索"""
    try:
        client = get_clickhouse_client()
        asns = client.get_available_asns(region, limit, search)

        return {
            "success": True,
            "region": region,
            "asns": asns,
            "total": len(asns),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata/countries")
async def list_available_countries(
    region: str,
    search: Optional[str] = Query(default=None, description="模糊搜索国家代码或名称"),
    limit: int = Query(default=50, ge=1, le=200)
):
    """获取地区可用的国家列表，支持模糊搜索"""
    try:
        client = get_clickhouse_client()
        countries = client.get_available_countries(region, limit, search)

        return {
            "success": True,
            "region": region,
            "countries": countries,
            "total": len(countries),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata/asgeos")
async def list_available_asgeos(
    region: str,
    search: Optional[str] = Query(default=None, description="模糊搜索 ASGeo"),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """获取地区可用的 ASGeo 列表（AS+Geo 组合），支持模糊搜索"""
    try:
        client = get_clickhouse_client()
        asgeos = client.get_available_asgeos(region, limit, search)

        return {
            "success": True,
            "region": region,
            "asgeos": asgeos,
            "total": len(asgeos),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata/data-centers")
async def list_available_data_centers(
    region: str,
    search: Optional[str] = Query(default=None, description="模糊搜索数据中心"),
    limit: int = Query(default=50, ge=1, le=200)
):
    """获取地区可用的数据中心列表，支持模糊搜索"""
    try:
        client = get_clickhouse_client()
        data_centers = client.get_available_data_centers(region, limit, search)

        return {
            "success": True,
            "region": region,
            "data_centers": data_centers,
            "total": len(data_centers),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata/prefix24s")
async def list_available_prefix24s(
    region: str,
    search: Optional[str] = Query(default=None, description="模糊搜索前缀"),
    asn: Optional[int] = Query(default=None, description="按 AS 号过滤"),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """获取地区可用的 /24 前缀列表，支持模糊搜索和按 AS 过滤"""
    try:
        client = get_clickhouse_client()
        prefix24s = client.get_available_prefix24s(region, limit, search, asn)

        return {
            "success": True,
            "region": region,
            "prefix24s": prefix24s,
            "total": len(prefix24s),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata/isps")
async def list_available_isps(
    region: str,
    search: Optional[str] = Query(default=None, description="模糊搜索 ISP 名称"),
    limit: int = Query(default=100, ge=1, le=500)
):
    """获取地区可用的 ISP（运营商）列表，支持模糊搜索"""
    try:
        client = get_clickhouse_client()
        isps = client.get_available_isps(region, limit, search)

        return {
            "success": True,
            "region": region,
            "isps": isps,
            "total": len(isps),
        }
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


@router.get("/metadata/time-range")
async def get_time_range(region: str):
    """获取地区数据的时间范围"""
    try:
        client = get_clickhouse_client()
        min_time, max_time = client.get_time_range(region)

        return {
            "success": True,
            "region": region,
            "min_time": min_time.isoformat() if min_time else None,
            "max_time": max_time.isoformat() if max_time else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ip-mapping/{ip}")
async def get_ip_mapping(ip: str):
    """查询单个 IP 的映射信息"""
    try:
        client = get_clickhouse_client()
        mapping = client.query_ip_mapping(ip)

        if not mapping:
            raise HTTPException(status_code=404, detail=f"IP {ip} not found")

        return {
            "success": True,
            "ip": ip,
            "mapping": mapping.__dict__,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Traceroute 深度分析端点 =====

@router.post("/trace/terminal-analysis")
async def analyze_terminal_nodes(request: TerminalAnalysisRequest):
    """
    末端 AS/ASGeo 节点分析

    分析所有末端节点（terminal AS/ASGeo）的分布情况:
    - 每个末端节点的路径数量
    - 末端节点包含的 prefix24 数量
    - 示例路径
    """
    try:
        client = get_clickhouse_client()
        analyzer = TracerouteAnalyzer(client.client)

        result = analyzer.analyze_terminal_nodes(
            region=request.region,
            terminal_type=request.terminal_type,
            start_time=request.start_time,
            end_time=request.end_time,
            top_n=request.top_n,
            include_paths=request.include_paths,
            terminal_filter=request.terminal_filter,
            data_center=request.data_center,
            trace_type=request.trace_type,
        )

        # 获取数据源信息
        data_source_info = analyzer.get_data_source_info(request.region)

        return {
            "success": True,
            "region": request.region,
            "terminal_type": request.terminal_type,
            "data_source": data_source_info.get('data_source', 'unknown'),
            "sampling_rate": data_source_info.get('sampling_rate', 0),
            **result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trace/terminal/{terminal}/prefix24s")
async def get_terminal_prefix24s(
    terminal: str,
    region: str,
    terminal_type: str = Query(default="asgeo", description="as 或 asgeo"),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    top_n: int = Query(default=100, ge=1, le=500)
):
    """
    获取末端节点的所有 Prefix24

    返回末端 ASGeo 下的所有 /24 前缀及其关联的 Ping 数据:
    - 每个 prefix24 的 traceroute 样本数
    - 关联的 Ping RTT 统计
    - 示例路径
    """
    try:
        client = get_clickhouse_client()
        analyzer = TracerouteAnalyzer(client.client)

        prefix24s = analyzer.get_prefix24s_in_terminal(
            region=region,
            terminal=terminal,
            terminal_type=terminal_type,
            start_time=start_time,
            end_time=end_time,
            top_n=top_n,
        )

        return {
            "success": True,
            "region": region,
            "terminal": terminal,
            "terminal_type": terminal_type,
            "prefix24s": prefix24s,
            "total_prefixes": len(prefix24s),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trace/ping-correlation")
async def get_ping_trace_correlation(request: PingTraceCorrelationRequest):
    """
    Ping-Trace 关联分析

    通过 prefix24 关联 Traceroute 路径和 Ping 数据:
    - Traceroute 数据 (1/4 抽样)
    - Ping 数据 (全量)
    - 关联的 AS/Geo 信息
    """
    try:
        client = get_clickhouse_client()
        analyzer = TracerouteAnalyzer(client.client)

        result = analyzer.correlate_ping_trace(
            region=request.region,
            prefix24=request.prefix24,
            recent_hours=request.recent_hours,
            start_time=request.start_time,
            end_time=request.end_time,
        )

        return {
            "success": True,
            **result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traceroute/data-centers")
async def get_traceroute_data_centers(region: str):
    """
    获取 Traceroute 数据中的数据中心列表

    用于 Traceroute 分析的数据中心筛选下拉框。
    """
    try:
        client = get_clickhouse_client()

        # 查询 traceroute 表中的数据中心
        query = f"""
        SELECT DISTINCT data_center
        FROM {region}__quarter_traceroute
        WHERE data_center != ''
        ORDER BY data_center
        """
        result = client.client.execute(query)
        data_centers = [row[0] for row in result]

        # 同时查询全量表（如果存在）
        try:
            query_full = f"""
            SELECT DISTINCT data_center
            FROM {region}__traceroute
            WHERE data_center != ''
            ORDER BY data_center
            """
            result_full = client.client.execute(query_full)
            data_centers_full = [row[0] for row in result_full]
            # 合并去重
            all_data_centers = sorted(set(data_centers + data_centers_full))
        except:
            all_data_centers = data_centers

        return {
            "success": True,
            "region": region,
            "data_centers": all_data_centers,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trace/data-source")
async def get_trace_data_source_info(region: str):
    """
    获取 Traceroute 数据源信息

    返回数据源类型:
    - full: 全量数据
    - quarter: 1/4 抽样数据
    """
    try:
        client = get_clickhouse_client()
        analyzer = TracerouteAnalyzer(client.client)

        info = analyzer.get_data_source_info(region)

        return {
            "success": True,
            "region": region,
            **info,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hierarchical-analysis")
async def hierarchical_analysis(request: HierarchicalAnalysisRequest):
    """
    分层分析 - 支持逐层下钻

    按照指定的层级顺序进行聚合统计，支持极端值过滤。

    层级选项:
    - time: 时间维度 (按小时)
    - asn: AS 维度
    - asgeo: AS+Geo 维度
    - prefix24: /24 前缀维度
    - country: 国家维度

    示例:
    ```
    {
        "region": "UKRAINE",
        "hierarchy": ["time", "asgeo", "prefix24"],
        "outlier_filter_min": 5,
        "outlier_filter_max": 95
    }
    ```

    返回:
    - flat_data: 扁平化的聚合结果列表
    - hierarchy_tree: 树形结构的聚合结果
    """
    try:
        client = get_clickhouse_client()
        analyzer = PingAnalyzer(client.client)

        config = AnalysisConfig(percentiles=request.percentiles)

        outlier_filter = None
        if request.outlier_filter_min is not None or request.outlier_filter_max is not None:
            outlier_filter = {
                'percentile_min': request.outlier_filter_min or 0,
                'percentile_max': request.outlier_filter_max or 100,
            }

        filters = {}
        if request.asn:
            filters['ip_asn'] = request.asn
        if request.country:
            filters['ip_geo_country'] = request.country

        result = analyzer.hierarchical_analysis(
            region=request.region,
            hierarchy=request.hierarchy,
            start_time=request.start_time,
            end_time=request.end_time,
            config=config,
            outlier_filter=outlier_filter,
            **filters
        )

        return {
            "success": True,
            "region": request.region,
            **result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drill-down")
async def drill_down_analysis(request: DrillDownRequest):
    """
    下钻分析 - 从一个层级钻取到下一层级

    用于交互式分层分析，点击某个层级节点后获取下一层级的详细数据。

    示例:
    ```
    {
        "region": "UKRAINE",
        "level": "asgeo",
        "level_value": "1234_US",
        "next_level": "prefix24"
    }
    ```

    返回:
    - children: 下一层级的聚合统计列表
    """
    try:
        client = get_clickhouse_client()
        analyzer = PingAnalyzer(client.client)

        config = AnalysisConfig(percentiles=request.percentiles)

        result = analyzer.drill_down(
            region=request.region,
            level=request.level,
            level_value=request.level_value,
            next_level=request.next_level,
            start_time=request.start_time,
            end_time=request.end_time,
            config=config,
        )

        return {
            "success": True,
            "region": request.region,
            **result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== 末端 AS/ASGeo 列表端点 =====

class TerminalListRequest(BaseModel):
    """末端节点列表请求"""
    region: str
    terminal_type: str = Field(default="asgeo", description="as 或 asgeo")
    search: Optional[str] = Field(default=None, description="模糊搜索关键词")
    limit: int = Field(default=100, ge=1, le=500)


@router.post("/trace/terminals/list")
async def list_available_terminals(request: TerminalListRequest):
    """
    获取可用的末端 AS/ASGeo 列表（支持模糊搜索）

    用于下拉框选择，支持按 AS 号或地理位置模糊搜索。
    """
    try:
        client = get_clickhouse_client()
        analyzer = TracerouteAnalyzer(client.client)

        terminals = analyzer.list_terminals(
            region=request.region,
            terminal_type=request.terminal_type,
            search=request.search,
            limit=request.limit,
        )

        return {
            "success": True,
            "region": request.region,
            "terminal_type": request.terminal_type,
            "terminals": terminals,
            "total": len(terminals),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== AS 路径分析增强端点 =====

class ASPathAnalysisRequest(BaseModel):
    """AS 路径分析请求"""
    region: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    path_type: str = Field(default="as", description="as 或 asgeo")
    terminal_as: Optional[str] = Field(default=None, description="限定末端 AS，如 AS12345")
    terminal_asgeo: Optional[str] = Field(default=None, description="限定末端 ASGeo，如 AS12345-US")
    top_n: int = Field(default=50, ge=1, le=500)
    # 新增：数据中心筛选
    data_center: Optional[str] = Field(default=None, description="数据中心筛选")
    # 新增：数据类型
    trace_type: str = Field(default="quarter", description="quarter 或 full")


@router.post("/trace/paths/analysis")
async def analyze_as_paths(request: ASPathAnalysisRequest):
    """
    AS 路径深度分析

    支持:
    - AS 路径或 ASGeo 路径分析
    - 按末端 AS 或 ASGeo 过滤
    - 路径统计和可视化数据
    """
    try:
        client = get_clickhouse_client()
        analyzer = TracerouteAnalyzer(client.client)

        result = analyzer.analyze_paths_with_filter(
            region=request.region,
            path_type=request.path_type,
            terminal_as=request.terminal_as,
            terminal_asgeo=request.terminal_asgeo,
            start_time=request.start_time,
            end_time=request.end_time,
            top_n=request.top_n,
            data_center=request.data_center,
            trace_type=request.trace_type,
        )

        return {
            "success": True,
            "region": request.region,
            "path_type": request.path_type,
            **result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== 路径搜索端点 =====

class PathListRequest(BaseModel):
    """路径搜索请求"""
    region: str
    path_type: str = Field(default="as", description="as 或 asgeo")
    search: Optional[str] = Field(default=None, description="路径搜索关键词")
    limit: int = Field(default=50, ge=1, le=200)


class PathListItem(BaseModel):
    """路径列表项"""
    path: str
    trace_count: int
    reach_rate: float


@router.post("/trace/paths/list")
async def list_paths(request: PathListRequest):
    """
    搜索路径列表（用于下拉搜索）

    返回匹配的路径及其基本统计
    """
    try:
        client = get_clickhouse_client()
        analyzer = TracerouteAnalyzer(client.client)

        result = analyzer.search_paths(
            region=request.region,
            path_type=request.path_type,
            search=request.search,
            limit=request.limit,
        )

        return {
            "success": True,
            "region": request.region,
            "path_type": request.path_type,
            "paths": result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== 路径详情分析端点 =====

class PathDetailRequest(BaseModel):
    """路径详情请求"""
    region: str
    path: str = Field(..., description="AS 路径或 ASGeo 路径字符串")
    path_type: str = Field(default="as", description="as 或 asgeo")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    top_n: int = Field(default=50, ge=1, le=500)


class PathPingTrendRequest(BaseModel):
    """路径 Ping 时序分析请求"""
    region: str
    path: str = Field(..., description="AS 路径或 ASGeo 路径字符串")
    path_type: str = Field(default="as", description="as 或 asgeo")
    interval: str = Field(default="hour", description="minute, hour, day")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    percentiles: List[int] = Field(default=[50, 90, 95, 99])
    # 筛选参数
    asn: Optional[int] = Field(default=None, description="AS 号筛选")
    asgeo: Optional[str] = Field(default=None, description="ASGeo 筛选 (格式: ASN_Country)")
    isp: Optional[str] = Field(default=None, description="运营商筛选")
    data_center: Optional[str] = Field(default=None, description="数据中心筛选")
    # 极端值过滤
    outlier_filter_min: Optional[int] = Field(default=None, description="极端值过滤下界分位数")
    outlier_filter_max: Optional[int] = Field(default=None, description="极端值过滤上界分位数")


class PathFilterOptionsRequest(BaseModel):
    """路径筛选选项请求"""
    region: str
    path: str = Field(..., description="AS 路径或 ASGeo 路径字符串")
    path_type: str = Field(default="as", description="as 或 asgeo")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


@router.post("/trace/path/filter-options")
async def get_path_filter_options(request: PathFilterOptionsRequest):
    """
    获取路径关联的筛选选项

    返回这条路径包含的:
    - AS 选项
    - ASGeo 选项
    - 运营商选项
    - 数据中心选项
    - Prefix24 选项
    """
    try:
        client = get_clickhouse_client()
        analyzer = TracerouteAnalyzer(client.client)

        result = analyzer.get_path_filter_options(
            region=request.region,
            path=request.path,
            path_type=request.path_type,
            start_time=request.start_time,
            end_time=request.end_time,
        )

        return {
            "success": True,
            "region": request.region,
            **result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trace/path/detail")
async def get_path_detail(request: PathDetailRequest):
    """
    获取路径详情

    返回该路径关联的:
    - 所有末端节点 (terminal AS/ASGeo) 及其统计
    - 所有 prefix24 及其统计
    - 数据中心分布
    """
    try:
        client = get_clickhouse_client()
        analyzer = TracerouteAnalyzer(client.client)

        result = analyzer.get_path_detail(
            region=request.region,
            path=request.path,
            path_type=request.path_type,
            start_time=request.start_time,
            end_time=request.end_time,
            top_n=request.top_n,
        )

        return {
            "success": True,
            "region": request.region,
            **result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trace/path/ping-trend")
async def get_path_ping_trend(request: PathPingTrendRequest):
    """
    获取路径关联的 Ping 时序数据

    通过路径关联的所有 prefix24 查询 Ping 时序统计:
    - 按时间粒度聚合
    - 返回 RTT 统计和分位数
    - 支持按 AS/ASGeo/运营商/数据中心筛选
    - 支持极端值过滤
    """
    try:
        client = get_clickhouse_client()
        analyzer = TracerouteAnalyzer(client.client)

        result = analyzer.analyze_path_ping_trend(
            region=request.region,
            path=request.path,
            path_type=request.path_type,
            interval=request.interval,
            start_time=request.start_time,
            end_time=request.end_time,
            percentiles=request.percentiles,
            asn=request.asn,
            asgeo=request.asgeo,
            isp=request.isp,
            data_center=request.data_center,
            outlier_filter_min=request.outlier_filter_min,
            outlier_filter_max=request.outlier_filter_max,
        )

        return {
            "success": True,
            "region": request.region,
            **result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Geo 维度分析端点 =====

class GeoAnalysisRequest(BaseModel):
    """Geo 分析请求"""
    region: str
    country: str = Field(..., description="国家代码，如 US, CN, UA")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)


@router.post("/metadata/geo/asns")
async def get_asns_by_geo(request: GeoAnalysisRequest):
    """
    获取特定国家/地区下的所有 AS

    返回该国家/地区下按样本数排序的 AS 列表
    """
    try:
        client = get_clickhouse_client()
        table_name = f"{request.region}__ping"

        time_filter = ""
        params: Dict[str, Any] = {'country': request.country, 'limit': request.limit}

        if request.start_time:
            time_filter += " AND measure_time >= %(start_time)s"
            params['start_time'] = request.start_time
        if request.end_time:
            time_filter += " AND measure_time <= %(end_time)s"
            params['end_time'] = request.end_time

        query = f"""
        SELECT
            ip_asn,
            ip_as_name,
            count() as sample_count,
            uniqExact(dst_ip) as unique_ips,
            uniqExact(prefix24) as prefix24_count
        FROM {table_name}
        WHERE ip_geo_country = %(country)s AND ip_asn > 0 {time_filter}
        GROUP BY ip_asn, ip_as_name
        ORDER BY sample_count DESC
        LIMIT %(limit)s
        """

        result = client.execute(query, params)

        return {
            "success": True,
            "region": request.region,
            "country": request.country,
            "asns": [
                {
                    "asn": row[0],
                    "as_name": row[1] or f"AS{row[0]}",
                    "sample_count": row[2],
                    "unique_ips": row[3],
                    "prefix24_count": row[4],
                    "display": f"AS{row[0]} - {row[1] or 'Unknown'}"
                }
                for row in result
            ],
            "total": len(result),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/metadata/geo/asgeos")
async def get_asgeos_by_geo(request: GeoAnalysisRequest):
    """
    获取特定国家/地区下的所有 ASGeo

    返回该国家/地区下按样本数排序的 ASGeo 列表
    """
    try:
        client = get_clickhouse_client()
        table_name = f"{request.region}__ping"

        time_filter = ""
        params: Dict[str, Any] = {'country': request.country, 'limit': request.limit}

        if request.start_time:
            time_filter += " AND measure_time >= %(start_time)s"
            params['start_time'] = request.start_time
        if request.end_time:
            time_filter += " AND measure_time <= %(end_time)s"
            params['end_time'] = request.end_time

        query = f"""
        SELECT
            concat('AS', toString(ip_asn), '_', ip_geo_country) as asgeo,
            ip_asn,
            ip_geo_country,
            ip_as_name,
            count() as sample_count,
            uniqExact(dst_ip) as unique_ips,
            uniqExact(prefix24) as prefix24_count
        FROM {table_name}
        WHERE ip_geo_country = %(country)s AND ip_asn > 0 {time_filter}
        GROUP BY asgeo, ip_asn, ip_geo_country, ip_as_name
        ORDER BY sample_count DESC
        LIMIT %(limit)s
        """

        result = client.execute(query, params)

        return {
            "success": True,
            "region": request.region,
            "country": request.country,
            "asgeos": [
                {
                    "asgeo": row[0],
                    "asn": row[1],
                    "country": row[2],
                    "as_name": row[3] or f"AS{row[1]}",
                    "sample_count": row[4],
                    "unique_ips": row[5],
                    "prefix24_count": row[6],
                }
                for row in result
            ],
            "total": len(result),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AsnPrefixExportRequest(BaseModel):
    """AS 前缀导出请求"""
    region: str
    asn: Optional[int] = None
    asgeo: Optional[str] = None
    country: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=500, ge=1, le=5000)


@router.post("/metadata/export/prefix24s")
async def export_prefix24s(request: AsnPrefixExportRequest):
    """
    导出 AS/ASGeo/国家下的所有 prefix24

    支持按 AS、ASGeo 或国家过滤，返回 CSV 格式数据
    """
    try:
        client = get_clickhouse_client()
        table_name = f"{request.region}__ping"

        where_conditions = ["prefix24 != ''"]
        params: Dict[str, Any] = {'limit': request.limit}

        if request.asn:
            where_conditions.append("ip_asn = %(asn)s")
            params['asn'] = request.asn

        if request.asgeo:
            # 解析 ASGeo: AS12345_US -> asn=12345, country=US
            asgeo_parts = request.asgeo.replace('AS', '').split('_')
            if len(asgeo_parts) >= 2:
                params['asn'] = int(asgeo_parts[0])
                params['country_code'] = asgeo_parts[1]
                where_conditions.append("ip_asn = %(asn)s AND ip_geo_country = %(country_code)s")

        if request.country:
            where_conditions.append("ip_geo_country = %(country)s")
            params['country'] = request.country

        if request.start_time:
            where_conditions.append("measure_time >= %(start_time)s")
            params['start_time'] = request.start_time
        if request.end_time:
            where_conditions.append("measure_time <= %(end_time)s")
            params['end_time'] = request.end_time

        where_clause = " AND ".join(where_conditions)

        query = f"""
        SELECT
            prefix24,
            ip_asn,
            ip_as_name,
            ip_geo_country,
            ip_geo_city,
            count() as sample_count,
            uniqExact(dst_ip) as unique_ips,
            avg(rtt_ms) as avg_rtt,
            median(rtt_ms) as median_rtt,
            quantile(0.95)(rtt_ms) as p95_rtt
        FROM {table_name}
        WHERE {where_clause}
        GROUP BY prefix24, ip_asn, ip_as_name, ip_geo_country, ip_geo_city
        ORDER BY sample_count DESC
        LIMIT %(limit)s
        """

        result = client.execute(query, params)

        return {
            "success": True,
            "region": request.region,
            "filter": {
                "asn": request.asn,
                "asgeo": request.asgeo,
                "country": request.country,
            },
            "prefix24s": [
                {
                    "prefix24": row[0],
                    "asn": row[1],
                    "as_name": row[2] or f"AS{row[1]}",
                    "country": row[3],
                    "city": row[4],
                    "sample_count": row[5],
                    "unique_ips": row[6],
                    "avg_rtt": round(row[7], 2) if row[7] else None,
                    "median_rtt": round(row[8], 2) if row[8] else None,
                    "p95_rtt": round(row[9], 2) if row[9] else None,
                }
                for row in result
            ],
            "total": len(result),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata/countries/list")
async def list_countries_in_region(
    region: str,
    limit: int = Query(default=100, ge=1, le=500)
):
    """
    获取地区中出现的所有国家列表
    """
    try:
        client = get_clickhouse_client()
        table_name = f"{region}__ping"

        query = f"""
        SELECT
            ip_geo_country,
            count() as sample_count,
            uniqExact(ip_asn) as asn_count,
            uniqExact(prefix24) as prefix24_count
        FROM {table_name}
        WHERE ip_geo_country != ''
        GROUP BY ip_geo_country
        ORDER BY sample_count DESC
        LIMIT %(limit)s
        """

        result = client.execute(query, {'limit': limit})

        return {
            "success": True,
            "region": region,
            "countries": [
                {
                    "country_code": row[0],
                    "sample_count": row[1],
                    "asn_count": row[2],
                    "prefix24_count": row[3],
                }
                for row in result
            ],
            "total": len(result),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata/isps/stats")
async def get_isp_stats(
    region: str,
    limit: int = Query(default=100, ge=1, le=500)
):
    """
    获取地区 ISP 统计排行

    按 AS 聚合统计，因为一个 AS 代表一个 ISP 公司
    返回每个 ISP 的:
    - prefix24 数量 (C段数量)
    - ISP domain 数量
    - 样本数
    - IP 数
    """
    try:
        client = get_clickhouse_client()
        table_name = f"{region}__ping"

        # 按 AS 聚合，统计每个 ISP (AS) 的 C段数、域名数等
        query = f"""
        SELECT
            ip_asn,
            any(ip_as_name) as as_name,
            uniqExact(prefix24) as prefix24_count,
            uniqExact(ip_isp_domain) as isp_domain_count,
            uniqExact(dst_ip) as unique_ips,
            count() as sample_count
        FROM {table_name}
        WHERE ip_asn > 0
        GROUP BY ip_asn
        ORDER BY prefix24_count DESC
        LIMIT %(limit)s
        """

        result = client.execute(query, {'limit': limit})

        return {
            "success": True,
            "region": region,
            "isps": [
                {
                    "asn": row[0],
                    "as_name": row[1] or f"AS{row[0]}",
                    "prefix24_count": row[2],
                    "isp_domain_count": row[3],
                    "unique_ips": row[4],
                    "sample_count": row[5],
                }
                for row in result
            ],
            "total": len(result),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class IspDetailRequest(BaseModel):
    """ISP 详情请求"""
    region: str
    asn: int  # 改为 asn，因为 ISP 按 AS 聚合
    limit: int = Field(default=500, ge=1, le=5000)


@router.post("/metadata/isp/detail")
async def get_isp_detail(request: IspDetailRequest):
    """
    获取 ISP (AS) 详情

    返回该 ISP 下的:
    - 包含的所有 ISP domain 列表
    - 包含的所有 C段 (prefix24) 列表
    - RTT 统计
    """
    try:
        client = get_clickhouse_client()
        table_name = f"{request.region}__ping"

        # 查询 ISP 的 domain 列表
        domain_query = f"""
        SELECT
            ip_isp_domain,
            prefix24,
            count() as sample_count,
            uniqExact(dst_ip) as unique_ips,
            avg(rtt_ms) as avg_rtt
        FROM {table_name}
        WHERE ip_asn = %(asn)s AND ip_isp_domain != ''
        GROUP BY ip_isp_domain, prefix24
        ORDER BY sample_count DESC
        LIMIT 200
        """

        domain_result = client.execute(domain_query, {'asn': request.asn})

        # 查询 ISP 的 prefix24 列表
        prefix_query = f"""
        SELECT
            prefix24,
            ip_isp_domain,
            ip_geo_country,
            ip_geo_city,
            count() as sample_count,
            uniqExact(dst_ip) as unique_ips,
            avg(rtt_ms) as avg_rtt,
            median(rtt_ms) as median_rtt
        FROM {table_name}
        WHERE ip_asn = %(asn)s AND prefix24 != ''
        GROUP BY prefix24, ip_isp_domain, ip_geo_country, ip_geo_city
        ORDER BY sample_count DESC
        LIMIT %(limit)s
        """

        prefix_result = client.execute(prefix_query, {
            'asn': request.asn,
            'limit': request.limit
        })

        return {
            "success": True,
            "region": request.region,
            "asn": request.asn,
            "domain_list": [
                {
                    "isp_domain": row[0],
                    "prefix24": row[1],
                    "sample_count": row[2],
                    "unique_ips": row[3],
                    "avg_rtt": round(row[4], 2) if row[4] else None,
                }
                for row in domain_result
            ],
            "prefix24_list": [
                {
                    "prefix24": row[0],
                    "isp_domain": row[1] or "-",
                    "country": row[2],
                    "city": row[3],
                    "sample_count": row[4],
                    "unique_ips": row[5],
                    "avg_rtt": round(row[6], 2) if row[6] else None,
                    "median_rtt": round(row[7], 2) if row[7] else None,
                }
                for row in prefix_result
            ],
            "total_domains": len(domain_result),
            "total_prefix24": len(prefix_result),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
