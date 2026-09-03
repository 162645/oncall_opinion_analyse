"""
Ping 数据分析器
提供 Ping 测量数据的分析功能
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict

from .statistics import calculate_statistics, calculate_percentile, detect_anomalies


class PingAnalyzer:
    """
    Ping 数据分析器

    功能:
    - RTT 统计分析
    - 按 AS/ASGeo/前缀分组分析
    - 时间趋势分析
    - 异常检测
    """

    def __init__(self):
        self._data: List[Dict[str, Any]] = []

    def load_data(self, data: List[Dict[str, Any]]) -> None:
        """
        加载数据

        Args:
            data: Ping 记录列表
        """
        self._data = data

    def clear(self) -> None:
        """清空数据"""
        self._data = []

    # ===== 基本统计分析 =====

    def calculate_rtt_statistics(
        self,
        percentiles: Optional[List[float]] = None
    ) -> Dict[str, float]:
        """
        计算 RTT 统计指标

        Args:
            percentiles: 要计算的百分位

        Returns:
            统计指标字典
        """
        rtt_values = [
            record.get('rtt_ms', 0)
            for record in self._data
            if record.get('rtt_ms') is not None
        ]

        if not rtt_values:
            return {'count': 0}

        return calculate_statistics(rtt_values, percentiles or [50, 90, 95, 99])

    def calculate_rtt_distribution(
        self,
        bucket_size: float = 10,
        max_value: float = 500
    ) -> Dict[str, int]:
        """
        计算 RTT 分布

        Args:
            bucket_size: 桶大小 (ms)
            max_value: 最大值 (ms)

        Returns:
            分布字典
        """
        distribution = defaultdict(int)

        for record in self._data:
            rtt = record.get('rtt_ms', 0)
            if rtt is None:
                continue

            if rtt > max_value:
                bucket = f">{int(max_value)}"
            else:
                bucket_start = int(rtt // bucket_size) * bucket_size
                bucket = f"{int(bucket_start)}-{int(bucket_start + bucket_size)}"

            distribution[bucket] += 1

        # 排序
        return dict(sorted(distribution.items(), key=lambda x: float(x[0].split('-')[0].replace('>', ''))))

    # ===== 分组分析 =====

    def analyze_by_asn(
        self,
        top_n: int = 20,
        min_samples: int = 10
    ) -> List[Dict[str, Any]]:
        """
        按 AS 分析

        Args:
            top_n: 返回前 N 个 AS
            min_samples: 最小样本数

        Returns:
            AS 统计列表
        """
        asn_data = defaultdict(list)

        for record in self._data:
            asn = record.get('ip_asn')
            rtt = record.get('rtt_ms')
            if asn is not None and rtt is not None:
                asn_data[asn].append(rtt)

        results = []
        for asn, rtts in asn_data.items():
            if len(rtts) < min_samples:
                continue

            stats = calculate_statistics(rtts, [50, 90, 95, 99])

            # 获取 AS 名称
            as_name = None
            for record in self._data:
                if record.get('ip_asn') == asn:
                    as_name = record.get('ip_as_name')
                    break

            results.append({
                'asn': asn,
                'as_name': as_name,
                'sample_count': len(rtts),
                **stats,
            })

        # 按样本数排序
        results.sort(key=lambda x: x['sample_count'], reverse=True)
        return results[:top_n]

    def analyze_by_asgeo(
        self,
        top_n: int = 20,
        min_samples: int = 10
    ) -> List[Dict[str, Any]]:
        """
        按 AS+Geo 分析

        Returns:
            AS+Geo 统计列表
        """
        asgeo_data = defaultdict(list)

        for record in self._data:
            asn = record.get('ip_asn')
            geo_country = record.get('ip_geo_country', '')
            geo_region = record.get('ip_geo_region', '')
            rtt = record.get('rtt_ms')

            if asn is not None and rtt is not None:
                key = f"AS{asn}-{geo_country}-{geo_region}"
                asgeo_data[key].append({
                    'rtt': rtt,
                    'asn': asn,
                    'country': geo_country,
                    'region': geo_region,
                })

        results = []
        for key, items in asgeo_data.items():
            if len(items) < min_samples:
                continue

            rtts = [item['rtt'] for item in items]
            stats = calculate_statistics(rtts, [50, 90, 95])

            results.append({
                'asgeo': key,
                'asn': items[0]['asn'],
                'country': items[0]['country'],
                'region': items[0]['region'],
                'sample_count': len(rtts),
                **stats,
            })

        results.sort(key=lambda x: x['sample_count'], reverse=True)
        return results[:top_n]

    def analyze_by_prefix24(
        self,
        top_n: int = 50,
        min_samples: int = 5
    ) -> List[Dict[str, Any]]:
        """
        按 /24 前缀分析

        Returns:
            前缀统计列表
        """
        prefix_data = defaultdict(list)

        for record in self._data:
            prefix = record.get('prefix24')
            rtt = record.get('rtt_ms')

            if prefix and rtt is not None:
                prefix_data[prefix].append(rtt)

        results = []
        for prefix, rtts in prefix_data.items():
            if len(rtts) < min_samples:
                continue

            stats = calculate_statistics(rtts, [50, 90, 95])

            # 获取该前缀的 ASN 信息
            asn = None
            for record in self._data:
                if record.get('prefix24') == prefix:
                    asn = record.get('ip_asn')
                    break

            results.append({
                'prefix24': prefix,
                'asn': asn,
                'sample_count': len(rtts),
                **stats,
            })

        results.sort(key=lambda x: x['sample_count'], reverse=True)
        return results[:top_n]

    def analyze_by_country(
        self,
        top_n: int = 20,
        min_samples: int = 10
    ) -> List[Dict[str, Any]]:
        """
        按国家分析

        Returns:
            国家统计列表
        """
        country_data = defaultdict(list)

        for record in self._data:
            country = record.get('ip_geo_country', 'Unknown')
            rtt = record.get('rtt_ms')

            if rtt is not None:
                country_data[country].append(rtt)

        results = []
        for country, rtts in country_data.items():
            if len(rtts) < min_samples:
                continue

            stats = calculate_statistics(rtts, [50, 90, 95])

            results.append({
                'country': country,
                'sample_count': len(rtts),
                **stats,
            })

        results.sort(key=lambda x: x['sample_count'], reverse=True)
        return results[:top_n]

    # ===== 时间分析 =====

    def analyze_by_time(
        self,
        interval: str = 'hour'
    ) -> List[Dict[str, Any]]:
        """
        按时间分析趋势

        Args:
            interval: 时间间隔 (minute, hour, day)

        Returns:
            时间序列数据
        """
        time_data = defaultdict(list)

        for record in self._data:
            measure_time = record.get('measure_time')
            rtt = record.get('rtt_ms')

            if measure_time and rtt is not None:
                # 根据间隔确定时间键
                if isinstance(measure_time, str):
                    measure_time = datetime.fromisoformat(measure_time.replace('Z', '+00:00'))

                if interval == 'minute':
                    time_key = measure_time.replace(second=0, microsecond=0)
                elif interval == 'hour':
                    time_key = measure_time.replace(minute=0, second=0, microsecond=0)
                else:  # day
                    time_key = measure_time.replace(hour=0, minute=0, second=0, microsecond=0)

                time_data[time_key].append(rtt)

        results = []
        for time_key in sorted(time_data.keys()):
            rtts = time_data[time_key]
            stats = calculate_statistics(rtts, [50, 90, 95])

            results.append({
                'time': time_key.isoformat() if hasattr(time_key, 'isoformat') else str(time_key),
                'sample_count': len(rtts),
                **stats,
            })

        return results

    # ===== 异常检测 =====

    def detect_rtt_anomalies(
        self,
        threshold: float = 2.0
    ) -> Dict[str, Any]:
        """
        检测 RTT 异常

        Args:
            threshold: Z-score 阈值

        Returns:
            异常检测结果
        """
        rtt_values = [
            record.get('rtt_ms', 0)
            for record in self._data
            if record.get('rtt_ms') is not None
        ]

        anomalies = detect_anomalies(rtt_values, threshold)

        # 关联原始记录
        anomaly_records = []
        for anomaly in anomalies:
            idx = anomaly['index']
            if idx < len(self._data):
                record = self._data[idx].copy()
                record['anomaly_score'] = anomaly['z_score']
                record['anomaly_type'] = anomaly['type']
                anomaly_records.append(record)

        return {
            'total_samples': len(rtt_values),
            'anomaly_count': len(anomalies),
            'anomaly_rate': len(anomalies) / len(rtt_values) if rtt_values else 0,
            'anomalies': anomaly_records[:100],  # 限制返回数量
        }

    # ===== 数据中心分析 =====

    def analyze_by_datacenter(
        self
    ) -> List[Dict[str, Any]]:
        """
        按数据中心分析

        Returns:
            数据中心统计列表
        """
        dc_data = defaultdict(list)

        for record in self._data:
            dc = record.get('data_center', 'Unknown')
            rtt = record.get('rtt_ms')

            if rtt is not None:
                dc_data[dc].append(rtt)

        results = []
        for dc, rtts in dc_data.items():
            stats = calculate_statistics(rtts, [50, 90, 95])

            results.append({
                'data_center': dc,
                'sample_count': len(rtts),
                **stats,
            })

        results.sort(key=lambda x: x['sample_count'], reverse=True)
        return results

    # ===== 综合报告 =====

    def generate_report(
        self
    ) -> Dict[str, Any]:
        """
        生成综合分析报告

        Returns:
            完整分析报告
        """
        return {
            'overall_stats': self.calculate_rtt_statistics(),
            'rtt_distribution': self.calculate_rtt_distribution(),
            'top_asns': self.analyze_by_asn(top_n=10),
            'top_asgeos': self.analyze_by_asgeo(top_n=10),
            'top_prefixes': self.analyze_by_prefix24(top_n=10),
            'top_countries': self.analyze_by_country(top_n=10),
            'anomalies': self.detect_rtt_anomalies(),
            'datacenter_stats': self.analyze_by_datacenter(),
        }
