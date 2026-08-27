#!/usr/bin/env python3
"""
导入 Excel 数据到 SQLite
"""

import os
import sys
import pandas as pd
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.clickhouse.sqlite_client import get_sqlite_client


def import_excel_data(excel_path: str):
    """导入 Excel 数据到 SQLite"""
    print(f"导入 Excel 数据: {excel_path}")

    client = get_sqlite_client()
    conn = client._get_connection()
    cursor = conn.cursor()

    xlsx = pd.ExcelFile(excel_path)

    # 1. 导入 import_files
    if '样例_import_files' in xlsx.sheet_names:
        df = pd.read_excel(xlsx, sheet_name='样例_import_files')
        print(f"\n导入 import_files: {len(df)} 条记录")

        for _, row in df.iterrows():
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO import_files (
                        file_id, file_path, file_name, data_kind, target_region,
                        region_group, data_center, measurement_source, source_type,
                        provider, probe_site, cycle_id, measure_time, has_ping,
                        has_trace, import_status, ping_rows, trace_rows,
                        error_message, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(row.get('file_id', '')),
                    str(row.get('file_path', '')),
                    str(row.get('file_name', '')),
                    str(row.get('data_kind', '')),
                    str(row.get('target_region', '')),
                    str(row.get('region_group', '')),
                    str(row.get('data_center', '')),
                    str(row.get('measurement_source', '')),
                    str(row.get('source_type', '')),
                    str(row.get('provider', '')),
                    str(row.get('probe_site', '')),
                    str(row.get('cycle_id', '')),
                    str(row.get('measure_time', '')),
                    int(row.get('has_ping', 0)) if pd.notna(row.get('has_ping')) else 0,
                    int(row.get('has_trace', 0)) if pd.notna(row.get('has_trace')) else 0,
                    str(row.get('import_status', 'pending')),
                    int(row.get('ping_rows', 0)) if pd.notna(row.get('ping_rows')) else 0,
                    int(row.get('trace_rows', 0)) if pd.notna(row.get('trace_rows')) else 0,
                    str(row.get('error_message', '')),
                    str(row.get('created_at', '')),
                    str(row.get('updated_at', '')),
                ))
            except Exception as e:
                print(f"  导入错误: {e}")

        conn.commit()
        print("  ✅ import_files 导入完成")

    # 2. 导入 ping 数据
    if '样例_ping' in xlsx.sheet_names:
        df = pd.read_excel(xlsx, sheet_name='样例_ping')
        print(f"\n导入 ping: {len(df)} 条记录")

        for _, row in df.iterrows():
            try:
                cursor.execute("""
                    INSERT INTO UKRAINE__ping (
                        cycle_id, measure_time, data_center, prefix24, dst_ip,
                        dst_ip_num, ttl, rtt_ms, probe_ts_us, raw_ping,
                        ip_asn, ip_as_name, ip_geo_latitude, ip_geo_longitude,
                        ip_geo_region, ip_geo_country, ip_geo_city, ip_isp_domain
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(row.get('cycle_id', '')),
                    str(row.get('measure_time', '')),
                    str(row.get('data_center', '')),
                    str(row.get('prefix24', '')),
                    str(row.get('dst_ip', '')),
                    int(row.get('dst_ip_num', 0)) if pd.notna(row.get('dst_ip_num')) else None,
                    int(row.get('ttl', 0)) if pd.notna(row.get('ttl')) else None,
                    float(row.get('rtt_ms', 0)) if pd.notna(row.get('rtt_ms')) else None,
                    int(row.get('probe_ts_us', 0)) if pd.notna(row.get('probe_ts_us')) else None,
                    str(row.get('raw_ping', '')),
                    int(row.get('ip_asn', 0)) if pd.notna(row.get('ip_asn')) else None,
                    str(row.get('ip_as_name', '')) if pd.notna(row.get('ip_as_name')) else None,
                    float(row.get('ip_geo_latitude', 0)) if pd.notna(row.get('ip_geo_latitude')) else None,
                    float(row.get('ip_geo_longitude', 0)) if pd.notna(row.get('ip_geo_longitude')) else None,
                    str(row.get('ip_geo_region', '')) if pd.notna(row.get('ip_geo_region')) else None,
                    str(row.get('ip_geo_country', '')) if pd.notna(row.get('ip_geo_country')) else None,
                    str(row.get('ip_geo_city', '')) if pd.notna(row.get('ip_geo_city')) else None,
                    str(row.get('ip_isp_domain', '')) if pd.notna(row.get('ip_isp_domain')) else None,
                ))
            except Exception as e:
                print(f"  导入错误: {e}")

        conn.commit()
        print("  ✅ ping 导入完成")

    # 3. 导入 quarter_traceroute 数据
    if '样例_quarter_traceroute' in xlsx.sheet_names:
        df = pd.read_excel(xlsx, sheet_name='样例_quarter_traceroute')
        print(f"\n导入 quarter_traceroute: {len(df)} 条记录")

        for _, row in df.iterrows():
            try:
                cursor.execute("""
                    INSERT INTO UKRAINE__quarter_traceroute (
                        cycle_id, measure_time, data_center, prefix24, dst_ip,
                        hop_count, responded_hop_count, star_hop_count, reached_target,
                        hop_path, hop_info_path, ip_path_text, ip_path_hash,
                        as_path_text, as_path_hash, as_mid_nodes, as_term,
                        asgeo_path_text, asgeo_path_hash, asgeo_mid_nodes, asgeo_term,
                        raw_trace, probe_ts_us
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(row.get('cycle_id', '')),
                    str(row.get('measure_time', '')),
                    str(row.get('data_center', '')),
                    str(row.get('prefix24', '')),
                    str(row.get('dst_ip', '')),
                    int(row.get('hop_count', 0)) if pd.notna(row.get('hop_count')) else None,
                    int(row.get('responded_hop_count', 0)) if pd.notna(row.get('responded_hop_count')) else None,
                    int(row.get('star_hop_count', 0)) if pd.notna(row.get('star_hop_count')) else None,
                    int(row.get('reached_target', 0)) if pd.notna(row.get('reached_target')) else None,
                    str(row.get('hop_path', '')) if pd.notna(row.get('hop_path')) else None,
                    str(row.get('hop_info_path', '')) if pd.notna(row.get('hop_info_path')) else None,
                    str(row.get('ip_path_text', '')) if pd.notna(row.get('ip_path_text')) else None,
                    str(row.get('ip_path_hash', '')) if pd.notna(row.get('ip_path_hash')) else None,
                    str(row.get('as_path_text', '')) if pd.notna(row.get('as_path_text')) else None,
                    str(row.get('as_path_hash', '')) if pd.notna(row.get('as_path_hash')) else None,
                    str(row.get('as_mid_nodes', '')) if pd.notna(row.get('as_mid_nodes')) else None,
                    str(row.get('as_term', '')) if pd.notna(row.get('as_term')) else None,
                    str(row.get('asgeo_path_text', '')) if pd.notna(row.get('asgeo_path_text')) else None,
                    str(row.get('asgeo_path_hash', '')) if pd.notna(row.get('asgeo_path_hash')) else None,
                    str(row.get('asgeo_mid_nodes', '')) if pd.notna(row.get('asgeo_mid_nodes')) else None,
                    str(row.get('asgeo_term', '')) if pd.notna(row.get('asgeo_term')) else None,
                    str(row.get('raw_trace', '')) if pd.notna(row.get('raw_trace')) else None,
                    int(row.get('probe_ts_us', 0)) if pd.notna(row.get('probe_ts_us')) else None,
                ))
            except Exception as e:
                print(f"  导入错误: {e}")

        conn.commit()
        print("  ✅ quarter_traceroute 导入完成")

    # 4. 导入 ip_mapping_cache 数据
    if '样例_ip_mapping_cache' in xlsx.sheet_names:
        df = pd.read_excel(xlsx, sheet_name='样例_ip_mapping_cache')
        print(f"\n导入 ip_mapping_cache: {len(df)} 条记录")

        for _, row in df.iterrows():
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO ip_mapping_cache (
                        ip, ip_num, prefix24, asn, as_name,
                        geo_latitude, geo_longitude, geo_region, geo_country,
                        geo_city, isp_domain, asgeo, mapping_source, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(row.get('ip', '')),
                    int(row.get('ip_num', 0)) if pd.notna(row.get('ip_num')) else None,
                    str(row.get('prefix24', '')) if pd.notna(row.get('prefix24')) else None,
                    int(row.get('asn', 0)) if pd.notna(row.get('asn')) else None,
                    str(row.get('as_name', '')) if pd.notna(row.get('as_name')) else None,
                    float(row.get('geo_latitude', 0)) if pd.notna(row.get('geo_latitude')) else None,
                    float(row.get('geo_longitude', 0)) if pd.notna(row.get('geo_longitude')) else None,
                    str(row.get('geo_region', '')) if pd.notna(row.get('geo_region')) else None,
                    str(row.get('geo_country', '')) if pd.notna(row.get('geo_country')) else None,
                    str(row.get('geo_city', '')) if pd.notna(row.get('geo_city')) else None,
                    str(row.get('isp_domain', '')) if pd.notna(row.get('isp_domain')) else None,
                    str(row.get('asgeo', '')) if pd.notna(row.get('asgeo')) else None,
                    str(row.get('mapping_source', '')) if pd.notna(row.get('mapping_source')) else None,
                    str(row.get('updated_at', '')) if pd.notna(row.get('updated_at')) else None,
                ))
            except Exception as e:
                print(f"  导入错误: {e}")

        conn.commit()
        print("  ✅ ip_mapping_cache 导入完成")

    # 验证数据
    print("\n验证导入结果:")
    for table in ['import_files', 'UKRAINE__ping', 'UKRAINE__quarter_traceroute', 'ip_mapping_cache']:
        count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count} 条记录")

    conn.close()
    print("\n🎉 数据导入完成!")


if __name__ == "__main__":
    # Excel 文件路径
    excel_path = "APIandSympleData/net_measure_UKRAINE_完整样例100.xlsx"

    if not os.path.exists(excel_path):
        print(f"错误: 找不到 Excel 文件: {excel_path}")
        sys.exit(1)

    import_excel_data(excel_path)
