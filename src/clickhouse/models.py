"""
ClickHouse 数据模型
定义网络测量数据的结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class PingRecord:
    """Ping 测量记录"""
    cycle_id: int
    measure_time: datetime
    data_center: str
    prefix24: str
    dst_ip: str
    dst_ip_num: Optional[int] = None
    ttl: Optional[int] = None
    rtt_ms: Optional[float] = None
    probe_ts_us: Optional[int] = None
    raw_ping: Optional[str] = None
    ip_asn: Optional[int] = None
    ip_as_name: Optional[str] = None
    ip_geo_latitude: Optional[float] = None
    ip_geo_longitude: Optional[float] = None
    ip_geo_region: Optional[str] = None
    ip_geo_country: Optional[str] = None
    ip_geo_city: Optional[str] = None
    ip_isp_domain: Optional[str] = None

    @classmethod
    def from_row(cls, row: tuple, columns: List[str]) -> 'PingRecord':
        """从数据库行创建记录"""
        data = dict(zip(columns, row))
        return cls(
            cycle_id=data.get('cycle_id', 0),
            measure_time=data.get('measure_time'),
            data_center=data.get('data_center', ''),
            prefix24=data.get('prefix24', ''),
            dst_ip=data.get('dst_ip', ''),
            dst_ip_num=data.get('dst_ip_num'),
            ttl=data.get('ttl'),
            rtt_ms=data.get('rtt_ms'),
            probe_ts_us=data.get('probe_ts_us'),
            raw_ping=data.get('raw_ping'),
            ip_asn=data.get('ip_asn'),
            ip_as_name=data.get('ip_as_name'),
            ip_geo_latitude=data.get('ip_geo_latitude'),
            ip_geo_longitude=data.get('ip_geo_longitude'),
            ip_geo_region=data.get('ip_geo_region'),
            ip_geo_country=data.get('ip_geo_country'),
            ip_geo_city=data.get('ip_geo_city'),
            ip_isp_domain=data.get('ip_isp_domain'),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'cycle_id': self.cycle_id,
            'measure_time': self.measure_time.isoformat() if self.measure_time else None,
            'data_center': self.data_center,
            'prefix24': self.prefix24,
            'dst_ip': self.dst_ip,
            'rtt_ms': self.rtt_ms,
            'ip_asn': self.ip_asn,
            'ip_as_name': self.ip_as_name,
            'ip_geo_region': self.ip_geo_region,
            'ip_geo_country': self.ip_geo_country,
            'ip_geo_city': self.ip_geo_city,
        }


@dataclass
class TraceRecord:
    """Traceroute 记录"""
    cycle_id: int
    measure_time: datetime
    data_center: str
    prefix24: str
    dst_ip: str
    hop_count: int
    responded_hop_count: int
    star_hop_count: int
    reached_target: bool
    hop_path: Optional[str] = None
    hop_info_path: Optional[str] = None
    ip_path_text: Optional[str] = None
    ip_path_hash: Optional[int] = None
    as_path_text: Optional[str] = None
    as_path_hash: Optional[int] = None
    as_mid_nodes: Optional[str] = None
    as_term: Optional[str] = None
    asgeo_path_text: Optional[str] = None
    asgeo_path_hash: Optional[int] = None
    asgeo_mid_nodes: Optional[str] = None
    asgeo_term: Optional[str] = None
    raw_trace: Optional[str] = None
    probe_ts_us: Optional[int] = None

    @classmethod
    def from_row(cls, row: tuple, columns: List[str]) -> 'TraceRecord':
        """从数据库行创建记录"""
        data = dict(zip(columns, row))
        return cls(
            cycle_id=data.get('cycle_id', 0),
            measure_time=data.get('measure_time'),
            data_center=data.get('data_center', ''),
            prefix24=data.get('prefix24', ''),
            dst_ip=data.get('dst_ip', ''),
            hop_count=data.get('hop_count', 0),
            responded_hop_count=data.get('responded_hop_count', 0),
            star_hop_count=data.get('star_hop_count', 0),
            reached_target=data.get('reached_target', False),
            hop_path=data.get('hop_path'),
            hop_info_path=data.get('hop_info_path'),
            ip_path_text=data.get('ip_path_text'),
            ip_path_hash=data.get('ip_path_hash'),
            as_path_text=data.get('as_path_text'),
            as_path_hash=data.get('as_path_hash'),
            as_mid_nodes=data.get('as_mid_nodes'),
            as_term=data.get('as_term'),
            asgeo_path_text=data.get('asgeo_path_text'),
            asgeo_path_hash=data.get('asgeo_path_hash'),
            asgeo_mid_nodes=data.get('asgeo_mid_nodes'),
            asgeo_term=data.get('asgeo_term'),
            raw_trace=data.get('raw_trace'),
            probe_ts_us=data.get('probe_ts_us'),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'cycle_id': self.cycle_id,
            'measure_time': self.measure_time.isoformat() if self.measure_time else None,
            'data_center': self.data_center,
            'prefix24': self.prefix24,
            'dst_ip': self.dst_ip,
            'hop_count': self.hop_count,
            'ip_path_text': self.ip_path_text,
            'as_path_text': self.as_path_text,
            'asgeo_path_text': self.asgeo_path_text,
            'reached_target': self.reached_target,
        }

    def parse_as_path(self) -> List[str]:
        """解析 AS 路径"""
        if not self.as_path_text:
            return []
        return [as_node for as_node in self.as_path_text.split('->') if as_node != '*']

    def parse_asgeo_path(self) -> List[str]:
        """解析 AS+Geo 路径"""
        if not self.asgeo_path_text:
            return []
        return [node for node in self.asgeo_path_text.split('->') if node != '*']


@dataclass
class IPMappingRecord:
    """IP 映射记录"""
    ip: str
    ip_num: Optional[int] = None
    prefix24: Optional[str] = None
    asn: Optional[int] = None
    as_name: Optional[str] = None
    geo_latitude: Optional[float] = None
    geo_longitude: Optional[float] = None
    geo_region: Optional[str] = None
    geo_country: Optional[str] = None
    geo_city: Optional[str] = None
    isp_domain: Optional[str] = None
    asgeo: Optional[str] = None
    mapping_source: Optional[str] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row: tuple, columns: List[str]) -> 'IPMappingRecord':
        """从数据库行创建记录"""
        data = dict(zip(columns, row))
        return cls(
            ip=data.get('ip', ''),
            ip_num=data.get('ip_num'),
            prefix24=data.get('prefix24'),
            asn=data.get('asn'),
            as_name=data.get('as_name'),
            geo_latitude=data.get('geo_latitude'),
            geo_longitude=data.get('geo_longitude'),
            geo_region=data.get('geo_region'),
            geo_country=data.get('geo_country'),
            geo_city=data.get('geo_city'),
            isp_domain=data.get('isp_domain'),
            asgeo=data.get('asgeo'),
            mapping_source=data.get('mapping_source'),
            updated_at=data.get('updated_at'),
        )


@dataclass
class ImportFileRecord:
    """导入文件记录"""
    file_id: int
    file_path: str
    file_name: str
    data_kind: str
    target_region: str
    region_group: str
    data_center: str
    measurement_source: str
    source_type: str
    provider: str
    probe_site: str
    cycle_id: int
    measure_time: datetime
    has_ping: bool
    has_trace: bool
    import_status: str
    ping_rows: int
    trace_rows: int
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row: tuple, columns: List[str]) -> 'ImportFileRecord':
        """从数据库行创建记录"""
        data = dict(zip(columns, row))
        return cls(
            file_id=data.get('file_id', 0),
            file_path=data.get('file_path', ''),
            file_name=data.get('file_name', ''),
            data_kind=data.get('data_kind', ''),
            target_region=data.get('target_region', ''),
            region_group=data.get('region_group', ''),
            data_center=data.get('data_center', ''),
            measurement_source=data.get('measurement_source', ''),
            source_type=data.get('source_type', ''),
            provider=data.get('provider', ''),
            probe_site=data.get('probe_site', ''),
            cycle_id=data.get('cycle_id', 0),
            measure_time=data.get('measure_time'),
            has_ping=data.get('has_ping', False),
            has_trace=data.get('has_trace', False),
            import_status=data.get('import_status', ''),
            ping_rows=data.get('ping_rows', 0),
            trace_rows=data.get('trace_rows', 0),
            error_message=data.get('error_message'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )


@dataclass
class RegionInfo:
    """地区信息"""
    name: str
    ping_table: str
    trace_table: str
    quarter_trace_table: str
    total_ping_rows: int = 0
    total_trace_rows: int = 0
    data_centers: List[str] = field(default_factory=list)
    min_time: Optional[datetime] = None
    max_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'ping_table': self.ping_table,
            'trace_table': self.trace_table,
            'quarter_trace_table': self.quarter_trace_table,
            'total_ping_rows': self.total_ping_rows,
            'total_trace_rows': self.total_trace_rows,
            'data_centers': self.data_centers,
            'min_time': self.min_time.isoformat() if self.min_time else None,
            'max_time': self.max_time.isoformat() if self.max_time else None,
        }


@dataclass
class QueryFilters:
    """查询过滤器"""
    region: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    asn: Optional[int] = None
    prefix24: Optional[str] = None
    data_center: Optional[str] = None
    ip_geo_country: Optional[str] = None
    ip_geo_region: Optional[str] = None
    isp_domain: Optional[str] = None  # 运营商筛选
    limit: int = 10000
    offset: int = 0

    def to_where_clause(self, table_alias: str = '') -> tuple:
        """生成 WHERE 子句"""
        conditions = []
        params = {}

        prefix = f"{table_alias}." if table_alias else ""

        if self.start_time:
            conditions.append(f"{prefix}measure_time >= %(start_time)s")
            params['start_time'] = self.start_time

        if self.end_time:
            conditions.append(f"{prefix}measure_time <= %(end_time)s")
            params['end_time'] = self.end_time

        if self.asn:
            conditions.append(f"{prefix}ip_asn = %(asn)s")
            params['asn'] = self.asn

        if self.prefix24:
            conditions.append(f"{prefix}prefix24 = %(prefix24)s")
            params['prefix24'] = self.prefix24

        if self.data_center:
            conditions.append(f"{prefix}data_center = %(data_center)s")
            params['data_center'] = self.data_center

        if self.ip_geo_country:
            conditions.append(f"{prefix}ip_geo_country = %(ip_geo_country)s")
            params['ip_geo_country'] = self.ip_geo_country

        if self.ip_geo_region:
            conditions.append(f"{prefix}ip_geo_region = %(ip_geo_region)s")
            params['ip_geo_region'] = self.ip_geo_region

        if self.isp_domain:
            conditions.append(f"{prefix}ip_isp_domain = %(isp_domain)s")
            params['isp_domain'] = self.isp_domain

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        return where_clause, params
