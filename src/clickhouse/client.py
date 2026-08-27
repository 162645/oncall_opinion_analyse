"""
ClickHouse 客户端
提供数据库连接和查询功能
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from .models import (
    PingRecord,
    TraceRecord,
    IPMappingRecord,
    ImportFileRecord,
    RegionInfo,
    QueryFilters,
)


@dataclass
class ClickHouseConfig:
    """ClickHouse 配置"""
    host: str = "localhost"
    port: int = 9000
    database: str = "net_measure"
    user: str = "default"
    password: str = ""

    @classmethod
    def from_env(cls) -> 'ClickHouseConfig':
        """从环境变量创建配置"""
        return cls(
            host=os.getenv("CLICKHOUSE_HOST", "localhost"),
            port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
            database=os.getenv("CLICKHOUSE_DATABASE", "net_measure"),
            user=os.getenv("CLICKHOUSE_USER", "default"),
            password=os.getenv("CLICKHOUSE_PASSWORD", ""),
        )


class ClickHouseClient:
    """
    ClickHouse 客户端

    提供网络测量数据的查询功能
    """

    def __init__(self, config: Optional[ClickHouseConfig] = None):
        self.config = config or ClickHouseConfig.from_env()
        self._client = None

    @property
    def client(self):
        """获取底层 ClickHouse 客户端（供分析器使用）"""
        return self._get_client()

    def _get_client(self):
        """获取 ClickHouse 客户端"""
        if self._client is None:
            try:
                from clickhouse_driver import Client
                self._client = Client(
                    host=self.config.host,
                    port=self.config.port,
                    database=self.config.database,
                    user=self.config.user,
                    password=self.config.password,
                )
            except ImportError:
                raise ImportError("请安装 clickhouse-driver: pip install clickhouse-driver")
        return self._client

    def execute(
        self,
        query: str,
        params: Optional[Dict] = None,
        with_column_types: bool = False
    ) -> Any:
        """执行查询"""
        client = self._get_client()
        return client.execute(query, params or {}, with_column_types=with_column_types)

    # ===== 地区和表管理 =====

    def get_regions(self) -> List[str]:
        """获取所有地区列表"""
        query = """
        SELECT DISTINCT target_region
        FROM import_files
        WHERE target_region != ''
        ORDER BY target_region
        """
        result = self.execute(query)
        return [row[0] for row in result]

    def get_region_info(self, region: str) -> Optional[RegionInfo]:
        """获取地区详细信息"""
        # 检查表是否存在
        ping_table = f"{region}__ping"
        trace_table = f"{region}__trace"
        quarter_trace_table = f"{region}__quarter_traceroute"

        info = RegionInfo(
            name=region,
            ping_table=ping_table,
            trace_table=trace_table,
            quarter_trace_table=quarter_trace_table,
        )

        # 获取 ping 表统计
        try:
            ping_stats = self.execute(f"""
                SELECT
                    count() as total_rows,
                    min(measure_time) as min_time,
                    max(measure_time) as max_time,
                    uniqExact(data_center) as dc_count
                FROM {ping_table}
            """)
            if ping_stats:
                info.total_ping_rows = ping_stats[0][0]
                info.min_time = ping_stats[0][1]
                info.max_time = ping_stats[0][2]

            # 获取数据中心列表
            dcs = self.execute(f"""
                SELECT DISTINCT data_center
                FROM {ping_table}
                ORDER BY data_center
            """)
            info.data_centers = [row[0] for row in dcs]
        except Exception:
            pass

        return info

    # ===== Ping 数据查询 =====

    def query_ping_data(
        self,
        filters: QueryFilters,
        columns: Optional[List[str]] = None
    ) -> List[PingRecord]:
        """查询 Ping 数据"""
        table_name = f"{filters.region}__ping"

        if columns is None:
            columns = [
                'cycle_id', 'measure_time', 'data_center', 'prefix24',
                'dst_ip', 'rtt_ms', 'ip_asn', 'ip_as_name',
                'ip_geo_region', 'ip_geo_country', 'ip_geo_city'
            ]

        where_clause, params = filters.to_where_clause()

        query = f"""
        SELECT {', '.join(columns)}
        FROM {table_name}
        WHERE {where_clause}
        ORDER BY measure_time
        LIMIT %(limit)s
        OFFSET %(offset)s
        """

        params['limit'] = filters.limit
        params['offset'] = filters.offset

        result = self.execute(query, params)
        return [PingRecord.from_row(row, columns) for row in result]

    def query_ping_stats(
        self,
        filters: QueryFilters,
        group_by: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        查询 Ping 统计数据

        Args:
            filters: 查询过滤器
            group_by: 分组字段，如 ['ip_asn'] 或 ['ip_geo_country', 'ip_geo_region']
        """
        table_name = f"{filters.region}__ping"
        where_clause, params = filters.to_where_clause()

        if group_by:
            group_cols = ', '.join(group_by)
            query = f"""
            SELECT
                {group_cols},
                count() as sample_count,
                avg(rtt_ms) as mean_rtt,
                median(rtt_ms) as median_rtt,
                min(rtt_ms) as min_rtt,
                max(rtt_ms) as max_rtt,
                stddevPop(rtt_ms) as std_rtt,
                quantile(0.90)(rtt_ms) as p90_rtt,
                quantile(0.95)(rtt_ms) as p95_rtt,
                quantile(0.99)(rtt_ms) as p99_rtt
            FROM {table_name}
            WHERE {where_clause}
            GROUP BY {group_cols}
            ORDER BY sample_count DESC
            LIMIT %(limit)s
            """
        else:
            query = f"""
            SELECT
                count() as sample_count,
                avg(rtt_ms) as mean_rtt,
                median(rtt_ms) as median_rtt,
                min(rtt_ms) as min_rtt,
                max(rtt_ms) as max_rtt,
                stddevPop(rtt_ms) as std_rtt,
                quantile(0.90)(rtt_ms) as p90_rtt,
                quantile(0.95)(rtt_ms) as p95_rtt,
                quantile(0.99)(rtt_ms) as p99_rtt
            FROM {table_name}
            WHERE {where_clause}
            """

        params['limit'] = filters.limit

        result = self.execute(query, params)

        if group_by:
            return [
                dict(zip(group_by + [
                    'sample_count', 'mean_rtt', 'median_rtt', 'min_rtt', 'max_rtt',
                    'std_rtt', 'p90_rtt', 'p95_rtt', 'p99_rtt'
                ], row))
                for row in result
            ]
        else:
            return [dict(zip([
                'sample_count', 'mean_rtt', 'median_rtt', 'min_rtt', 'max_rtt',
                'std_rtt', 'p90_rtt', 'p95_rtt', 'p99_rtt'
            ], result[0]))] if result else []

    def query_ping_trend(
        self,
        filters: QueryFilters,
        interval: str = 'hour'
    ) -> List[Dict[str, Any]]:
        """
        查询 Ping 时间趋势

        Args:
            filters: 查询过滤器
            interval: 时间间隔 (minute, hour, day)
        """
        table_name = f"{filters.region}__ping"
        where_clause, params = filters.to_where_clause()

        interval_func = {
            'minute': 'toStartOfMinute',
            'hour': 'toStartOfHour',
            'day': 'toStartOfDay',
        }.get(interval, 'toStartOfHour')

        query = f"""
        SELECT
            {interval_func}(measure_time) as time_bucket,
            count() as sample_count,
            avg(rtt_ms) as mean_rtt,
            median(rtt_ms) as median_rtt,
            quantile(0.90)(rtt_ms) as p90_rtt,
            quantile(0.95)(rtt_ms) as p95_rtt
        FROM {table_name}
        WHERE {where_clause}
        GROUP BY time_bucket
        ORDER BY time_bucket
        """

        result = self.execute(query, params)
        return [
            {
                'time': row[0],
                'sample_count': row[1],
                'mean_rtt': row[2],
                'median_rtt': row[3],
                'p90_rtt': row[4],
                'p95_rtt': row[5],
            }
            for row in result
        ]

    # ===== Traceroute 数据查询 =====

    def query_traceroute_data(
        self,
        filters: QueryFilters,
        columns: Optional[List[str]] = None
    ) -> List[TraceRecord]:
        """查询 Traceroute 数据"""
        table_name = f"{filters.region}__quarter_traceroute"

        if columns is None:
            columns = [
                'cycle_id', 'measure_time', 'data_center', 'prefix24', 'dst_ip',
                'hop_count', 'ip_path_text', 'as_path_text', 'asgeo_path_text',
                'reached_target'
            ]

        where_clause, params = filters.to_where_clause()

        query = f"""
        SELECT {', '.join(columns)}
        FROM {table_name}
        WHERE {where_clause}
        ORDER BY measure_time
        LIMIT %(limit)s
        OFFSET %(offset)s
        """

        params['limit'] = filters.limit
        params['offset'] = filters.offset

        result = self.execute(query, params)
        return [TraceRecord.from_row(row, columns) for row in result]

    def query_path_stats(
        self,
        filters: QueryFilters,
        group_by_path: bool = True
    ) -> List[Dict[str, Any]]:
        """查询路径统计"""
        table_name = f"{filters.region}__quarter_traceroute"
        where_clause, params = filters.to_where_clause()

        if group_by_path:
            query = f"""
            SELECT
                ip_path_text,
                as_path_text,
                asgeo_path_text,
                ip_path_hash,
                count() as occurrence_count,
                avg(hop_count) as avg_hop_count,
                sum(if(reached_target, 1, 0)) as reached_count
            FROM {table_name}
            WHERE {where_clause}
            GROUP BY ip_path_text, as_path_text, asgeo_path_text, ip_path_hash
            ORDER BY occurrence_count DESC
            LIMIT %(limit)s
            """
        else:
            query = f"""
            SELECT
                count() as total_traces,
                avg(hop_count) as avg_hop_count,
                sum(if(reached_target, 1, 0)) as reached_count,
                uniqExact(ip_path_hash) as unique_paths
            FROM {table_name}
            WHERE {where_clause}
            """

        params['limit'] = filters.limit

        result = self.execute(query, params)

        if group_by_path:
            return [
                {
                    'ip_path_text': row[0],
                    'as_path_text': row[1],
                    'asgeo_path_text': row[2],
                    'ip_path_hash': row[3],
                    'occurrence_count': row[4],
                    'avg_hop_count': row[5],
                    'reached_count': row[6],
                }
                for row in result
            ]
        else:
            return [dict(zip([
                'total_traces', 'avg_hop_count', 'reached_count', 'unique_paths'
            ], result[0]))] if result else []

    def query_paths_to_target(
        self,
        filters: QueryFilters,
        target_asn: int
    ) -> List[Dict[str, Any]]:
        """查询到特定 AS 的路径"""
        table_name = f"{filters.region}__quarter_traceroute"
        where_clause, params = filters.to_where_clause()

        query = f"""
        SELECT
            ip_path_text,
            as_path_text,
            asgeo_path_text,
            count() as occurrence_count
        FROM {table_name}
        WHERE {where_clause}
          AND hasToken(as_path_text, 'AS{target_asn}')
        GROUP BY ip_path_text, as_path_text, asgeo_path_text
        ORDER BY occurrence_count DESC
        LIMIT %(limit)s
        """

        params['limit'] = filters.limit

        result = self.execute(query, params)
        return [
            {
                'ip_path_text': row[0],
                'as_path_text': row[1],
                'asgeo_path_text': row[2],
                'occurrence_count': row[3],
            }
            for row in result
        ]

    # ===== IP 映射查询 =====

    def query_ip_mapping(
        self,
        ip: str
    ) -> Optional[IPMappingRecord]:
        """查询单个 IP 的映射信息"""
        query = """
        SELECT *
        FROM ip_mapping_cache
        WHERE ip = %(ip)s
        LIMIT 1
        """
        result = self.execute(query, {'ip': ip})
        if result:
            # 获取列名
            columns = ['ip', 'ip_num', 'prefix24', 'asn', 'as_name',
                       'geo_latitude', 'geo_longitude', 'geo_region',
                       'geo_country', 'geo_city', 'isp_domain', 'asgeo',
                       'mapping_source', 'updated_at']
            return IPMappingRecord.from_row(result[0], columns)
        return None

    def query_ips_by_asn(
        self,
        asn: int,
        limit: int = 1000
    ) -> List[IPMappingRecord]:
        """查询属于特定 AS 的所有 IP"""
        query = """
        SELECT *
        FROM ip_mapping_cache
        WHERE asn = %(asn)s
        LIMIT %(limit)s
        """
        result = self.execute(query, {'asn': asn, 'limit': limit})
        columns = ['ip', 'ip_num', 'prefix24', 'asn', 'as_name',
                   'geo_latitude', 'geo_longitude', 'geo_region',
                   'geo_country', 'geo_city', 'isp_domain', 'asgeo',
                   'mapping_source', 'updated_at']
        return [IPMappingRecord.from_row(row, columns) for row in result]

    # ===== 关联查询 =====

    def query_ping_trace_correlation(
        self,
        filters: QueryFilters,
        prefix24: str
    ) -> Dict[str, Any]:
        """
        关联查询 Ping 和 Traceroute 数据

        通过 prefix24 关联
        """
        ping_table = f"{filters.region}__ping"
        trace_table = f"{filters.region}__quarter_traceroute"
        where_clause, params = filters.to_where_clause()

        # 查询该 prefix24 的 ping 统计
        ping_query = f"""
        SELECT
            count() as sample_count,
            avg(rtt_ms) as mean_rtt,
            median(rtt_ms) as median_rtt,
            quantile(0.95)(rtt_ms) as p95_rtt
        FROM {ping_table}
        WHERE prefix24 = %(prefix24)s AND {where_clause}
        """

        # 查询该 prefix24 的 trace 统计
        trace_query = f"""
        SELECT
            ip_path_text,
            as_path_text,
            count() as occurrence_count
        FROM {trace_table}
        WHERE prefix24 = %(prefix24)s AND {where_clause}
        GROUP BY ip_path_text, as_path_text
        ORDER BY occurrence_count DESC
        LIMIT 10
        """

        params['prefix24'] = prefix24

        ping_result = self.execute(ping_query, params)
        trace_result = self.execute(trace_query, params)

        return {
            'prefix24': prefix24,
            'ping_stats': {
                'sample_count': ping_result[0][0] if ping_result else 0,
                'mean_rtt': ping_result[0][1] if ping_result else None,
                'median_rtt': ping_result[0][2] if ping_result else None,
                'p95_rtt': ping_result[0][3] if ping_result else None,
            },
            'trace_paths': [
                {
                    'ip_path_text': row[0],
                    'as_path_text': row[1],
                    'occurrence_count': row[2],
                }
                for row in trace_result
            ],
        }

    # ===== 元数据查询 =====

    def get_available_asns(
        self,
        region: str,
        limit: int = 100,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取地区中出现的 AS 列表，支持模糊搜索"""
        table_name = f"{region}__ping"

        search_condition = ""
        params: Dict[str, Any] = {'limit': limit}

        if search:
            search_condition = "AND (toString(ip_asn) LIKE %(search)s OR ip_as_name LIKE %(search)s)"
            params['search'] = f"%{search}%"

        query = f"""
        SELECT
            ip_asn,
            ip_as_name,
            count() as sample_count,
            uniqExact(dst_ip) as unique_ips,
            uniqExact(prefix24) as prefix24_count
        FROM {table_name}
        WHERE ip_asn > 0 {search_condition}
        GROUP BY ip_asn, ip_as_name
        ORDER BY sample_count DESC
        LIMIT %(limit)s
        """

        result = self.execute(query, params)
        return [
            {
                'asn': row[0],
                'as_name': row[1],
                'sample_count': row[2],
                'unique_ips': row[3],
                'prefix24_count': row[4],
                'display': f"AS{row[0]} - {row[1]}" if row[1] else f"AS{row[0]}",
            }
            for row in result
        ]

    def get_available_countries(
        self,
        region: str,
        limit: int = 50,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取地区中出现的国家列表，支持模糊搜索"""
        table_name = f"{region}__ping"

        search_condition = ""
        params: Dict[str, Any] = {'limit': limit}

        if search:
            search_condition = "AND ip_geo_country LIKE %(search)s"
            params['search'] = f"%{search}%"

        query = f"""
        SELECT
            ip_geo_country,
            count() as sample_count
        FROM {table_name}
        WHERE ip_geo_country != '' {search_condition}
        GROUP BY ip_geo_country
        ORDER BY sample_count DESC
        LIMIT %(limit)s
        """

        result = self.execute(query, params)
        return [
            {
                'country': row[0],
                'sample_count': row[1],
            }
            for row in result
        ]

    def get_available_asgeos(
        self,
        region: str,
        limit: int = 100,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取地区中出现的 ASGeo 列表（AS+Geo 组合），支持模糊搜索

        ASGeo 格式: AS{asn}_{country}，如 AS12345_US
        """
        table_name = f"{region}__ping"

        search_condition = ""
        params: Dict[str, Any] = {'limit': limit}

        if search:
            search_condition = "AND (concat('AS', toString(ip_asn), '_', ip_geo_country) LIKE %(search)s)"
            params['search'] = f"%{search}%"

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
        WHERE ip_asn > 0 AND ip_geo_country != '' {search_condition}
        GROUP BY asgeo, ip_asn, ip_geo_country, ip_as_name
        ORDER BY sample_count DESC
        LIMIT %(limit)s
        """

        result = self.execute(query, params)
        return [
            {
                'asgeo': row[0],
                'asn': row[1],
                'country': row[2],
                'as_name': row[3] or f"AS{row[1]}",
                'sample_count': row[4],
                'unique_ips': row[5],
                'prefix24_count': row[6],
            }
            for row in result
        ]

    def get_available_data_centers(
        self,
        region: str,
        limit: int = 50,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取地区中可能出现的数据中心列表，支持模糊搜索"""
        table_name = f"{region}__ping"

        search_condition = ""
        params: Dict[str, Any] = {'limit': limit}

        if search:
            search_condition = "AND data_center LIKE %(search)s"
            params['search'] = f"%{search}%"

        query = f"""
        SELECT
            data_center,
            count() as sample_count
        FROM {table_name}
        WHERE data_center != '' {search_condition}
        GROUP BY data_center
        ORDER BY sample_count DESC
        LIMIT %(limit)s
        """

        result = self.execute(query, params)
        return [
            {
                'data_center': row[0],
                'sample_count': row[1],
            }
            for row in result
        ]

    def get_available_isps(
        self,
        region: str,
        limit: int = 100,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取地区中出现的 ISP（运营商）列表，支持模糊搜索"""
        table_name = f"{region}__ping"

        conditions = ["ip_isp_domain != ''", "ip_isp_domain IS NOT NULL"]
        params: Dict[str, Any] = {'limit': limit}

        if search:
            conditions.append("ip_isp_domain LIKE %(search)s")
            params['search'] = f"%{search}%"

        where_clause = " AND ".join(conditions)

        query = f"""
        SELECT
            ip_isp_domain,
            count() as sample_count
        FROM {table_name}
        WHERE {where_clause}
        GROUP BY ip_isp_domain
        ORDER BY sample_count DESC
        LIMIT %(limit)s
        """

        result = self.execute(query, params)
        return [
            {
                'isp': row[0],
                'sample_count': row[1],
            }
            for row in result
        ]

    def get_available_prefix24s(
        self,
        region: str,
        limit: int = 100,
        search: Optional[str] = None,
        asn: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """获取地区中出现的 /24 前缀列表，支持模糊搜索和按 AS 过滤"""
        table_name = f"{region}__ping"

        conditions = ["prefix24 != ''"]
        params: Dict[str, Any] = {'limit': limit}

        if search:
            conditions.append("prefix24 LIKE %(search)s")
            params['search'] = f"%{search}%"

        if asn:
            conditions.append("ip_asn = %(asn)s")
            params['asn'] = asn

        where_clause = " AND ".join(conditions)

        query = f"""
        SELECT
            prefix24,
            count() as sample_count,
            uniqExact(dst_ip) as unique_ips
        FROM {table_name}
        WHERE {where_clause}
        GROUP BY prefix24
        ORDER BY sample_count DESC
        LIMIT %(limit)s
        """

        result = self.execute(query, params)
        return [
            {
                'prefix24': row[0],
                'sample_count': row[1],
                'unique_ips': row[2],
            }
            for row in result
        ]

    def get_time_range(
        self,
        region: str
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """获取地区数据的时间范围"""
        table_name = f"{region}__ping"

        query = f"""
        SELECT min(measure_time), max(measure_time)
        FROM {table_name}
        """

        result = self.execute(query)
        if result:
            return result[0][0], result[0][1]
        return None, None


# 全局客户端实例
_clickhouse_client: Optional[ClickHouseClient] = None


def get_clickhouse_client() -> ClickHouseClient:
    """获取 ClickHouse 客户端实例"""
    global _clickhouse_client
    if _clickhouse_client is None:
        _clickhouse_client = ClickHouseClient()
    return _clickhouse_client
