"""
增强版数据分析器
提供全面的网络测量数据分析功能
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging
import math

logger = logging.getLogger(__name__)


def _safe_float(value):
    """将浮点数转换为安全值，处理 inf 和 NaN"""
    if value is None:
        return 0.0
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return 0.0
    return value


@dataclass
class AnalysisConfig:
    """分析配置"""
    percentiles: List[int] = None  # 如 [50, 90, 95, 99]
    include_stats: bool = True  # 是否包含基础统计
    include_distribution: bool = True  # 是否包含分布信息
    include_anomalies: bool = False  # 是否检测异常
    # 极端值过滤
    outlier_filter_min: Optional[float] = None  # 最小分位数过滤 (如 5 表示过滤掉 P5 以下的数据)
    outlier_filter_max: Optional[float] = None  # 最大分位数过滤 (如 95 表示过滤掉 P95 以上的数据)

    def __post_init__(self):
        if self.percentiles is None:
            self.percentiles = [50, 90, 95, 99]


class PingAnalyzer:
    """
    Ping 数据增强分析器

    支持的分析维度:
    1. 整体统计（均值、中位数、分位数、标准差）
    2. 时间趋势分析
    3. AS 维度分析
    4. ASGeo 维度分析
    5. 国家/地区/城市维度分析
    6. 数据中心维度分析
    7. /24 前缀维度分析
    8. 多维度交叉分析
    9. 异常检测
    10. 对比分析
    """

    def __init__(self, client):
        """
        Args:
            client: ClickHouse 客户端实例
        """
        self.client = client

    def analyze_overall(
        self,
        region: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        config: Optional[AnalysisConfig] = None,
        **filters
    ) -> Dict[str, Any]:
        """
        整体统计分析

        Returns:
            包含完整统计指标的字典，包括高级统计量
        """
        config = config or AnalysisConfig()
        table_name = f"{region}__ping"

        where_conditions = []
        params = {}

        if start_time:
            where_conditions.append("measure_time >= %(start_time)s")
            params['start_time'] = start_time
        if end_time:
            where_conditions.append("measure_time <= %(end_time)s")
            params['end_time'] = end_time

        # 添加其他筛选条件
        for key, value in filters.items():
            if value is not None:
                where_conditions.append(f"{key} = %({key})s")
                params[key] = value

        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        # 构建分位数查询
        percentile_queries = ", ".join([
            f"quantile({p/100})(rtt_ms) as p{p}_rtt"
            for p in config.percentiles
        ])

        # 构建极端值过滤条件
        outlier_filter = ""
        if config.outlier_filter_min is not None or config.outlier_filter_max is not None:
            conditions = []
            if config.outlier_filter_min is not None:
                conditions.append(f"rtt_ms >= quantile({config.outlier_filter_min/100})(rtt_ms)")
            if config.outlier_filter_max is not None:
                conditions.append(f"rtt_ms <= quantile({config.outlier_filter_max/100})(rtt_ms)")
            outlier_filter = " AND " + " AND ".join(conditions)

        query = f"""
        SELECT
            count() as total_samples,
            countIf(rtt_ms > 0) as valid_samples,
            sum(if(rtt_ms = 0, 1, 0)) as zero_rtt_count,
            sum(if(rtt_ms < 0, 1, 0)) as timeout_count,

            -- 基础统计
            min(rtt_ms) as min_rtt,
            max(rtt_ms) as max_rtt,
            avg(rtt_ms) as mean_rtt,
            median(rtt_ms) as median_rtt,
            stddevPop(rtt_ms) as std_rtt,
            varPop(rtt_ms) as var_rtt,

            -- 高级统计
            stddevPop(rtt_ms) / avg(rtt_ms) as coefficient_of_variation,
            skewPop(rtt_ms) as skewness,
            kurtPop(rtt_ms) as kurtosis,
            quantile(0.75)(rtt_ms) - quantile(0.25)(rtt_ms) as iqr,

            -- 几何平均 (只对正数有效)
            exp(avg(log(rtt_ms))) as geometric_mean,

            -- 分位数
            {percentile_queries},

            -- 分布统计
            uniqExact(ip_asn) as unique_asns,
            uniqExact(ip_geo_country) as unique_countries,
            uniqExact(prefix24) as unique_prefixes,
            uniqExact(dst_ip) as unique_ips

        FROM {table_name}
        WHERE {where_clause}
        """

        result = self.client.execute(query, params)

        if not result:
            return {'error': 'No data found'}

        row = result[0]
        base_idx = 16  # 基础统计 + 高级统计的数量

        response = {
            'total_samples': row[0],
            'valid_samples': row[1],
            'zero_rtt_count': row[2],
            'timeout_count': row[3],
            'min_rtt': row[4],
            'max_rtt': row[5],
            'mean_rtt': row[6],
            'median_rtt': row[7],
            'std_rtt': row[8],
            'var_rtt': row[9],
            # 高级统计
            'coefficient_of_variation': row[10],  # 变异系数
            'skewness': row[11],  # 偏度
            'kurtosis': row[12],  # 峰度
            'iqr': row[13],  # 四分位距
            'geometric_mean': row[14],  # 几何平均
            'percentiles': {
                f'p{p}': row[15 + i]
                for i, p in enumerate(config.percentiles)
            },
            'distribution': {
                'unique_asns': row[15 + len(config.percentiles)],
                'unique_countries': row[16 + len(config.percentiles)],
                'unique_prefixes': row[17 + len(config.percentiles)],
                'unique_ips': row[18 + len(config.percentiles)],
            },
        }

        # 计算截尾均值 (trimmed mean)
        if config.outlier_filter_min is not None and config.outlier_filter_max is not None:
            trimmed_query = f"""
            SELECT avg(rtt_ms) as trimmed_mean
            FROM {table_name}
            WHERE {where_clause}
              AND rtt_ms >= quantile({config.outlier_filter_min/100})(rtt_ms)
              AND rtt_ms <= quantile({config.outlier_filter_max/100})(rtt_ms)
            """
            try:
                trimmed_result = self.client.execute(trimmed_query, params)
                if trimmed_result and trimmed_result[0][0] is not None:
                    response['trimmed_mean'] = trimmed_result[0][0]
                    response['trimmed_percentile_range'] = {
                        'min': config.outlier_filter_min,
                        'max': config.outlier_filter_max
                    }
            except Exception:
                pass

        return response

    def analyze_time_trend(
        self,
        region: str,
        interval: str = 'hour',
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        config: Optional[AnalysisConfig] = None,
        **filters
    ) -> List[Dict[str, Any]]:
        """
        时间趋势分析

        Args:
            interval: 时间粒度 (minute, hour, day)
        """
        config = config or AnalysisConfig()
        table_name = f"{region}__ping"

        interval_func = {
            'minute': 'toStartOfMinute',
            'hour': 'toStartOfHour',
            'day': 'toStartOfDay',
            'week': 'toStartOfWeek',
            'month': 'toStartOfMonth',
        }.get(interval, 'toStartOfHour')

        where_conditions = []
        params = {}

        if start_time:
            where_conditions.append("measure_time >= %(start_time)s")
            params['start_time'] = start_time
        if end_time:
            where_conditions.append("measure_time <= %(end_time)s")
            params['end_time'] = end_time

        for key, value in filters.items():
            if value is not None:
                where_conditions.append(f"{key} = %({key})s")
                params[key] = value

        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        percentile_queries = ", ".join([
            f"quantile({p/100})(rtt_ms) as p{p}_rtt"
            for p in config.percentiles
        ])

        # 计算方差 (标准差的平方)
        var_query = "stddevPop(rtt_ms) as std_rtt, varPop(rtt_ms) as var_rtt"
        # 计算 IQR (Q3 - Q1)
        iqr_query = "quantile(0.75)(rtt_ms) as q3_rtt, quantile(0.25)(rtt_ms) as q1_rtt"
        # 计算偏度和峰度
        skew_kurt_query = "skewPop(rtt_ms) as skewness, kurtPop(rtt_ms) as kurtosis"

        query = f"""
        SELECT
            {interval_func}(measure_time) as time_bucket,
            count() as sample_count,
            avg(rtt_ms) as mean_rtt,
            median(rtt_ms) as median_rtt,
            min(rtt_ms) as min_rtt,
            max(rtt_ms) as max_rtt,
            {var_query},
            {iqr_query},
            {skew_kurt_query},
            {percentile_queries}
        FROM {table_name}
        WHERE {where_clause}
        GROUP BY time_bucket
        ORDER BY time_bucket
        """

        result = self.client.execute(query, params)

        data = []
        for row in result:
            mean_rtt = _safe_float(row[2])
            std_rtt = _safe_float(row[6])
            # 计算变异系数 (CV = std / mean * 100)
            coefficient_of_variation = (std_rtt / mean_rtt * 100) if mean_rtt > 0 else 0.0
            # 计算 IQR (Q3 - Q1)
            q1 = _safe_float(row[9])
            q3 = _safe_float(row[8])
            iqr = q3 - q1

            item = {
                'time': row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                'sample_count': row[1],
                'mean_rtt': mean_rtt,
                'median_rtt': _safe_float(row[3]),
                'min_rtt': _safe_float(row[4]),
                'max_rtt': _safe_float(row[5]),
                'std_rtt': std_rtt,
                'var_rtt': _safe_float(row[7]),
                'coefficient_of_variation': coefficient_of_variation,
                'iqr': iqr,
                'skewness': _safe_float(row[10]),
                'kurtosis': _safe_float(row[11]),
                'percentiles': {
                    f'p{p}': _safe_float(row[12 + i])
                    for i, p in enumerate(config.percentiles)
                },
            }
            data.append(item)

        return data

    def analyze_by_asn(
        self,
        region: str,
        top_n: int = 20,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        config: Optional[AnalysisConfig] = None,
        **filters
    ) -> List[Dict[str, Any]]:
        """按 AS 维度分析"""
        config = config or AnalysisConfig()
        table_name = f"{region}__ping"

        where_conditions = ["ip_asn > 0"]
        params = {'limit': top_n}

        if start_time:
            where_conditions.append("measure_time >= %(start_time)s")
            params['start_time'] = start_time
        if end_time:
            where_conditions.append("measure_time <= %(end_time)s")
            params['end_time'] = end_time

        for key, value in filters.items():
            if value is not None:
                where_conditions.append(f"{key} = %({key})s")
                params[key] = value

        where_clause = " AND ".join(where_conditions)

        percentile_queries = ", ".join([
            f"quantile({p/100})(rtt_ms) as p{p}_rtt"
            for p in config.percentiles
        ])

        query = f"""
        SELECT
            ip_asn,
            ip_as_name,
            count() as sample_count,
            avg(rtt_ms) as mean_rtt,
            median(rtt_ms) as median_rtt,
            min(rtt_ms) as min_rtt,
            max(rtt_ms) as max_rtt,
            stddevPop(rtt_ms) as std_rtt,
            {percentile_queries},
            uniqExact(ip_geo_country) as countries_reached,
            uniqExact(dst_ip) as unique_ips
        FROM {table_name}
        WHERE {where_clause}
        GROUP BY ip_asn, ip_as_name
        ORDER BY sample_count DESC
        LIMIT %(limit)s
        """

        result = self.client.execute(query, params)

        data = []
        for row in result:
            item = {
                'asn': row[0],
                'as_name': row[1],
                'sample_count': row[2],
                'mean_rtt': row[3],
                'median_rtt': row[4],
                'min_rtt': row[5],
                'max_rtt': row[6],
                'std_rtt': row[7],
                'percentiles': {
                    f'p{p}': row[8 + i]
                    for i, p in enumerate(config.percentiles)
                },
                'countries_reached': row[8 + len(config.percentiles)],
                'unique_ips': row[9 + len(config.percentiles)],
            }
            data.append(item)

        return data

    def analyze_by_asgeo(
        self,
        region: str,
        top_n: int = 20,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        config: Optional[AnalysisConfig] = None,
        **filters
    ) -> List[Dict[str, Any]]:
        """按 AS+Geo 维度分析"""
        config = config or AnalysisConfig()
        table_name = f"{region}__ping"

        where_conditions = ["ip_asn > 0"]
        params = {'limit': top_n}

        if start_time:
            where_conditions.append("measure_time >= %(start_time)s")
            params['start_time'] = start_time
        if end_time:
            where_conditions.append("measure_time <= %(end_time)s")
            params['end_time'] = end_time

        where_clause = " AND ".join(where_conditions)

        percentile_queries = ", ".join([
            f"quantile({p/100})(rtt_ms) as p{p}_rtt"
            for p in config.percentiles
        ])

        query = f"""
        SELECT
            concat('AS', toString(ip_asn), '-', ip_geo_country) as asgeo,
            ip_asn,
            ip_as_name,
            ip_geo_country,
            ip_geo_region,
            count() as sample_count,
            avg(rtt_ms) as mean_rtt,
            median(rtt_ms) as median_rtt,
            min(rtt_ms) as min_rtt,
            max(rtt_ms) as max_rtt,
            {percentile_queries}
        FROM {table_name}
        WHERE {where_clause}
        GROUP BY ip_asn, ip_as_name, ip_geo_country, ip_geo_region
        ORDER BY sample_count DESC
        LIMIT %(limit)s
        """

        result = self.client.execute(query, params)

        data = []
        for row in result:
            item = {
                'asgeo': row[0],
                'asn': row[1],
                'as_name': row[2],
                'country': row[3],
                'region': row[4],
                'sample_count': row[5],
                'mean_rtt': row[6],
                'median_rtt': row[7],
                'min_rtt': row[8],
                'max_rtt': row[9],
                'percentiles': {
                    f'p{p}': row[10 + i]
                    for i, p in enumerate(config.percentiles)
                },
            }
            data.append(item)

        return data

    def analyze_by_country(
        self,
        region: str,
        top_n: int = 30,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        config: Optional[AnalysisConfig] = None,
        **filters
    ) -> List[Dict[str, Any]]:
        """按国家维度分析"""
        config = config or AnalysisConfig()
        table_name = f"{region}__ping"

        where_conditions = ["ip_geo_country != ''"]
        params = {'limit': top_n}

        if start_time:
            where_conditions.append("measure_time >= %(start_time)s")
            params['start_time'] = start_time
        if end_time:
            where_conditions.append("measure_time <= %(end_time)s")
            params['end_time'] = end_time

        where_clause = " AND ".join(where_conditions)

        percentile_queries = ", ".join([
            f"quantile({p/100})(rtt_ms) as p{p}_rtt"
            for p in config.percentiles
        ])

        query = f"""
        SELECT
            ip_geo_country,
            count() as sample_count,
            avg(rtt_ms) as mean_rtt,
            median(rtt_ms) as median_rtt,
            min(rtt_ms) as min_rtt,
            max(rtt_ms) as max_rtt,
            {percentile_queries},
            uniqExact(ip_asn) as unique_asns,
            uniqExact(ip_geo_region) as unique_regions
        FROM {table_name}
        WHERE {where_clause}
        GROUP BY ip_geo_country
        ORDER BY sample_count DESC
        LIMIT %(limit)s
        """

        result = self.client.execute(query, params)

        data = []
        for row in result:
            item = {
                'country': row[0],
                'sample_count': row[1],
                'mean_rtt': row[2],
                'median_rtt': row[3],
                'min_rtt': row[4],
                'max_rtt': row[5],
                'percentiles': {
                    f'p{p}': row[6 + i]
                    for i, p in enumerate(config.percentiles)
                },
                'unique_asns': row[6 + len(config.percentiles)],
                'unique_regions': row[7 + len(config.percentiles)],
            }
            data.append(item)

        return data

    def analyze_by_data_center(
        self,
        region: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        config: Optional[AnalysisConfig] = None,
        **filters
    ) -> List[Dict[str, Any]]:
        """按数据中心维度分析"""
        config = config or AnalysisConfig()
        table_name = f"{region}__ping"

        where_conditions = ["data_center != ''"]
        params = {}

        if start_time:
            where_conditions.append("measure_time >= %(start_time)s")
            params['start_time'] = start_time
        if end_time:
            where_conditions.append("measure_time <= %(end_time)s")
            params['end_time'] = end_time

        where_clause = " AND ".join(where_conditions)

        percentile_queries = ", ".join([
            f"quantile({p/100})(rtt_ms) as p{p}_rtt"
            for p in config.percentiles
        ])

        query = f"""
        SELECT
            data_center,
            count() as sample_count,
            avg(rtt_ms) as mean_rtt,
            median(rtt_ms) as median_rtt,
            min(rtt_ms) as min_rtt,
            max(rtt_ms) as max_rtt,
            {percentile_queries}
        FROM {table_name}
        WHERE {where_clause}
        GROUP BY data_center
        ORDER BY sample_count DESC
        """

        result = self.client.execute(query, params)

        data = []
        for row in result:
            item = {
                'data_center': row[0],
                'sample_count': row[1],
                'mean_rtt': row[2],
                'median_rtt': row[3],
                'min_rtt': row[4],
                'max_rtt': row[5],
                'percentiles': {
                    f'p{p}': row[6 + i]
                    for i, p in enumerate(config.percentiles)
                },
            }
            data.append(item)

        return data

    def detect_anomalies(
        self,
        region: str,
        threshold_std: float = 3.0,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        **filters
    ) -> Dict[str, Any]:
        """
        异常检测

        Args:
            threshold_std: 标准差阈值，超过此值视为异常
        """
        table_name = f"{region}__ping"

        where_conditions = []
        params = {}

        if start_time:
            where_conditions.append("measure_time >= %(start_time)s")
            params['start_time'] = start_time
        if end_time:
            where_conditions.append("measure_time <= %(end_time)s")
            params['end_time'] = end_time

        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        query = f"""
        SELECT
            avg(rtt_ms) as mean_rtt,
            stddevPop(rtt_ms) as std_rtt,
            median(rtt_ms) as median_rtt
        FROM {table_name}
        WHERE {where_clause}
        """

        result = self.client.execute(query, params)

        if not result or result[0][1] is None:
            return {'anomalies': [], 'message': 'Insufficient data for anomaly detection'}

        mean_rtt = result[0][0]
        std_rtt = result[0][1]
        median_rtt = result[0][2]

        upper_bound = mean_rtt + threshold_std * std_rtt
        lower_bound = max(0, mean_rtt - threshold_std * std_rtt)

        # 查找异常值
        anomaly_query = f"""
        SELECT
            measure_time,
            dst_ip,
            ip_asn,
            ip_as_name,
            rtt_ms
        FROM {table_name}
        WHERE {where_clause}
          AND (rtt_ms > {upper_bound} OR rtt_ms < {lower_bound})
        ORDER BY rtt_ms DESC
        LIMIT 100
        """

        anomalies = self.client.execute(anomaly_query, params)

        return {
            'mean_rtt': mean_rtt,
            'std_rtt': std_rtt,
            'median_rtt': median_rtt,
            'upper_bound': upper_bound,
            'lower_bound': lower_bound,
            'threshold_std': threshold_std,
            'anomaly_count': len(anomalies),
            'anomalies': [
                {
                    'time': row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                    'dst_ip': row[1],
                    'asn': row[2],
                    'as_name': row[3],
                    'rtt_ms': row[4],
                }
                for row in anomalies
            ],
        }

    def hierarchical_analysis(
        self,
        region: str,
        hierarchy: List[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        config: Optional[AnalysisConfig] = None,
        outlier_filter: Optional[Dict[str, float]] = None,
        **filters
    ) -> Dict[str, Any]:
        """
        分层分析 - 支持逐层下钻

        Args:
            hierarchy: 层级顺序，如 ['time', 'asgeo', 'prefix24']
            outlier_filter: 极端值过滤配置 {'percentile_min': 5, 'percentile_max': 95}

        Returns:
            分层聚合的统计结果
        """
        config = config or AnalysisConfig()
        if hierarchy is None:
            hierarchy = ['asn', 'country', 'prefix24']

        table_name = f"{region}__ping"
        where_conditions = ["rtt_ms > 0"]
        params = {}

        if start_time:
            where_conditions.append("measure_time >= %(start_time)s")
            params['start_time'] = start_time
        if end_time:
            where_conditions.append("measure_time <= %(end_time)s")
            params['end_time'] = end_time

        for key, value in filters.items():
            if value is not None:
                where_conditions.append(f"{key} = %({key})s")
                params[key] = value

        where_clause = " AND ".join(where_conditions)

        group_field_map = {
            'time': 'toStartOfHour(measure_time) as time_bucket',
            'asn': 'ip_asn',
            'asgeo': "concat(toString(ip_asn), '_', ifNull(ip_geo_country, 'Unknown')) as asgeo",
            'prefix24': 'prefix24',
            'country': 'ip_geo_country',
            'data_center': 'data_center',
        }

        select_fields = []
        group_fields = []
        for level in hierarchy:
            if level in group_field_map:
                select_fields.append(group_field_map[level])
                if ' as ' in group_field_map[level]:
                    alias = group_field_map[level].split(' as ')[1]
                    group_fields.append(alias)
                else:
                    group_fields.append(group_field_map[level])

        if not group_fields:
            return {'error': 'Invalid hierarchy configuration'}

        percentile_queries = ", ".join([
            f"quantile({p/100})(rtt_ms) as p{p}_rtt"
            for p in config.percentiles
        ])

        query = f"""
        SELECT
            {', '.join(select_fields)},
            count() as sample_count,
            avg(rtt_ms) as mean_rtt,
            median(rtt_ms) as median_rtt,
            min(rtt_ms) as min_rtt,
            max(rtt_ms) as max_rtt,
            stddevPop(rtt_ms) as std_rtt,
            {percentile_queries}
        FROM {table_name}
        WHERE {where_clause}
        GROUP BY {', '.join(group_fields)}
        ORDER BY sample_count DESC
        LIMIT 1000
        """

        try:
            result = self.client.execute(query, params)
        except Exception as e:
            logger.error(f"Hierarchical analysis failed: {e}")
            return {'error': str(e)}

        data = []
        for row in result:
            item = {
                'sample_count': row[len(group_fields)],
                'mean_rtt': row[len(group_fields) + 1],
                'median_rtt': row[len(group_fields) + 2],
                'min_rtt': row[len(group_fields) + 3],
                'max_rtt': row[len(group_fields) + 4],
                'std_rtt': row[len(group_fields) + 5],
                'percentiles': {},
            }
            for i, field in enumerate(group_fields):
                item[field] = row[i]
            for i, p in enumerate(config.percentiles):
                item['percentiles'][f'p{p}'] = row[len(group_fields) + 6 + i]
            data.append(item)

        return {
            'flat_data': data,
            'hierarchy': hierarchy,
            'total_records': len(data),
        }

    def drill_down(
        self,
        region: str,
        level: str,
        level_value: Any,
        next_level: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        config: Optional[AnalysisConfig] = None,
        **filters
    ) -> Dict[str, Any]:
        """
        下钻分析 - 从一个层级钻取到下一层级

        Args:
            level: 当前层级 (asn, asgeo, prefix24, country)
            level_value: 当前层级的值
            next_level: 下一层级

        Returns:
            下一层级的聚合统计
        """
        config = config or AnalysisConfig()
        table_name = f"{region}__ping"

        where_conditions = ["rtt_ms > 0"]
        params = {}

        level_field_map = {
            'overall': None,  # overall doesn't have a filter
            'asn': 'ip_asn',
            'asgeo': "concat(toString(ip_asn), '_', ifNull(ip_geo_country, 'Unknown'))",
            'prefix24': 'prefix24',
            'country': 'ip_geo_country',
            'data_center': 'data_center',
        }

        if level in level_field_map and level != 'overall' and level_value is not None:
            if level == 'asgeo':
                parts = str(level_value).split('_')
                if len(parts) >= 2:
                    where_conditions.append("ip_asn = %(asn)s")
                    params['asn'] = int(parts[0]) if parts[0].isdigit() else 0
                    where_conditions.append("ip_geo_country = %(country)s")
                    params['country'] = parts[1]
            else:
                where_conditions.append(f"{level_field_map[level]} = %(level_value)s")
                params['level_value'] = level_value

        if start_time:
            where_conditions.append("measure_time >= %(start_time)s")
            params['start_time'] = start_time
        if end_time:
            where_conditions.append("measure_time <= %(end_time)s")
            params['end_time'] = end_time

        for key, value in filters.items():
            if value is not None:
                where_conditions.append(f"{key} = %({key})s")
                params[key] = value

        where_clause = " AND ".join(where_conditions)

        next_field = level_field_map.get(next_level, next_level)
        percentile_queries = ", ".join([
            f"quantile({p/100})(rtt_ms) as p{p}_rtt"
            for p in config.percentiles
        ])

        query = f"""
        SELECT
            {next_field} as {next_level},
            count() as sample_count,
            avg(rtt_ms) as mean_rtt,
            median(rtt_ms) as median_rtt,
            min(rtt_ms) as min_rtt,
            max(rtt_ms) as max_rtt,
            stddevPop(rtt_ms) as std_rtt,
            {percentile_queries}
        FROM {table_name}
        WHERE {where_clause}
        GROUP BY {next_level}
        ORDER BY sample_count DESC
        LIMIT 100
        """

        try:
            result = self.client.execute(query, params)
        except Exception as e:
            logger.error(f"Drill down analysis failed: {e}")
            return {'error': str(e)}

        data = []
        for row in result:
            item = {
                next_level: row[0],
                'sample_count': row[1],
                'mean_rtt': row[2],
                'median_rtt': row[3],
                'min_rtt': row[4],
                'max_rtt': row[5],
                'std_rtt': row[6],
                'percentiles': {},
            }
            for i, p in enumerate(config.percentiles):
                item['percentiles'][f'p{p}'] = row[7 + i]
            data.append(item)

        return {
            'children': data,
            'level': level,
            'level_value': level_value,
            'next_level': next_level,
        }


class TracerouteAnalyzer:
    """
    Traceroute 数据增强分析器

    支持的分析维度:
    1. 路径统计
    2. AS 路径分析
    3. ASGeo 路径分析
    4. 路径-Ping 关联分析
    5. 目标 AS 路径分析
    """

    def __init__(self, client):
        self.client = client

    def analyze_path_statistics(
        self,
        region: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        path_type: str = 'as',  # ip, as, asgeo
        top_n: int = 50,
        **filters
    ) -> List[Dict[str, Any]]:
        """
        路径统计分析

        Args:
            path_type: 路径类型 (ip, as, asgeo)
        """
        table_name = f"{region}__quarter_traceroute"

        where_conditions = []
        params = {'limit': top_n}

        if start_time:
            where_conditions.append("measure_time >= %(start_time)s")
            params['start_time'] = start_time
        if end_time:
            where_conditions.append("measure_time <= %(end_time)s")
            params['end_time'] = end_time

        for key, value in filters.items():
            if value is not None:
                where_conditions.append(f"{key} = %({key})s")
                params[key] = value

        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        # 根据路径类型选择字段
        path_field = {
            'ip': 'ip_path_text',
            'as': 'as_path_text',
            'asgeo': 'asgeo_path_text',
        }.get(path_type, 'as_path_text')

        path_hash_field = f"{path_field}_hash" if path_type != 'asgeo' else 'asgeo_path_hash'

        query = f"""
        SELECT
            {path_field} as path,
            count() as occurrence_count,
            avg(hop_count) as avg_hop_count,
            sum(if(reached_target, 1, 0)) as reached_count,
            uniqExact(data_center) as unique_data_centers
        FROM {table_name}
        WHERE {where_clause}
          AND {path_field} != ''
        GROUP BY {path_field}
        ORDER BY occurrence_count DESC
        LIMIT %(limit)s
        """

        result = self.client.execute(query, params)

        return [
            {
                'path': row[0],
                'occurrence_count': row[1],
                'avg_hop_count': row[2],
                'reached_count': row[3],
                'reach_rate': row[3] / row[1] if row[1] > 0 else 0,
                'unique_data_centers': row[4],
            }
            for row in result
        ]

    def analyze_paths_to_target(
        self,
        region: str,
        target_asn: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        top_n: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        分析到特定 AS 的路径

        Args:
            target_asn: 目标 AS 号
        """
        table_name = f"{region}__quarter_traceroute"

        where_conditions = [f"hasToken(as_path_text, 'AS{target_asn}')"]
        params = {'limit': top_n, 'target_asn': target_asn}

        if start_time:
            where_conditions.append("measure_time >= %(start_time)s")
            params['start_time'] = start_time
        if end_time:
            where_conditions.append("measure_time <= %(end_time)s")
            params['end_time'] = end_time

        where_clause = " AND ".join(where_conditions)

        query = f"""
        SELECT
            as_path_text,
            asgeo_path_text,
            ip_path_text,
            count() as occurrence_count,
            avg(hop_count) as avg_hop_count,
            sum(if(reached_target, 1, 0)) as reached_count
        FROM {table_name}
        WHERE {where_clause}
        GROUP BY as_path_text, asgeo_path_text, ip_path_text
        ORDER BY occurrence_count DESC
        LIMIT %(limit)s
        """

        result = self.client.execute(query, params)

        return [
            {
                'as_path': row[0],
                'asgeo_path': row[1],
                'ip_path': row[2],
                'occurrence_count': row[3],
                'avg_hop_count': row[4],
                'reached_count': row[5],
            }
            for row in result
        ]

    def analyze_path_ping_correlation(
        self,
        region: str,
        prefix24: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        分析路径关联的 Ping 数据

        通过 prefix24 关联 Traceroute 路径和 Ping 数据
        """
        ping_table = f"{region}__ping"
        trace_table = f"{region}__quarter_traceroute"

        time_filter = ""
        params = {'prefix24': prefix24}

        if start_time and end_time:
            time_filter = "AND measure_time BETWEEN %(start_time)s AND %(end_time)s"
            params['start_time'] = start_time
            params['end_time'] = end_time

        # 查询该 prefix24 的路径
        trace_query = f"""
        SELECT
            as_path_text,
            asgeo_path_text,
            count() as trace_count
        FROM {trace_table}
        WHERE prefix24 = %(prefix24)s {time_filter}
        GROUP BY as_path_text, asgeo_path_text
        ORDER BY trace_count DESC
        LIMIT 10
        """

        # 查询该 prefix24 的 Ping 统计
        ping_query = f"""
        SELECT
            count() as sample_count,
            avg(rtt_ms) as mean_rtt,
            median(rtt_ms) as median_rtt,
            quantile(0.90)(rtt_ms) as p90_rtt,
            quantile(0.95)(rtt_ms) as p95_rtt,
            quantile(0.99)(rtt_ms) as p99_rtt,
            uniqExact(dst_ip) as unique_ips,
            uniqExact(ip_asn) as unique_asns
        FROM {ping_table}
        WHERE prefix24 = %(prefix24)s {time_filter}
        """

        trace_result = self.client.execute(trace_query, params)
        ping_result = self.client.execute(ping_query, params)

        paths = [
            {
                'as_path': row[0],
                'asgeo_path': row[1],
                'trace_count': row[2],
            }
            for row in trace_result
        ]

        ping_stats = {}
        if ping_result and ping_result[0][0] > 0:
            ping_stats = {
                'sample_count': ping_result[0][0],
                'mean_rtt': ping_result[0][1],
                'median_rtt': ping_result[0][2],
                'p90_rtt': ping_result[0][3],
                'p95_rtt': ping_result[0][4],
                'p99_rtt': ping_result[0][5],
                'unique_ips': ping_result[0][6],
                'unique_asns': ping_result[0][7],
            }

        return {
            'prefix24': prefix24,
            'ping_stats': ping_stats,
            'trace_paths': paths,
        }

    def analyze_hop_distribution(
        self,
        region: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """分析跳数分布"""
        table_name = f"{region}__quarter_traceroute"

        where_conditions = []
        params = {}

        if start_time:
            where_conditions.append("measure_time >= %(start_time)s")
            params['start_time'] = start_time
        if end_time:
            where_conditions.append("measure_time <= %(end_time)s")
            params['end_time'] = end_time

        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        query = f"""
        SELECT
            hop_count,
            count() as occurrence_count,
            avg(responded_hop_count) as avg_responded_hops,
            sum(if(reached_target, 1, 0)) as reached_count
        FROM {table_name}
        WHERE {where_clause}
        GROUP BY hop_count
        ORDER BY hop_count
        """

        result = self.client.execute(query, params)

        return {
            'distribution': [
                {
                    'hop_count': row[0],
                    'occurrence_count': row[1],
                    'avg_responded_hops': row[2],
                    'reached_count': row[3],
                }
                for row in result
            ],
        }

    def analyze_terminal_nodes(
        self,
        region: str,
        terminal_type: str = 'as',  # 'as' or 'asgeo'
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        top_n: int = 50,
        include_paths: bool = True,
        terminal_filter: Optional[str] = None,
        data_center: Optional[str] = None,
        trace_type: str = 'quarter',
    ) -> Dict[str, Any]:
        """
        分析末端 AS/ASGeo 节点（只分析成功到达目标的路径）

        Args:
            terminal_type: 'as' 或 'asgeo'
            include_paths: 是否包含示例路径
            terminal_filter: 末端节点模糊搜索过滤
            data_center: 数据中心筛选
            trace_type: 数据类型 'quarter' 或 'full'
        """
        # 根据数据类型选择表
        if trace_type == 'full':
            table_name = f"{region}__traceroute"
        else:
            table_name = f"{region}__quarter_traceroute"

        where_conditions = ["reached_target = 1"]  # 只分析成功到达的路径
        params = {'limit': top_n}

        if start_time:
            where_conditions.append("measure_time >= %(start_time)s")
            params['start_time'] = start_time
        if end_time:
            where_conditions.append("measure_time <= %(end_time)s")
            params['end_time'] = end_time

        # 数据中心筛选
        if data_center:
            where_conditions.append("data_center = %(data_center)s")
            params['data_center'] = data_center

        where_clause = " AND ".join(where_conditions)

        # 根据末端类型选择字段
        if terminal_type == 'asgeo':
            terminal_field = 'asgeo_term'
            path_field = 'asgeo_path_text'
        else:
            terminal_field = 'as_term'
            path_field = 'as_path_text'

        # 添加末端节点过滤
        if terminal_filter:
            where_clause += f" AND {terminal_field} LIKE %(terminal_filter)s"
            params['terminal_filter'] = f'%{terminal_filter}%'

        # 主查询：统计末端节点（包含独立路径数）
        main_query = f"""
        SELECT
            {terminal_field} as terminal,
            count() as trace_count,
            countDistinct(prefix24) as prefix24_count,
            countDistinct(data_center) as data_center_count,
            countDistinct({path_field}) as path_count,
            avg(hop_count) as avg_hop_count
        FROM {table_name}
        WHERE {where_clause}
          AND {terminal_field} != ''
        GROUP BY {terminal_field}
        ORDER BY trace_count DESC
        LIMIT %(limit)s
        """

        result = self.client.execute(main_query, params)

        terminals = []
        for row in result:
            terminal_data = {
                'terminal': row[0],
                'trace_count': row[1],
                'prefix24_count': row[2],
                'data_center_count': row[3],
                'path_count': row[4],
                'avg_hop_count': _safe_float(row[5]),
                'sample_paths': [],
            }

            # 获取示例路径（增加返回数量，支持展开查看）
            if include_paths and row[0]:
                path_query = f"""
                SELECT
                    {path_field},
                    count() as path_count
                FROM {table_name}
                WHERE {where_clause}
                  AND {terminal_field} = %(terminal)s
                  AND {path_field} != ''
                GROUP BY {path_field}
                ORDER BY path_count DESC
                LIMIT 20
                """
                path_params = {**params, 'terminal': row[0]}
                if 'terminal_filter' in path_params:
                    del path_params['terminal_filter']
                path_result = self.client.execute(path_query, path_params)
                terminal_data['sample_paths'] = [
                    {'path': p[0], 'count': p[1]}
                    for p in path_result
                ]

            terminals.append(terminal_data)

        # 获取总统计数据
        total_query = f"""
        SELECT
            count() as total_traces,
            countDistinct({terminal_field}) as unique_terminals
        FROM {table_name}
        WHERE {where_clause}
          AND {terminal_field} != ''
        """
        if 'terminal_filter' in params:
            total_params = {k: v for k, v in params.items() if k != 'limit'}
        else:
            total_params = {k: v for k, v in params.items() if k != 'limit'}
        total_result = self.client.execute(total_query, total_params)

        return {
            'terminals': terminals,
            'total_traces': total_result[0][0] if total_result else 0,
            'unique_terminals': total_result[0][1] if total_result else 0,
            'terminal_type': terminal_type,
            'data_source': 'quarter',  # 使用的是抽样表
        }

    def get_prefix24s_in_terminal(
        self,
        region: str,
        terminal: str,
        terminal_type: str = 'asgeo',
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        top_n: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        获取末端 ASGeo 下的所有 prefix24

        Args:
            terminal: 末端标识，如 "AS12345-US"
            terminal_type: 'as' 或 'asgeo'
        """
        trace_table = f"{region}__quarter_traceroute"
        ping_table = f"{region}__ping"

        where_conditions = []
        params = {'terminal': terminal, 'limit': top_n}

        if terminal_type == 'asgeo':
            terminal_field = 'asgeo_term'
        else:
            terminal_field = 'as_term'

        if start_time:
            where_conditions.append("measure_time >= %(start_time)s")
            params['start_time'] = start_time
        if end_time:
            where_conditions.append("measure_time <= %(end_time)s")
            params['end_time'] = end_time

        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        # 查询该末端下的所有 prefix24
        trace_query = f"""
        SELECT
            prefix24,
            count() as trace_count,
            countDistinct(dst_ip) as unique_ips,
            any(as_path_text) as sample_as_path,
            any(asgeo_path_text) as sample_asgeo_path
        FROM {trace_table}
        WHERE {where_clause}
          AND {terminal_field} = %(terminal)s
          AND prefix24 != ''
        GROUP BY prefix24
        ORDER BY trace_count DESC
        LIMIT %(limit)s
        """

        trace_result = self.client.execute(trace_query, params)

        prefix24s = []
        for row in trace_result:
            prefix24_data = {
                'prefix24': row[0],
                'trace_count': row[1],
                'unique_ips': row[2],
                'sample_as_path': row[3],
                'sample_asgeo_path': row[4],
                'ping_stats': {},
            }

            # 关联 Ping 数据
            ping_query = f"""
            SELECT
                count() as sample_count,
                avg(rtt_ms) as mean_rtt,
                median(rtt_ms) as median_rtt,
                quantile(0.90)(rtt_ms) as p90_rtt,
                quantile(0.95)(rtt_ms) as p95_rtt,
                quantile(0.99)(rtt_ms) as p99_rtt,
                min(rtt_ms) as min_rtt,
                max(rtt_ms) as max_rtt
            FROM {ping_table}
            WHERE prefix24 = %(prefix24)s
            """
            ping_params = {'prefix24': row[0]}

            if start_time:
                ping_query += " AND measure_time >= %(start_time)s"
                ping_params['start_time'] = start_time
            if end_time:
                ping_query += " AND measure_time <= %(end_time)s"
                ping_params['end_time'] = end_time

            ping_result = self.client.execute(ping_query, ping_params)

            if ping_result and ping_result[0][0] > 0:
                prefix24_data['ping_stats'] = {
                    'sample_count': ping_result[0][0],
                    'mean_rtt': ping_result[0][1],
                    'median_rtt': ping_result[0][2],
                    'p90_rtt': ping_result[0][3],
                    'p95_rtt': ping_result[0][4],
                    'p99_rtt': ping_result[0][5],
                    'min_rtt': ping_result[0][6],
                    'max_rtt': ping_result[0][7],
                }

            prefix24s.append(prefix24_data)

        return prefix24s

    def correlate_ping_trace(
        self,
        region: str,
        prefix24: str,
        recent_hours: int = 24,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        关联 Ping 和 Traceroute 数据

        由于 Traceroute 是 1/4 抽样，查找最近 N 小时的 Ping 数据补充

        Args:
            prefix24: /24 前缀
            recent_hours: 查找最近 N 小时的 Ping 数据
        """
        trace_table = f"{region}__quarter_traceroute"
        ping_table = f"{region}__ping"

        params = {'prefix24': prefix24}

        if start_time:
            params['start_time'] = start_time
        if end_time:
            params['end_time'] = end_time

        time_filter = ""
        if start_time and end_time:
            time_filter = "AND measure_time BETWEEN %(start_time)s AND %(end_time)s"

        # Traceroute 数据 (1/4 抽样)
        trace_query = f"""
        SELECT
            as_path_text,
            asgeo_path_text,
            ip_path_text,
            hop_count,
            reached_target,
            measure_time,
            data_center
        FROM {trace_table}
        WHERE prefix24 = %(prefix24)s {time_filter}
        ORDER BY measure_time DESC
        LIMIT 100
        """

        trace_result = self.client.execute(trace_query, params)

        # 构建路径统计
        path_stats = {}
        for row in trace_result:
            as_path = row[0]
            if as_path not in path_stats:
                path_stats[as_path] = {
                    'as_path': as_path,
                    'asgeo_path': row[1],
                    'ip_path': row[2],
                    'count': 0,
                    'hop_counts': [],
                    'reached_count': 0,
                }
            path_stats[as_path]['count'] += 1
            path_stats[as_path]['hop_counts'].append(row[3])
            if row[4]:
                path_stats[as_path]['reached_count'] += 1

        paths = list(path_stats.values())
        for p in paths:
            p['avg_hop_count'] = sum(p['hop_counts']) / len(p['hop_counts']) if p['hop_counts'] else 0
            del p['hop_counts']

        # Ping 数据 (全量) - 查找最近 N 小时
        recent_time_filter = ""
        if recent_hours > 0:
            recent_time_filter = f"AND measure_time >= now() - INTERVAL {recent_hours} HOUR"

        ping_query = f"""
        SELECT
            count() as sample_count,
            avg(rtt_ms) as mean_rtt,
            median(rtt_ms) as median_rtt,
            stddevPop(rtt_ms) as std_rtt,
            quantile(0.50)(rtt_ms) as p50_rtt,
            quantile(0.90)(rtt_ms) as p90_rtt,
            quantile(0.95)(rtt_ms) as p95_rtt,
            quantile(0.99)(rtt_ms) as p99_rtt,
            min(rtt_ms) as min_rtt,
            max(rtt_ms) as max_rtt,
            countDistinct(dst_ip) as unique_ips,
            any(ip_asn) as asn,
            any(ip_as_name) as as_name,
            any(ip_geo_country) as geo_country
        FROM {ping_table}
        WHERE prefix24 = %(prefix24)s {recent_time_filter}
        """

        ping_result = self.client.execute(ping_query, params)

        ping_stats = {}
        if ping_result and ping_result[0][0] > 0:
            ping_stats = {
                'sample_count': ping_result[0][0],
                'mean_rtt': ping_result[0][1],
                'median_rtt': ping_result[0][2],
                'std_rtt': ping_result[0][3],
                'p50_rtt': ping_result[0][4],
                'p90_rtt': ping_result[0][5],
                'p95_rtt': ping_result[0][6],
                'p99_rtt': ping_result[0][7],
                'min_rtt': ping_result[0][8],
                'max_rtt': ping_result[0][9],
                'unique_ips': ping_result[0][10],
            }

        return {
            'prefix24': prefix24,
            'trace_data': {
                'sample_type': 'quarter',
                'sampling_rate': 0.25,
                'paths': paths,
                'total_traces': len(trace_result),
            },
            'ping_data': {
                'sample_type': 'full',
                'sampling_rate': 1.0,
                'stats': ping_stats,
            },
            'correlation': {
                'asn': ping_result[0][11] if ping_result and ping_result[0] else None,
                'as_name': ping_result[0][12] if ping_result and ping_result[0] else None,
                'geo_country': ping_result[0][13] if ping_result and ping_result[0] else None,
            },
        }

    def get_data_source_info(self, region: str) -> Dict[str, Any]:
        """
        获取数据源信息

        Returns:
            data_source: "full" 或 "quarter"
            table_name: 使用的表名
            sampling_rate: 抽样率
        """
        # 默认使用 quarter_traceroute (1/4 抽样)
        quarter_table = f"{region}__quarter_traceroute"
        full_table = f"{region}__trace"

        try:
            # 检查 quarter 表是否存在且有数据
            quarter_count_query = f"SELECT count() FROM {quarter_table} LIMIT 1"
            quarter_result = self.client.execute(quarter_count_query)
            quarter_count = quarter_result[0][0] if quarter_result else 0

            if quarter_count > 0:
                return {
                    'data_source': 'quarter',
                    'table_name': quarter_table,
                    'sampling_rate': 0.25,
                    'record_count': quarter_count,
                    'description': '1/4 抽样数据，适合大规模分析',
                }
        except Exception:
            pass

        try:
            # 检查 full 表
            full_count_query = f"SELECT count() FROM {full_table} LIMIT 1"
            full_result = self.client.execute(full_count_query)
            full_count = full_result[0][0] if full_result else 0

            if full_count > 0:
                return {
                    'data_source': 'full',
                    'table_name': full_table,
                    'sampling_rate': 1.0,
                    'record_count': full_count,
                    'description': '全量数据',
                }
        except Exception:
            pass

        return {
            'data_source': 'unknown',
            'table_name': '',
            'sampling_rate': 0,
            'record_count': 0,
            'description': '未找到 Traceroute 数据',
        }

    def hierarchical_analysis(
        self,
        region: str,
        hierarchy: List[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        config: Optional[AnalysisConfig] = None,
        outlier_filter: Optional[Dict[str, float]] = None,
        **filters
    ) -> Dict[str, Any]:
        """
        分层分析 - 支持逐层下钻

        Args:
            hierarchy: 层级顺序，如 ['time', 'asgeo', 'prefix24']
                     - time: 时间维度
                     - asn: AS 维度
                     - asgeo: AS+Geo 维度
                     - prefix24: /24 前缀维度
                     - country: 国家维度
            outlier_filter: 极端值过滤配置 {'percentile_min': 5, 'percentile_max': 95}

        Returns:
            分层聚合的统计结果
        """
        config = config or AnalysisConfig()
        if hierarchy is None:
            hierarchy = ['time', 'asgeo', 'prefix24']

        table_name = f"{region}__ping"

        where_conditions = ["rtt_ms > 0"]  # 过滤无效数据
        params = {}

        if start_time:
            where_conditions.append("measure_time >= %(start_time)s")
            params['start_time'] = start_time
        if end_time:
            where_conditions.append("measure_time <= %(end_time)s")
            params['end_time'] = end_time

        for key, value in filters.items():
            if value is not None:
                where_conditions.append(f"{key} = %({key})s")
                params[key] = value

        where_clause = " AND ".join(where_conditions)

        # 构建分组字段映射
        group_field_map = {
            'time': 'toStartOfHour(measure_time) as time_bucket',
            'asn': 'ip_asn',
            'asgeo': "concat(toString(ip_asn), '_', ifNull(ip_geo_country, 'Unknown')) as asgeo",
            'prefix24': 'prefix24',
            'country': 'ip_geo_country',
            'data_center': 'data_center',
        }

        # 构建层级分组
        group_fields = []
        select_fields = []
        for level in hierarchy:
            if level in group_field_map:
                select_fields.append(group_field_map[level])
                if ' as ' in group_field_map[level]:
                    # 提取别名
                    alias = group_field_map[level].split(' as ')[1]
                    group_fields.append(alias)
                else:
                    group_fields.append(group_field_map[level])

        if not group_fields:
            return {'error': 'Invalid hierarchy configuration'}

        # 构建极端值过滤子查询
        outlier_condition = ""
        if outlier_filter:
            min_pct = outlier_filter.get('percentile_min', 0)
            max_pct = outlier_filter.get('percentile_max', 100)
            if min_pct > 0 or max_pct < 100:
                outlier_condition = f"""
                AND rtt_ms >= (SELECT quantile({min_pct/100})(rtt_ms) FROM {table_name} WHERE {where_clause})
                AND rtt_ms <= (SELECT quantile({max_pct/100})(rtt_ms) FROM {table_name} WHERE {where_clause})
                """

        percentile_queries = ", ".join([
            f"quantile({p/100})(rtt_ms) as p{p}_rtt"
            for p in config.percentiles
        ])

        query = f"""
        SELECT
            {', '.join(select_fields)},
            count() as sample_count,
            avg(rtt_ms) as mean_rtt,
            median(rtt_ms) as median_rtt,
            min(rtt_ms) as min_rtt,
            max(rtt_ms) as max_rtt,
            stddevPop(rtt_ms) as std_rtt,
            stddevPop(rtt_ms) / avg(rtt_ms) as cv,
            quantile(0.75)(rtt_ms) - quantile(0.25)(rtt_ms) as iqr,
            {percentile_queries},
            uniqExact(dst_ip) as unique_ips
        FROM {table_name}
        WHERE {where_clause}
        {outlier_condition}
        GROUP BY {', '.join(group_fields)}
        ORDER BY sample_count DESC
        LIMIT 1000
        """

        try:
            result = self.client.execute(query, params)
        except Exception as e:
            logger.error(f"Hierarchical analysis failed: {e}")
            return {'error': str(e)}

        # 构建层级树结构
        hierarchy_tree = {}
        flat_data = []

        for row in result:
            # 解析行数据
            level_values = row[:len(group_fields)]
            stats_start = len(group_fields)

            item = {
                'levels': {hierarchy[i]: level_values[i] for i in range(len(hierarchy))},
                'sample_count': row[stats_start],
                'mean_rtt': row[stats_start + 1],
                'median_rtt': row[stats_start + 2],
                'min_rtt': row[stats_start + 3],
                'max_rtt': row[stats_start + 4],
                'std_rtt': row[stats_start + 5],
                'cv': row[stats_start + 6],  # 变异系数
                'iqr': row[stats_start + 7],  # 四分位距
                'percentiles': {
                    f'p{p}': row[stats_start + 8 + i]
                    for i, p in enumerate(config.percentiles)
                },
                'unique_ips': row[stats_start + 8 + len(config.percentiles)],
            }
            flat_data.append(item)

            # 构建树结构
            current_level = hierarchy_tree
            for i, level in enumerate(hierarchy[:-1]):
                level_value = str(level_values[i])
                if level_value not in current_level:
                    current_level[level_value] = {'_stats': {}, '_children': {}}
                current_level = current_level[level_value]['_children']

            # 最后一级
            last_level_value = str(level_values[-1])
            if last_level_value not in current_level:
                current_level[last_level_value] = {'_stats': {}}
            current_level[last_level_value]['_stats'] = item

        return {
            'hierarchy': hierarchy,
            'outlier_filter': outlier_filter,
            'total_groups': len(flat_data),
            'flat_data': flat_data[:100],  # 限制返回数量
            'hierarchy_tree': hierarchy_tree,
            'statistics': {
                'total_samples': sum(d['sample_count'] for d in flat_data),
                'unique_combinations': len(flat_data),
            }
        }

    def drill_down(
        self,
        region: str,
        level: str,
        level_value: Any,
        next_level: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        config: Optional[AnalysisConfig] = None,
        **filters
    ) -> Dict[str, Any]:
        """
        下钻分析 - 从一个层级钻取到下一层级

        Args:
            level: 当前层级 (asn, asgeo, prefix24, country)
            level_value: 当前层级的值
            next_level: 下一层级

        Returns:
            下一层级的聚合统计
        """
        config = config or AnalysisConfig()
        table_name = f"{region}__ping"

        where_conditions = ["rtt_ms > 0"]
        params = {}

        # 添加当前层级的过滤条件
        level_field_map = {
            'asn': 'ip_asn',
            'asgeo': "concat(toString(ip_asn), '_', ifNull(ip_geo_country, 'Unknown'))",
            'prefix24': 'prefix24',
            'country': 'ip_geo_country',
            'data_center': 'data_center',
        }

        if level in level_field_map:
            if level == 'asgeo':
                # 解析 asgeo 值 (格式: "ASN_COUNTRY")
                parts = str(level_value).split('_')
                if len(parts) >= 2:
                    where_conditions.append("ip_asn = %(asn)s")
                    params['asn'] = int(parts[0])
                    where_conditions.append("ip_geo_country = %(country)s")
                    params['country'] = parts[1]
                else:
                    where_conditions.append(f"{level_field_map[level]} = %(level_value)s")
                    params['level_value'] = level_value
            else:
                where_conditions.append(f"{level_field_map[level]} = %(level_value)s")
                params['level_value'] = level_value

        if start_time:
            where_conditions.append("measure_time >= %(start_time)s")
            params['start_time'] = start_time
        if end_time:
            where_conditions.append("measure_time <= %(end_time)s")
            params['end_time'] = end_time

        for key, value in filters.items():
            if value is not None:
                where_conditions.append(f"{key} = %({key})s")
                params[key] = value

        where_clause = " AND ".join(where_conditions)

        next_field = level_field_map.get(next_level, next_level)
        percentile_queries = ", ".join([
            f"quantile({p/100})(rtt_ms) as p{p}_rtt"
            for p in config.percentiles
        ])

        query = f"""
        SELECT
            {next_field} as {next_level},
            count() as sample_count,
            avg(rtt_ms) as mean_rtt,
            median(rtt_ms) as median_rtt,
            min(rtt_ms) as min_rtt,
            max(rtt_ms) as max_rtt,
            stddevPop(rtt_ms) as std_rtt,
            {percentile_queries},
            uniqExact(dst_ip) as unique_ips
        FROM {table_name}
        WHERE {where_clause}
        GROUP BY {next_level}
        ORDER BY sample_count DESC
        LIMIT 100
        """

        try:
            result = self.client.execute(query, params)
        except Exception as e:
            logger.error(f"Drill down analysis failed: {e}")
            return {'error': str(e)}

        data = []
        for row in result:
            item = {
                next_level: row[0],
                'sample_count': row[1],
                'mean_rtt': row[2],
                'median_rtt': row[3],
                'min_rtt': row[4],
                'max_rtt': row[5],
                'std_rtt': row[6],
                'percentiles': {
                    f'p{p}': row[7 + i]
                    for i, p in enumerate(config.percentiles)
                },
                'unique_ips': row[7 + len(config.percentiles)],
            }
            data.append(item)

        return {
            'parent_level': level,
            'parent_value': level_value,
            'child_level': next_level,
            'children': data,
            'total_children': len(data),
        }

    def list_terminals(
        self,
        region: str,
        terminal_type: str = 'asgeo',
        search: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        获取可用的末端 AS/ASGeo 列表（支持模糊搜索）

        Args:
            terminal_type: 'as' 或 'asgeo'
            search: 模糊搜索关键词（支持 AS 号、国家代码等）
            limit: 返回数量限制

        Returns:
            末端节点列表，包含标识、路径数、样本数等信息
        """
        table_name = f"{region}__quarter_traceroute"

        # 根据末端类型选择字段
        if terminal_type == 'asgeo':
            terminal_field = 'asgeo_term'
        else:
            terminal_field = 'as_term'

        where_clause = f"{terminal_field} != ''"
        params = {'limit': limit}

        # 添加搜索过滤
        if search:
            where_clause += f" AND {terminal_field} LIKE %(search)s"
            params['search'] = f'%{search}%'

        query = f"""
        SELECT
            {terminal_field} as terminal,
            count() as trace_count,
            countDistinct(prefix24) as prefix24_count,
            countDistinct(data_center) as data_center_count,
            sum(if(reached_target, 1, 0)) as reached_count
        FROM {table_name}
        WHERE {where_clause}
        GROUP BY {terminal_field}
        ORDER BY trace_count DESC
        LIMIT %(limit)s
        """

        result = self.client.execute(query, params)

        return [
            {
                'terminal': row[0],
                'trace_count': row[1],
                'prefix24_count': row[2],
                'data_center_count': row[3],
                'reached_count': row[4],
                'reach_rate': row[4] / row[1] if row[1] > 0 else 0,
            }
            for row in result
        ]

    def analyze_paths_with_filter(
        self,
        region: str,
        path_type: str = 'as',
        terminal_as: Optional[str] = None,
        terminal_asgeo: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        top_n: int = 50,
        data_center: Optional[str] = None,
        trace_type: str = 'quarter',
    ) -> Dict[str, Any]:
        """
        带过滤条件的路径分析（只分析成功到达目标的路径）

        Args:
            path_type: 'as' 或 'asgeo'
            terminal_as: 限定末端 AS（如 "AS12345"）
            terminal_asgeo: 限定末端 ASGeo（如 "AS12345-US"）
            data_center: 数据中心筛选
            trace_type: 数据类型 'quarter' 或 'full'
        """
        # 根据数据类型选择表
        if trace_type == 'full':
            table_name = f"{region}__traceroute"
        else:
            table_name = f"{region}__quarter_traceroute"

        where_conditions = ["reached_target = 1"]  # 只分析成功到达的路径
        params = {'limit': top_n}

        if start_time:
            where_conditions.append("measure_time >= %(start_time)s")
            params['start_time'] = start_time
        if end_time:
            where_conditions.append("measure_time <= %(end_time)s")
            params['end_time'] = end_time

        # 数据中心筛选
        if data_center:
            where_conditions.append("data_center = %(data_center)s")
            params['data_center'] = data_center

        # 末端节点过滤
        if terminal_as:
            where_conditions.append("as_term = %(terminal_as)s")
            params['terminal_as'] = terminal_as
        if terminal_asgeo:
            where_conditions.append("asgeo_term = %(terminal_asgeo)s")
            params['terminal_asgeo'] = terminal_asgeo

        where_clause = " AND ".join(where_conditions)

        # 根据路径类型选择字段
        if path_type == 'asgeo':
            path_field = 'asgeo_path_text'
        else:
            path_field = 'as_path_text'

        # 路径统计查询
        path_query = f"""
        SELECT
            {path_field} as path,
            count() as occurrence_count,
            avg(hop_count) as avg_hop_count,
            countDistinct(prefix24) as prefix24_count,
            countDistinct(data_center) as data_center_count
        FROM {table_name}
        WHERE {where_clause}
          AND {path_field} != ''
        GROUP BY {path_field}
        ORDER BY occurrence_count DESC
        LIMIT %(limit)s
        """

        path_result = self.client.execute(path_query, params)

        paths = [
            {
                'path': row[0],
                'occurrence_count': row[1],
                'avg_hop_count': _safe_float(row[2]),
                'prefix24_count': row[3],
                'data_center_count': row[4],
            }
            for row in path_result
        ]

        # 总体统计
        total_query = f"""
        SELECT
            count() as total_traces,
            countDistinct({path_field}) as unique_paths,
            avg(hop_count) as avg_hop_count
        FROM {table_name}
        WHERE {where_clause}
          AND {path_field} != ''
        """
        total_result = self.client.execute(total_query, params)

        # 获取末端节点分布
        terminal_field = 'asgeo_term' if path_type == 'asgeo' else 'as_term'
        terminal_query = f"""
        SELECT
            {terminal_field} as terminal,
            count() as trace_count
        FROM {table_name}
        WHERE {where_clause}
          AND {terminal_field} != ''
        GROUP BY {terminal_field}
        ORDER BY trace_count DESC
        LIMIT 20
        """
        terminal_result = self.client.execute(terminal_query, params)

        terminal_distribution = [
            {'terminal': row[0], 'trace_count': row[1]}
            for row in terminal_result
        ]

        return {
            'paths': paths,
            'total_traces': total_result[0][0] if total_result else 0,
            'unique_paths': total_result[0][1] if total_result else 0,
            'avg_hop_count': _safe_float(total_result[0][2]) if total_result else 0,
            'terminal_distribution': terminal_distribution,
            'filters': {
                'terminal_as': terminal_as,
                'terminal_asgeo': terminal_asgeo,
            },
        }

    def search_paths(
        self,
        region: str,
        path_type: str = 'as',
        search: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        搜索路径列表（用于下拉搜索，只返回成功到达的路径）

        Args:
            region: 地区
            path_type: 'as' 或 'asgeo'
            search: 搜索关键词
            limit: 返回数量限制

        Returns:
            [{path, trace_count}, ...]
        """
        table_name = f"{region}__quarter_traceroute"
        path_field = 'asgeo_path_text' if path_type == 'asgeo' else 'as_path_text'

        params: Dict[str, Any] = {'limit': limit}

        where_conditions = [f"{path_field} != ''", "reached_target = 1"]  # 只返回成功到达的路径
        if search:
            where_conditions.append(f"{path_field} LIKE %(search)s")
            params['search'] = f'%{search}%'

        where_clause = " AND ".join(where_conditions)

        query = f"""
        SELECT
            {path_field} as path,
            count() as trace_count
        FROM {table_name}
        WHERE {where_clause}
        GROUP BY {path_field}
        ORDER BY trace_count DESC
        LIMIT %(limit)s
        """

        result = self.client.execute(query, params)

        return [
            {
                'path': row[0],
                'trace_count': row[1],
            }
            for row in result
        ]

    def get_path_detail(
        self,
        region: str,
        path: str,
        path_type: str = 'as',
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        top_n: int = 50,
    ) -> Dict[str, Any]:
        """
        获取路径详情：关联的末端节点和 prefix24（只分析成功到达的路径）

        Args:
            region: 地区
            path: AS 路径或 ASGeo 路径字符串
            path_type: 'as' 或 'asgeo'
            start_time: 开始时间
            end_time: 结束时间
            top_n: 返回数量限制

        Returns:
            {
                terminals: [{terminal, trace_count, prefix24_count}],
                prefix24s: [{prefix24, trace_count, unique_ips, sample_terminal}],
                data_centers: [{data_center, count}],
                total_traces: int,
                unique_terminals: int,
                unique_prefix24s: int
            }
        """
        table_name = f"{region}__quarter_traceroute"

        # 选择路径字段
        path_field = 'asgeo_path_text' if path_type == 'asgeo' else 'as_path_text'
        terminal_field = 'asgeo_term' if path_type == 'asgeo' else 'as_term'

        # 构建时间过滤
        time_filter = ""
        params = {'path': path, 'limit': top_n}

        if start_time:
            time_filter += " AND measure_time >= %(start_time)s"
            params['start_time'] = start_time
        if end_time:
            time_filter += " AND measure_time <= %(end_time)s"
            params['end_time'] = end_time

        # 查询关联的末端节点（只统计成功到达的）
        terminal_query = f"""
        SELECT
            {terminal_field} as terminal,
            count() as trace_count,
            countDistinct(prefix24) as prefix24_count,
            avg(hop_count) as avg_hop_count
        FROM {table_name}
        WHERE {path_field} = %(path)s {time_filter}
          AND {terminal_field} != ''
          AND reached_target = 1
        GROUP BY {terminal_field}
        ORDER BY trace_count DESC
        LIMIT %(limit)s
        """

        terminal_result = self.client.execute(terminal_query, params)

        terminals = [
            {
                'terminal': row[0],
                'trace_count': row[1],
                'prefix24_count': row[2],
                'avg_hop_count': _safe_float(row[3]),
            }
            for row in terminal_result
        ]

        # 查询关联的 prefix24
        prefix24_query = f"""
        SELECT
            prefix24,
            count() as trace_count,
            countDistinct(dst_ip) as unique_ips,
            any({terminal_field}) as sample_terminal
        FROM {table_name}
        WHERE {path_field} = %(path)s {time_filter}
          AND prefix24 != ''
          AND reached_target = 1
        GROUP BY prefix24
        ORDER BY trace_count DESC
        LIMIT %(limit)s
        """

        prefix24_result = self.client.execute(prefix24_query, params)

        prefix24s = [
            {
                'prefix24': row[0],
                'trace_count': row[1],
                'unique_ips': row[2],
                'sample_terminal': row[3],
            }
            for row in prefix24_result
        ]

        # 查询数据中心分布
        dc_query = f"""
        SELECT
            data_center,
            count() as count
        FROM {table_name}
        WHERE {path_field} = %(path)s {time_filter}
          AND data_center != ''
          AND reached_target = 1
        GROUP BY data_center
        ORDER BY count DESC
        LIMIT 20
        """

        dc_result = self.client.execute(dc_query, params)

        data_centers = [
            {'data_center': row[0], 'count': row[1]}
            for row in dc_result
        ]

        # 总计统计
        total_query = f"""
        SELECT
            count() as total_traces,
            countDistinct({terminal_field}) as unique_terminals,
            countDistinct(prefix24) as unique_prefix24s,
            avg(hop_count) as avg_hop_count
        FROM {table_name}
        WHERE {path_field} = %(path)s {time_filter}
          AND reached_target = 1
        """

        total_result = self.client.execute(total_query, params)

        return {
            'path': path,
            'path_type': path_type,
            'terminals': terminals,
            'prefix24s': prefix24s,
            'data_centers': data_centers,
            'total_traces': total_result[0][0] if total_result else 0,
            'unique_terminals': total_result[0][1] if total_result else 0,
            'unique_prefix24s': total_result[0][2] if total_result else 0,
            'avg_hop_count': _safe_float(total_result[0][3]) if total_result else 0,
        }

    def analyze_path_ping_trend(
        self,
        region: str,
        path: str,
        path_type: str = 'as',
        interval: str = 'hour',
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        percentiles: List[int] = None,
        asn: Optional[int] = None,
        asgeo: Optional[str] = None,
        isp: Optional[str] = None,
        data_center: Optional[str] = None,
        outlier_filter_min: Optional[int] = None,
        outlier_filter_max: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        分析路径关联的 Ping 时序数据

        Args:
            region: 地区
            path: AS 路径或 ASGeo 路径字符串
            path_type: 'as' 或 'asgeo'
            interval: 时间粒度 (minute, hour, day)
            start_time: 开始时间
            end_time: 结束时间
            percentiles: 要计算的分位数
            asn: AS 号筛选
            asgeo: ASGeo 筛选 (格式: "ASN_Country")
            isp: 运营商筛选
            data_center: 数据中心筛选
            outlier_filter_min: 极端值过滤下界分位数
            outlier_filter_max: 极端值过滤上界分位数

        Returns:
            {
                time_series: [{time, sample_count, mean_rtt, median_rtt, ...}],
                prefix24_count: int,
                summary: {total_samples, mean_rtt, median_rtt, ...}
            }
        """
        if percentiles is None:
            percentiles = [50, 90, 95, 99]

        trace_table = f"{region}__quarter_traceroute"
        ping_table = f"{region}__ping"

        # 选择路径字段
        path_field = 'asgeo_path_text' if path_type == 'asgeo' else 'as_path_text'

        # 构建时间过滤
        time_filter = ""
        params = {'path': path}

        if start_time:
            time_filter += " AND measure_time >= %(start_time)s"
            params['start_time'] = start_time
        if end_time:
            time_filter += " AND measure_time <= %(end_time)s"
            params['end_time'] = end_time

        # 1. 获取路径关联的所有 prefix24（只统计成功到达的）
        prefix24_query = f"""
        SELECT DISTINCT prefix24
        FROM {trace_table}
        WHERE {path_field} = %(path)s {time_filter}
          AND prefix24 != ''
          AND reached_target = 1
        """

        prefix24_result = self.client.execute(prefix24_query, params)
        prefix24s = [row[0] for row in prefix24_result]

        if not prefix24s:
            return {
                'path': path,
                'path_type': path_type,
                'time_series': [],
                'prefix24_count': 0,
                'summary': {},
            }

        # 2. 使用 prefix24 列表查询 Ping 时序数据
        interval_func = {
            'minute': 'toStartOfMinute',
            'hour': 'toStartOfHour',
            'day': 'toStartOfDay',
        }.get(interval, 'toStartOfHour')

        percentile_queries = ", ".join([
            f"quantile({p/100})(rtt_ms) as p{p}_rtt"
            for p in percentiles
        ])

        # 构建 IN 子句
        prefix24s_str = ", ".join([f"'{p}'" for p in prefix24s])

        # Ping 表过滤条件
        ping_filter = f"prefix24 IN ({prefix24s_str})"

        if start_time:
            ping_filter += " AND measure_time >= %(start_time)s"
        if end_time:
            ping_filter += " AND measure_time <= %(end_time)s"

        # 添加额外筛选条件
        if asn is not None:
            ping_filter += " AND ip_asn = %(asn)s"
            params['asn'] = asn

        if asgeo:
            # asgeo 格式: "ASN_Country"
            parts = asgeo.split('_')
            if len(parts) >= 2:
                ping_filter += " AND ip_asn = %(asgeo_asn)s AND ip_geo_country = %(asgeo_country)s"
                params['asgeo_asn'] = int(parts[0]) if parts[0].isdigit() else 0
                params['asgeo_country'] = parts[1]

        if isp:
            ping_filter += " AND ip_isp_domain = %(isp)s"
            params['isp'] = isp

        if data_center:
            ping_filter += " AND data_center = %(data_center)s"
            params['data_center'] = data_center

        # 极端值过滤
        if outlier_filter_min is not None and outlier_filter_max is not None:
            ping_filter += f" AND rtt_ms >= quantile({outlier_filter_min/100})(rtt_ms) AND rtt_ms <= quantile({outlier_filter_max/100})(rtt_ms)"

        time_series_query = f"""
        SELECT
            {interval_func}(measure_time) as time_bucket,
            count() as sample_count,
            avg(rtt_ms) as mean_rtt,
            median(rtt_ms) as median_rtt,
            min(rtt_ms) as min_rtt,
            max(rtt_ms) as max_rtt,
            stddevPop(rtt_ms) as std_rtt,
            {percentile_queries}
        FROM {ping_table}
        WHERE {ping_filter}
        GROUP BY time_bucket
        ORDER BY time_bucket
        """

        time_series_result = self.client.execute(time_series_query, params)

        time_series = []
        for row in time_series_result:
            item = {
                'time': row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                'sample_count': row[1],
                'mean_rtt': _safe_float(row[2]),
                'median_rtt': _safe_float(row[3]),
                'min_rtt': _safe_float(row[4]),
                'max_rtt': _safe_float(row[5]),
                'std_rtt': _safe_float(row[6]),
                'percentiles': {
                    f'p{p}': _safe_float(row[7 + i])
                    for i, p in enumerate(percentiles)
                },
            }
            time_series.append(item)

        # 3. 计算总体统计
        summary_query = f"""
        SELECT
            count() as total_samples,
            avg(rtt_ms) as mean_rtt,
            median(rtt_ms) as median_rtt,
            min(rtt_ms) as min_rtt,
            max(rtt_ms) as max_rtt,
            stddevPop(rtt_ms) as std_rtt,
            {percentile_queries}
        FROM {ping_table}
        WHERE {ping_filter}
        """

        summary_result = self.client.execute(summary_query, params)

        summary = {}
        if summary_result and summary_result[0][0] > 0:
            summary = {
                'total_samples': summary_result[0][0],
                'mean_rtt': _safe_float(summary_result[0][1]),
                'median_rtt': _safe_float(summary_result[0][2]),
                'min_rtt': _safe_float(summary_result[0][3]),
                'max_rtt': _safe_float(summary_result[0][4]),
                'std_rtt': _safe_float(summary_result[0][5]),
                'percentiles': {
                    f'p{p}': _safe_float(summary_result[0][6 + i])
                    for i, p in enumerate(percentiles)
                },
            }

        return {
            'path': path,
            'path_type': path_type,
            'interval': interval,
            'time_series': time_series,
            'prefix24_count': len(prefix24s),
            'prefix24s': prefix24s[:20],  # 只返回前 20 个
            'summary': summary,
        }

    def get_path_filter_options(
        self,
        region: str,
        path: str,
        path_type: str = 'as',
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        获取路径关联的筛选选项（AS/ASGeo/运营商/数据中心/Prefix24）

        用于前端下拉框选择，只返回这条路径实际包含的选项。

        Returns:
            {
                as_options: [{asn, as_name, sample_count}],
                asgeo_options: [{asgeo, sample_count}],
                isp_options: [{isp, sample_count}],
                data_center_options: [{data_center, sample_count}],
                prefix24_options: [{prefix24, sample_count}],
            }
        """
        trace_table = f"{region}__quarter_traceroute"
        ping_table = f"{region}__ping"

        path_field = 'asgeo_path_text' if path_type == 'asgeo' else 'as_path_text'

        time_filter = ""
        params = {'path': path}

        if start_time:
            time_filter += " AND measure_time >= %(start_time)s"
            params['start_time'] = start_time
        if end_time:
            time_filter += " AND measure_time <= %(end_time)s"
            params['end_time'] = end_time

        # 1. 获取路径关联的所有 prefix24
        prefix24_query = f"""
        SELECT DISTINCT prefix24
        FROM {trace_table}
        WHERE {path_field} = %(path)s {time_filter}
          AND prefix24 != ''
          AND reached_target = 1
        """

        logger.info(f"[get_path_filter_options] Querying prefix24 for path: {path}, path_field: {path_field}")
        prefix24_result = self.client.execute(prefix24_query, params)
        prefix24s = [row[0] for row in prefix24_result]
        logger.info(f"[get_path_filter_options] Found {len(prefix24s)} prefix24s: {prefix24s[:5]}...")

        if not prefix24s:
            logger.warning(f"[get_path_filter_options] No prefix24s found for path: {path}")
            return {
                'as_options': [],
                'asgeo_options': [],
                'isp_options': [],
                'data_center_options': [],
                'prefix24_options': [],
            }

        prefix24s_str = ", ".join([f"'{p}'" for p in prefix24s])

        # 2. 查询 Ping 表中的筛选选项
        ping_time_filter = ""
        if start_time:
            ping_time_filter += " AND measure_time >= %(start_time)s"
        if end_time:
            ping_time_filter += " AND measure_time <= %(end_time)s"

        # AS 选项
        as_query = f"""
        SELECT
            ip_asn as asn,
            any(ip_as_name) as as_name,
            count() as sample_count
        FROM {ping_table}
        WHERE prefix24 IN ({prefix24s_str}) {ping_time_filter}
          AND ip_asn > 0
        GROUP BY ip_asn
        ORDER BY sample_count DESC
        LIMIT 100
        """
        as_result = self.client.execute(as_query, params)
        as_options = [
            {'asn': row[0], 'as_name': row[1] or '', 'sample_count': row[2]}
            for row in as_result
        ]

        # ASGeo 选项
        asgeo_query = f"""
        SELECT
            concat(toString(ip_asn), '_', ifNull(ip_geo_country, 'Unknown')) as asgeo,
            count() as sample_count
        FROM {ping_table}
        WHERE prefix24 IN ({prefix24s_str}) {ping_time_filter}
          AND ip_asn > 0
        GROUP BY asgeo
        ORDER BY sample_count DESC
        LIMIT 100
        """
        asgeo_result = self.client.execute(asgeo_query, params)
        asgeo_options = [
            {'asgeo': row[0], 'sample_count': row[1]}
            for row in asgeo_result
        ]

        # ISP 选项 - 使用 try-except 处理列不存在的情况
        isp_options = []
        try:
            isp_query = f"""
            SELECT
                ip_isp_domain as isp,
                count() as sample_count
            FROM {ping_table}
            WHERE prefix24 IN ({prefix24s_str}) {ping_time_filter}
              AND ip_isp_domain != ''
            GROUP BY ip_isp_domain
            ORDER BY sample_count DESC
            LIMIT 100
            """
            isp_result = self.client.execute(isp_query, params)
            isp_options = [
                {'isp': row[0], 'sample_count': row[1]}
                for row in isp_result
            ]
        except Exception as e:
            logger.warning(f"ISP column not available in {ping_table}: {e}")

        # 数据中心选项 - 使用 try-except 处理列不存在的情况
        data_center_options = []
        try:
            dc_query = f"""
            SELECT
                data_center,
                count() as sample_count
            FROM {ping_table}
            WHERE prefix24 IN ({prefix24s_str}) {ping_time_filter}
              AND data_center != ''
            GROUP BY data_center
            ORDER BY sample_count DESC
            LIMIT 100
            """
            dc_result = self.client.execute(dc_query, params)
            data_center_options = [
                {'data_center': row[0], 'sample_count': row[1]}
                for row in dc_result
            ]
        except Exception as e:
            logger.warning(f"data_center column not available in {ping_table}: {e}")

        # Prefix24 选项
        p24_query = f"""
        SELECT
            prefix24,
            count() as sample_count
        FROM {ping_table}
        WHERE prefix24 IN ({prefix24s_str}) {ping_time_filter}
        GROUP BY prefix24
        ORDER BY sample_count DESC
        LIMIT 100
        """
        p24_result = self.client.execute(p24_query, params)
        prefix24_options = [
            {'prefix24': row[0], 'sample_count': row[1]}
            for row in p24_result
        ]

        logger.info(f"[get_path_filter_options] Results: AS={len(as_options)}, ASGeo={len(asgeo_options)}, ISP={len(isp_options)}, DC={len(data_center_options)}, Prefix24={len(prefix24_options)}")

        return {
            'as_options': as_options,
            'asgeo_options': asgeo_options,
            'isp_options': isp_options,
            'data_center_options': data_center_options,
            'prefix24_options': prefix24_options,
        }
