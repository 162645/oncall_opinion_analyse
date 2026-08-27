"""
ClickHouse 查询构建器
提供常用查询的模板和构建工具
"""

from typing import List, Dict, Any, Optional
from datetime import datetime


class QueryBuilder:
    """查询构建器"""

    @staticmethod
    def build_ping_stats_query(
        table_name: str,
        filters: Dict[str, Any],
        group_by: Optional[List[str]] = None
    ) -> tuple:
        """
        构建 Ping 统计查询

        Returns:
            (query, params)
        """
        conditions = []
        params = {}

        if filters.get('start_time'):
            conditions.append("measure_time >= %(start_time)s")
            params['start_time'] = filters['start_time']

        if filters.get('end_time'):
            conditions.append("measure_time <= %(end_time)s")
            params['end_time'] = filters['end_time']

        if filters.get('asn'):
            conditions.append("ip_asn = %(asn)s")
            params['asn'] = filters['asn']

        if filters.get('prefix24'):
            conditions.append("prefix24 = %(prefix24)s")
            params['prefix24'] = filters['prefix24']

        if filters.get('data_center'):
            conditions.append("data_center = %(data_center)s")
            params['data_center'] = filters['data_center']

        if filters.get('ip_geo_country'):
            conditions.append("ip_geo_country = %(ip_geo_country)s")
            params['ip_geo_country'] = filters['ip_geo_country']

        where_clause = " AND ".join(conditions) if conditions else "1=1"

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
                quantile(0.90)(rtt_ms) as p90_rtt,
                quantile(0.95)(rtt_ms) as p95_rtt,
                quantile(0.99)(rtt_ms) as p99_rtt
            FROM {table_name}
            WHERE {where_clause}
            GROUP BY {group_cols}
            ORDER BY sample_count DESC
            """
        else:
            query = f"""
            SELECT
                count() as sample_count,
                avg(rtt_ms) as mean_rtt,
                median(rtt_ms) as median_rtt,
                min(rtt_ms) as min_rtt,
                max(rtt_ms) as max_rtt,
                quantile(0.90)(rtt_ms) as p90_rtt,
                quantile(0.95)(rtt_ms) as p95_rtt,
                quantile(0.99)(rtt_ms) as p99_rtt
            FROM {table_name}
            WHERE {where_clause}
            """

        return query, params

    @staticmethod
    def build_path_analysis_query(
        table_name: str,
        filters: Dict[str, Any],
        analysis_type: str = 'as_path'
    ) -> tuple:
        """
        构建路径分析查询

        Args:
            analysis_type: 'as_path', 'asgeo_path', 'ip_path'
        """
        conditions = []
        params = {}

        if filters.get('start_time'):
            conditions.append("measure_time >= %(start_time)s")
            params['start_time'] = filters['start_time']

        if filters.get('end_time'):
            conditions.append("measure_time <= %(end_time)s")
            params['end_time'] = filters['end_time']

        if filters.get('target_asn'):
            conditions.append("hasToken(as_path_text, %(target_asn_pattern)s)")
            params['target_asn_pattern'] = f"AS{filters['target_asn']}"

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        path_column = {
            'as_path': 'as_path_text',
            'asgeo_path': 'asgeo_path_text',
            'ip_path': 'ip_path_text',
        }.get(analysis_type, 'as_path_text')

        query = f"""
        SELECT
            {path_column},
            count() as occurrence_count,
            avg(hop_count) as avg_hop_count,
            sum(if(reached_target, 1, 0)) as reached_count,
            uniqExact(dst_ip) as unique_destinations
        FROM {table_name}
        WHERE {where_clause}
        GROUP BY {path_column}
        ORDER BY occurrence_count DESC
        """

        return query, params

    @staticmethod
    def build_time_series_query(
        table_name: str,
        filters: Dict[str, Any],
        metric: str = 'rtt_ms',
        interval: str = 'hour',
        aggregation: str = 'median'
    ) -> tuple:
        """
        构建时间序列查询

        Args:
            metric: 指标名称
            interval: 时间间隔 (minute, hour, day)
            aggregation: 聚合方式 (avg, median, min, max)
        """
        conditions = []
        params = {}

        if filters.get('start_time'):
            conditions.append("measure_time >= %(start_time)s")
            params['start_time'] = filters['start_time']

        if filters.get('end_time'):
            conditions.append("measure_time <= %(end_time)s")
            params['end_time'] = filters['end_time']

        if filters.get('asn'):
            conditions.append("ip_asn = %(asn)s")
            params['asn'] = filters['asn']

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        interval_func = {
            'minute': 'toStartOfMinute',
            'hour': 'toStartOfHour',
            'day': 'toStartOfDay',
        }.get(interval, 'toStartOfHour')

        agg_func = {
            'avg': 'avg',
            'median': 'median',
            'min': 'min',
            'max': 'max',
        }.get(aggregation, 'median')

        query = f"""
        SELECT
            {interval_func}(measure_time) as time_bucket,
            count() as sample_count,
            {agg_func}({metric}) as value,
            quantile(0.90)({metric}) as p90,
            quantile(0.95)({metric}) as p95
        FROM {table_name}
        WHERE {where_clause}
        GROUP BY time_bucket
        ORDER BY time_bucket
        """

        return query, params


# 常用查询模板
QUERIES = {
    # 获取地区概览
    'region_overview': """
    SELECT
        target_region,
        count() as file_count,
        sum(ping_rows) as total_ping_rows,
        sum(trace_rows) as total_trace_rows
    FROM import_files
    GROUP BY target_region
    ORDER BY total_ping_rows DESC
    """,

    # 获取 AS 分布
    'asn_distribution': """
    SELECT
        ip_asn,
        ip_as_name,
        count() as sample_count,
        median(rtt_ms) as median_rtt,
        avg(rtt_ms) as mean_rtt
    FROM {table_name}
    WHERE ip_asn > 0
    GROUP BY ip_asn, ip_as_name
    ORDER BY sample_count DESC
    LIMIT {limit}
    """,

    # 获取国家分布
    'country_distribution': """
    SELECT
        ip_geo_country,
        ip_geo_region,
        count() as sample_count,
        median(rtt_ms) as median_rtt
    FROM {table_name}
    WHERE ip_geo_country != ''
    GROUP BY ip_geo_country, ip_geo_region
    ORDER BY sample_count DESC
    LIMIT {limit}
    """,

    # 获取数据中心统计
    'datacenter_stats': """
    SELECT
        data_center,
        count() as sample_count,
        min(measure_time) as min_time,
        max(measure_time) as max_time,
        uniqExact(prefix24) as unique_prefixes
    FROM {table_name}
    GROUP BY data_center
    ORDER BY sample_count DESC
    """,

    # RTT 分布直方图
    'rtt_histogram': """
    SELECT
        floor(rtt_ms / {bucket_size}) * {bucket_size} as rtt_bucket,
        count() as count
    FROM {table_name}
    WHERE rtt_ms > 0 AND rtt_ms < {max_rtt}
    GROUP BY rtt_bucket
    ORDER BY rtt_bucket
    """,

    # 路径变化分析
    'path_variability': """
    SELECT
        dst_ip,
        uniqExact(ip_path_hash) as path_count,
        groupArray(tuple(ip_path_text, count)) as paths
    FROM (
        SELECT
            dst_ip,
            ip_path_hash,
            ip_path_text,
            count() as count
        FROM {table_name}
        GROUP BY dst_ip, ip_path_hash, ip_path_text
    )
    GROUP BY dst_ip
    HAVING path_count > 1
    ORDER BY path_count DESC
    LIMIT {limit}
    """,

    # AS 路径长度分布
    'as_path_length_distribution': """
    SELECT
        length(arrayFilter(x -> x != '*', splitByString('->', as_path_text))) as path_length,
        count() as count
    FROM {table_name}
    WHERE as_path_text != ''
    GROUP BY path_length
    ORDER BY path_length
    """,
}
