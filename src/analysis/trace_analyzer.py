"""
Traceroute 数据分析器
提供路径分析功能
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass


@dataclass
class HopInfo:
    """跳信息"""
    ip: str
    rtt: float
    ttl: int


@dataclass
class PathNode:
    """路径节点"""
    ip: str
    asn: Optional[int] = None
    as_name: Optional[str] = None
    geo_country: Optional[str] = None
    geo_region: Optional[str] = None


class TraceAnalyzer:
    """
    Traceroute 分析器

    功能:
    - 路径统计分析
    - AS 路径分析
    - ASGeo 路径分析
    - 路径变化检测
    """

    def __init__(self):
        self._data: List[Dict[str, Any]] = []

    def load_data(self, data: List[Dict[str, Any]]) -> None:
        """
        加载数据

        Args:
            data: Traceroute 记录列表
        """
        self._data = data

    def clear(self) -> None:
        """清空数据"""
        self._data = []

    # ===== 路径统计 =====

    def analyze_path_statistics(
        self
    ) -> Dict[str, Any]:
        """
        分析路径基本统计

        Returns:
            路径统计信息
        """
        if not self._data:
            return {}

        hop_counts = []
        reached_count = 0
        path_hashes = set()

        for record in self._data:
            hop_counts.append(record.get('hop_count', 0))
            if record.get('reached_target'):
                reached_count += 1
            if record.get('ip_path_hash'):
                path_hashes.add(record.get('ip_path_hash'))

        avg_hops = sum(hop_counts) / len(hop_counts) if hop_counts else 0
        reach_rate = reached_count / len(self._data) if self._data else 0

        return {
            'total_traces': len(self._data),
            'reached_count': reached_count,
            'reach_rate': reach_rate,
            'unique_paths': len(path_hashes),
            'avg_hop_count': avg_hops,
            'min_hop_count': min(hop_counts) if hop_counts else 0,
            'max_hop_count': max(hop_counts) if hop_counts else 0,
        }

    def analyze_ip_paths(
        self,
        top_n: int = 20
    ) -> List[Dict[str, Any]]:
        """
        分析 IP 路径

        Returns:
            IP 路径统计列表
        """
        path_counter = Counter()

        for record in self._data:
            ip_path = record.get('ip_path_text')
            if ip_path:
                path_counter[ip_path] += 1

        results = []
        for path, count in path_counter.most_common(top_n):
            # 解析路径
            hops = [h for h in path.split('>') if h != '*']

            results.append({
                'ip_path': path,
                'occurrence_count': count,
                'hop_count': len(hops),
                'percentage': count / len(self._data) * 100 if self._data else 0,
            })

        return results

    def analyze_as_paths(
        self,
        top_n: int = 20
    ) -> List[Dict[str, Any]]:
        """
        分析 AS 路径

        Returns:
            AS 路径统计列表
        """
        path_counter = Counter()
        path_details = {}

        for record in self._data:
            as_path = record.get('as_path_text')
            if as_path:
                path_counter[as_path] += 1
                if as_path not in path_details:
                    path_details[as_path] = {
                        'ip_path_example': record.get('ip_path_text'),
                        'asgeo_path': record.get('asgeo_path_text'),
                    }

        results = []
        for path, count in path_counter.most_common(top_n):
            # 解析 AS 路径
            as_nodes = [as_node for as_node in path.split('->') if as_node != '*']
            unique_asns = set(as_nodes)

            detail = path_details.get(path, {})

            results.append({
                'as_path': path,
                'occurrence_count': count,
                'as_hop_count': len(as_nodes),
                'unique_as_count': len(unique_asns),
                'percentage': count / len(self._data) * 100 if self._data else 0,
                **detail,
            })

        return results

    def analyze_asgeo_paths(
        self,
        top_n: int = 20
    ) -> List[Dict[str, Any]]:
        """
        分析 AS+Geo 路径

        Returns:
            ASGeo 路径统计列表
        """
        path_counter = Counter()

        for record in self._data:
            asgeo_path = record.get('asgeo_path_text')
            if asgeo_path:
                path_counter[asgeo_path] += 1

        results = []
        for path, count in path_counter.most_common(top_n):
            # 解析 ASGeo 路径
            nodes = [n for n in path.split('->') if n != '*']

            # 提取地理信息
            geo_countries = set()
            for node in nodes:
                parts = node.split('-')
                if len(parts) >= 2:
                    geo_countries.add(parts[1] if len(parts) > 1 else 'Unknown')

            results.append({
                'asgeo_path': path,
                'occurrence_count': count,
                'hop_count': len(nodes),
                'unique_countries': len(geo_countries),
                'countries': list(geo_countries),
                'percentage': count / len(self._data) * 100 if self._data else 0,
            })

        return results

    # ===== AS 分析 =====

    def analyze_as_distribution(
        self
    ) -> Dict[str, Any]:
        """
        分析 AS 分布

        Returns:
            AS 分布信息
        """
        asn_counter = Counter()
        asn_names = {}

        for record in self._data:
            as_path = record.get('as_path_text', '')
            for as_node in as_path.split('->'):
                if as_node and as_node != '*':
                    asn_counter[as_node] += 1

        # 获取 AS 名称
        for record in self._data:
            as_path = record.get('as_path_text', '')
            as_mid_nodes = record.get('as_mid_nodes', '')
            # 解析 mid_nodes 获取 AS 名称
            if as_mid_nodes:
                try:
                    import json
                    nodes = json.loads(as_mid_nodes.replace("'", '"'))
                    for asn, info_list in nodes.items():
                        if asn not in asn_names:
                            # 从第一个 info 中提取名称
                            pass
                except:
                    pass

        top_asns = [
            {
                'asn': asn,
                'occurrence_count': count,
                'percentage': count / sum(asn_counter.values()) * 100 if asn_counter else 0,
            }
            for asn, count in asn_counter.most_common(20)
        ]

        return {
            'total_unique_asns': len(asn_counter),
            'top_asns': top_asns,
        }

    def analyze_as_connectivity(
        self
    ) -> List[Dict[str, Any]]:
        """
        分析 AS 连接关系

        Returns:
            AS 连接对统计
        """
        link_counter = Counter()

        for record in self._data:
            as_path = record.get('as_path_text', '')
            as_nodes = [n for n in as_path.split('->') if n and n != '*']

            for i in range(len(as_nodes) - 1):
                link = (as_nodes[i], as_nodes[i + 1])
                link_counter[link] += 1

        results = []
        for (src, dst), count in link_counter.most_common(50):
            results.append({
                'source_as': src,
                'destination_as': dst,
                'occurrence_count': count,
            })

        return results

    # ===== 路径变化分析 =====

    def analyze_path_variability(
        self,
        top_n: int = 20
    ) -> List[Dict[str, Any]]:
        """
        分析路径变化

        检测同一目标的不同路径

        Returns:
            目标路径变化统计
        """
        dst_paths = defaultdict(set)

        for record in self._data:
            dst_ip = record.get('dst_ip')
            ip_path_hash = record.get('ip_path_hash')
            if dst_ip and ip_path_hash:
                dst_paths[dst_ip].add(ip_path_hash)

        results = []
        for dst_ip, paths in dst_paths.items():
            if len(paths) > 1:
                results.append({
                    'dst_ip': dst_ip,
                    'path_count': len(paths),
                })

        results.sort(key=lambda x: x['path_count'], reverse=True)
        return results[:top_n]

    def detect_path_changes(
        self
    ) -> Dict[str, Any]:
        """
        检测路径变化事件

        Returns:
            变化检测结果
        """
        # 按时间排序
        sorted_data = sorted(
            self._data,
            key=lambda x: x.get('measure_time', '')
        )

        changes = []
        prev_path = None

        for record in sorted_data:
            curr_path = record.get('ip_path_hash')
            if prev_path is not None and curr_path != prev_path:
                changes.append({
                    'time': record.get('measure_time'),
                    'from_path': prev_path,
                    'to_path': curr_path,
                    'dst_ip': record.get('dst_ip'),
                })
            prev_path = curr_path

        return {
            'total_records': len(self._data),
            'change_count': len(changes),
            'change_rate': len(changes) / max(len(self._data) - 1, 1),
            'changes': changes[:50],
        }

    # ===== 特定目标分析 =====

    def find_paths_to_asn(
        self,
        target_asn: int
    ) -> List[Dict[str, Any]]:
        """
        查找到特定 AS 的路径

        Args:
            target_asn: 目标 AS 号

        Returns:
            到目标 AS 的路径列表
        """
        results = []

        for record in self._data:
            as_path = record.get('as_path_text', '')
            as_term = record.get('as_term', '')

            # 检查是否经过目标 AS
            target_str = f"AS{target_asn}"
            if target_str in as_path or target_str == as_term:
                results.append({
                    'dst_ip': record.get('dst_ip'),
                    'ip_path': record.get('ip_path_text'),
                    'as_path': as_path,
                    'asgeo_path': record.get('asgeo_path_text'),
                    'reached_target': record.get('reached_target'),
                    'hop_count': record.get('hop_count'),
                })

        return results

    def find_paths_by_prefix(
        self,
        prefix24: str
    ) -> List[Dict[str, Any]]:
        """
        查询特定前缀的路径

        Args:
            prefix24: /24 前缀

        Returns:
            该前缀的路径列表
        """
        results = []

        for record in self._data:
            if record.get('prefix24') == prefix24:
                results.append({
                    'dst_ip': record.get('dst_ip'),
                    'ip_path': record.get('ip_path_text'),
                    'as_path': record.get('as_path_text'),
                    'asgeo_path': record.get('asgeo_path_text'),
                    'hop_count': record.get('hop_count'),
                })

        return results

    # ===== 路径关联分析 =====

    def correlate_with_ping(
        self,
        ping_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        关联 Traceroute 和 Ping 数据

        通过 prefix24 关联

        Args:
            ping_data: Ping 数据列表

        Returns:
            关联后的数据
        """
        # 构建 ping 统计
        ping_by_prefix = defaultdict(list)
        for record in ping_data:
            prefix = record.get('prefix24')
            rtt = record.get('rtt_ms')
            if prefix and rtt is not None:
                ping_by_prefix[prefix].append(rtt)

        # 关联 trace 数据
        results = []
        for record in self._data:
            prefix = record.get('prefix24')
            if prefix in ping_by_prefix:
                rtts = ping_by_prefix[prefix]
                avg_rtt = sum(rtts) / len(rtts)

                results.append({
                    **record,
                    'ping_sample_count': len(rtts),
                    'ping_avg_rtt': avg_rtt,
                })

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
            'statistics': self.analyze_path_statistics(),
            'top_ip_paths': self.analyze_ip_paths(top_n=10),
            'top_as_paths': self.analyze_as_paths(top_n=10),
            'top_asgeo_paths': self.analyze_asgeo_paths(top_n=10),
            'as_distribution': self.analyze_as_distribution(),
            'as_connectivity': self.analyze_as_connectivity()[:20],
            'path_variability': self.analyze_path_variability(top_n=10),
        }
