"""
SQLite 数据存储
提供本地数据存储功能，模拟 ClickHouse 接口

基于 Excel 示例数据结构构建:
- import_files: 导入文件元数据
- {region}__ping: Ping 测量数据
- {region}__quarter_traceroute: Traceroute 数据 (1/4抽样)
- ip_mapping_cache: IP 映射缓存
"""

import os
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import threading
import logging

from .models import (
    PingRecord,
    TraceRecord,
    IPMappingRecord,
    ImportFileRecord,
    RegionInfo,
    QueryFilters,
)

logger = logging.getLogger(__name__)


@dataclass
class SQLiteConfig:
    """SQLite 配置"""
    db_path: str = "data/net_measure.db"

    @classmethod
    def from_env(cls) -> 'SQLiteConfig':
        return cls(
            db_path=os.getenv("SQLITE_DB_PATH", "data/net_measure.db"),
        )


class SQLiteClient:
    """
    SQLite 客户端
    模拟 ClickHouse 接口，提供本地数据存储
    """

    def __init__(self, config: Optional[SQLiteConfig] = None):
        self.config = config or SQLiteConfig.from_env()
        self._local = threading.local()
        self._ensure_db()

    def _get_connection(self) -> sqlite3.Connection:
        """获取线程本地连接"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            os.makedirs(os.path.dirname(self.config.db_path) if os.path.dirname(self.config.db_path) else '.', exist_ok=True)
            self._local.conn = sqlite3.connect(self.config.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _ensure_db(self):
        """确保数据库和表存在 - 基于 Excel 结构定义"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # import_files 表 (对应 结构_import_files)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS import_files (
            file_id TEXT PRIMARY KEY,
            file_path TEXT,
            file_name TEXT,
            data_kind TEXT,
            target_region TEXT,
            region_group TEXT,
            data_center TEXT,
            measurement_source TEXT,
            source_type TEXT,
            provider TEXT,
            probe_site TEXT,
            cycle_id INTEGER,
            measure_time TEXT,
            has_ping INTEGER DEFAULT 0,
            has_trace INTEGER DEFAULT 0,
            import_status TEXT DEFAULT 'pending',
            ping_rows INTEGER DEFAULT 0,
            trace_rows INTEGER DEFAULT 0,
            error_message TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """)

        # UKRAINE__ping 表 (对应 结构_ping)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS UKRAINE__ping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id INTEGER,
            measure_time TEXT,
            data_center TEXT,
            prefix24 TEXT,
            dst_ip TEXT,
            dst_ip_num INTEGER,
            ttl INTEGER,
            rtt_ms REAL,
            probe_ts_us INTEGER,
            raw_ping TEXT,
            ip_asn INTEGER,
            ip_as_name TEXT,
            ip_geo_latitude REAL,
            ip_geo_longitude REAL,
            ip_geo_region TEXT,
            ip_geo_country TEXT,
            ip_geo_city TEXT,
            ip_isp_domain TEXT
        )
        """)

        # UKRAINE__quarter_traceroute 表 (对应 结构_quarter_traceroute)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS UKRAINE__quarter_traceroute (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id INTEGER,
            measure_time TEXT,
            data_center TEXT,
            prefix24 TEXT,
            dst_ip TEXT,
            hop_count INTEGER,
            responded_hop_count INTEGER,
            star_hop_count INTEGER,
            reached_target INTEGER,
            hop_path TEXT,
            hop_info_path TEXT,
            ip_path_text TEXT,
            ip_path_hash TEXT,
            as_path_text TEXT,
            as_path_hash TEXT,
            as_mid_nodes TEXT,
            as_term TEXT,
            asgeo_path_text TEXT,
            asgeo_path_hash TEXT,
            asgeo_mid_nodes TEXT,
            asgeo_term TEXT,
            raw_trace TEXT,
            probe_ts_us INTEGER
        )
        """)

        # ip_mapping_cache 表 (对应 结构_ip_mapping_cache)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ip_mapping_cache (
            ip TEXT PRIMARY KEY,
            ip_num INTEGER,
            prefix24 TEXT,
            asn INTEGER,
            as_name TEXT,
            geo_latitude REAL,
            geo_longitude REAL,
            geo_region TEXT,
            geo_country TEXT,
            geo_city TEXT,
            isp_domain TEXT,
            asgeo TEXT,
            mapping_source TEXT,
            updated_at TEXT
        )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ping_measure_time ON UKRAINE__ping(measure_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ping_prefix24 ON UKRAINE__ping(prefix24)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ping_asn ON UKRAINE__ping(ip_asn)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ping_country ON UKRAINE__ping(ip_geo_country)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ping_rtt ON UKRAINE__ping(rtt_ms)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trace_measure_time ON UKRAINE__quarter_traceroute(measure_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trace_prefix24 ON UKRAINE__quarter_traceroute(prefix24)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_import_region ON import_files(target_region)")

        conn.commit()
        logger.info("SQLite 数据库初始化完成")

    # ===== 提供与 ClickHouse 兼容的 client 属性 =====
    @property
    def client(self):
        """返回 self，用于与 ClickHouse 客户端接口兼容"""
        return self

    def execute(
        self,
        query: str,
        params: Optional[Dict] = None,
        with_column_types: bool = False
    ) -> Any:
        """执行查询"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                if with_column_types:
                    columns = [desc[0] for desc in cursor.description]
                    return [list(row) for row in results], columns
                return [list(row) for row in results]
            else:
                conn.commit()
                return []
        except Exception as e:
            logger.error(f"Query error: {e}\nQuery: {query}")
            raise

    # ===== 地区和表管理 =====

    def get_regions(self) -> List[str]:
        """获取所有地区列表"""
        query = """
        SELECT DISTINCT target_region
        FROM import_files
        WHERE target_region IS NOT NULL AND target_region != ''
        ORDER BY target_region
        """
        result = self.execute(query)
        regions = [row[0] for row in result if row[0]]

        # 如果没有数据，返回默认的 UKRAINE
        if not regions:
            # 检查 UKRAINE__ping 表是否有数据
            count = self.execute("SELECT COUNT(*) FROM UKRAINE__ping")
            if count and count[0][0] > 0:
                return ['UKRAINE']

        return regions

    def get_region_info(self, region: str) -> Optional[RegionInfo]:
        """获取地区详细信息"""
        ping_table = f"{region}__ping"
        trace_table = f"{region}__trace"
        quarter_trace_table = f"{region}__quarter_traceroute"

        info = RegionInfo(
            name=region,
            ping_table=ping_table,
            trace_table=trace_table,
            quarter_trace_table=quarter_trace_table,
        )

        try:
            # 检查表是否存在
            table_check = self.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{ping_table}'")
            if not table_check:
                return info

            # 获取 ping 表统计
            ping_stats = self.execute(f"""
                SELECT
                    COUNT(*) as total_rows,
                    MIN(measure_time) as min_time,
                    MAX(measure_time) as max_time
                FROM {ping_table}
            """)
            if ping_stats and ping_stats[0]:
                info.total_ping_rows = ping_stats[0][0] or 0
                info.min_time = ping_stats[0][1]
                info.max_time = ping_stats[0][2]

            # 获取数据中心列表
            dcs = self.execute(f"""
                SELECT DISTINCT data_center
                FROM {ping_table}
                WHERE data_center IS NOT NULL AND data_center != ''
                ORDER BY data_center
            """)
            info.data_centers = [row[0] for row in dcs if row[0]]
        except Exception as e:
            logger.warning(f"获取地区信息失败: {e}")

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

        where_clause, params = self._build_where_clause(filters)

        query = f"""
        SELECT {', '.join(columns)}
        FROM {table_name}
        WHERE {where_clause}
        ORDER BY measure_time
        LIMIT :limit
        OFFSET :offset
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
        """查询 Ping 统计数据"""
        table_name = f"{filters.region}__ping"
        where_clause, params = self._build_where_clause(filters)

        if group_by:
            group_cols = ', '.join(group_by)
            query = f"""
            SELECT
                {group_cols},
                COUNT(*) as sample_count,
                AVG(rtt_ms) as mean_rtt,
                MIN(rtt_ms) as min_rtt,
                MAX(rtt_ms) as max_rtt
            FROM {table_name}
            WHERE {where_clause}
            GROUP BY {group_cols}
            ORDER BY sample_count DESC
            LIMIT :limit
            """
        else:
            query = f"""
            SELECT
                COUNT(*) as sample_count,
                AVG(rtt_ms) as mean_rtt,
                MIN(rtt_ms) as min_rtt,
                MAX(rtt_ms) as max_rtt
            FROM {table_name}
            WHERE {where_clause}
            """

        params['limit'] = filters.limit

        result = self.execute(query, params)

        if group_by:
            return [
                dict(zip(group_by + ['sample_count', 'mean_rtt', 'min_rtt', 'max_rtt'], row))
                for row in result
            ]
        else:
            return [dict(zip(['sample_count', 'mean_rtt', 'min_rtt', 'max_rtt'], result[0]))] if result else []

    def query_ping_trend(
        self,
        filters: QueryFilters,
        interval: str = 'hour'
    ) -> List[Dict[str, Any]]:
        """查询 Ping 时间趋势"""
        table_name = f"{filters.region}__ping"
        where_clause, params = self._build_where_clause(filters)

        interval_format = {
            'minute': '%Y-%m-%d %H:%M:00',
            'hour': '%Y-%m-%d %H:00:00',
            'day': '%Y-%m-%d 00:00:00',
        }.get(interval, '%Y-%m-%d %H:00:00')

        query = f"""
        SELECT
            strftime('{interval_format}', measure_time) as time_bucket,
            COUNT(*) as sample_count,
            AVG(rtt_ms) as mean_rtt
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

        where_clause, params = self._build_where_clause(filters)

        query = f"""
        SELECT {', '.join(columns)}
        FROM {table_name}
        WHERE {where_clause}
        ORDER BY measure_time
        LIMIT :limit
        OFFSET :offset
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
        where_clause, params = self._build_where_clause(filters)

        if group_by_path:
            query = f"""
            SELECT
                ip_path_text,
                as_path_text,
                asgeo_path_text,
                ip_path_hash,
                COUNT(*) as occurrence_count,
                AVG(hop_count) as avg_hop_count,
                SUM(CASE WHEN reached_target = 1 THEN 1 ELSE 0 END) as reached_count
            FROM {table_name}
            WHERE {where_clause}
            GROUP BY ip_path_text, as_path_text, asgeo_path_text, ip_path_hash
            ORDER BY occurrence_count DESC
            LIMIT :limit
            """
        else:
            query = f"""
            SELECT
                COUNT(*) as total_traces,
                AVG(hop_count) as avg_hop_count,
                SUM(CASE WHEN reached_target = 1 THEN 1 ELSE 0 END) as reached_count,
                COUNT(DISTINCT ip_path_hash) as unique_paths
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

    # ===== IP 映射查询 =====

    def query_ip_mapping(self, ip: str) -> Optional[IPMappingRecord]:
        """查询单个 IP 的映射信息"""
        query = """
        SELECT *
        FROM ip_mapping_cache
        WHERE ip = ?
        LIMIT 1
        """
        result = self.execute(query, (ip,))
        if result:
            columns = ['ip', 'ip_num', 'prefix24', 'asn', 'as_name',
                       'geo_latitude', 'geo_longitude', 'geo_region',
                       'geo_country', 'geo_city', 'isp_domain', 'asgeo',
                       'mapping_source', 'updated_at']
            return IPMappingRecord.from_row(result[0], columns)
        return None

    def query_ips_by_asn(self, asn: int, limit: int = 1000) -> List[IPMappingRecord]:
        """查询属于特定 AS 的所有 IP"""
        query = """
        SELECT *
        FROM ip_mapping_cache
        WHERE asn = ?
        LIMIT ?
        """
        result = self.execute(query, (asn, limit))
        columns = ['ip', 'ip_num', 'prefix24', 'asn', 'as_name',
                   'geo_latitude', 'geo_longitude', 'geo_region',
                   'geo_country', 'geo_city', 'isp_domain', 'asgeo',
                   'mapping_source', 'updated_at']
        return [IPMappingRecord.from_row(row, columns) for row in result]

    # ===== 辅助方法 =====

    def _build_where_clause(self, filters: QueryFilters) -> Tuple[str, Dict]:
        """构建 WHERE 子句"""
        conditions = ["1=1"]
        params = {}

        if filters.start_time:
            conditions.append("measure_time >= :start_time")
            params['start_time'] = str(filters.start_time)

        if filters.end_time:
            conditions.append("measure_time <= :end_time")
            params['end_time'] = str(filters.end_time)

        if filters.data_center:
            conditions.append("data_center = :data_center")
            params['data_center'] = filters.data_center

        if filters.prefix24:
            conditions.append("prefix24 = :prefix24")
            params['prefix24'] = filters.prefix24

        if filters.asn:
            conditions.append("ip_asn = :asn")
            params['asn'] = filters.asn

        if filters.country:
            conditions.append("ip_geo_country = :country")
            params['country'] = filters.country

        return " AND ".join(conditions), params

    # ===== 元数据查询 =====

    def get_available_asns(self, region: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取地区中出现的 AS 列表"""
        table_name = f"{region}__ping"

        query = f"""
        SELECT
            ip_asn,
            ip_as_name,
            COUNT(*) as sample_count
        FROM {table_name}
        WHERE ip_asn IS NOT NULL AND ip_asn > 0
        GROUP BY ip_asn, ip_as_name
        ORDER BY sample_count DESC
        LIMIT ?
        """

        result = self.execute(query, (limit,))
        return [
            {
                'asn': row[0],
                'as_name': row[1],
                'sample_count': row[2],
            }
            for row in result
        ]

    def get_available_countries(self, region: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取地区中出现的国家列表"""
        table_name = f"{region}__ping"

        query = f"""
        SELECT
            ip_geo_country,
            COUNT(*) as sample_count
        FROM {table_name}
        WHERE ip_geo_country IS NOT NULL AND ip_geo_country != ''
        GROUP BY ip_geo_country
        ORDER BY sample_count DESC
        LIMIT ?
        """

        result = self.execute(query, (limit,))
        return [
            {
                'country': row[0],
                'sample_count': row[1],
            }
            for row in result
        ]

    def get_time_range(self, region: str) -> Tuple[Optional[str], Optional[str]]:
        """获取地区数据的时间范围"""
        table_name = f"{region}__ping"

        query = f"""
        SELECT MIN(measure_time), MAX(measure_time)
        FROM {table_name}
        """

        result = self.execute(query)
        if result and result[0]:
            return result[0][0], result[0][1]
        return None, None


# 全局客户端实例
_sqlite_client: Optional[SQLiteClient] = None


def get_sqlite_client() -> SQLiteClient:
    """获取 SQLite 客户端实例"""
    global _sqlite_client
    if _sqlite_client is None:
        _sqlite_client = SQLiteClient()
    return _sqlite_client
