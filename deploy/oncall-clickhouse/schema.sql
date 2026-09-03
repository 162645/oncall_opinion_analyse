CREATE DATABASE IF NOT EXISTS net_measure;

CREATE TABLE IF NOT EXISTS net_measure.UKRAINE__ping
(
    cycle_id UInt64,
    measure_time DateTime64(6),
    data_center LowCardinality(String),
    prefix24 String,
    dst_ip IPv4,
    dst_ip_num UInt32,
    ttl UInt8,
    rtt_ms Float32,
    probe_ts_us UInt64,
    raw_ping String,
    ip_asn UInt32,
    ip_as_name String,
    ip_geo_latitude Float32,
    ip_geo_longitude Float32,
    ip_geo_region LowCardinality(String),
    ip_geo_country LowCardinality(String),
    ip_geo_city LowCardinality(String),
    ip_isp_domain String
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(measure_time)
ORDER BY (measure_time, data_center, prefix24, dst_ip);

CREATE TABLE IF NOT EXISTS net_measure.UKRAINE__quarter_traceroute
(
    cycle_id UInt64,
    measure_time DateTime64(6),
    data_center LowCardinality(String),
    prefix24 String,
    dst_ip IPv4,
    hop_count UInt8,
    responded_hop_count UInt8,
    star_hop_count UInt8,
    reached_target UInt8,
    hop_path String,
    hop_info_path String,
    ip_path_text String,
    ip_path_hash UInt64,
    as_path_text String,
    as_path_hash UInt64,
    as_mid_nodes String,
    as_term String,
    asgeo_path_text String,
    asgeo_path_hash UInt64,
    asgeo_mid_nodes String,
    asgeo_term String,
    raw_trace String,
    probe_ts_us UInt64
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(measure_time)
ORDER BY (measure_time, data_center, prefix24, dst_ip);

CREATE TABLE IF NOT EXISTS net_measure.import_files
(
    file_id String,
    file_path String,
    file_name String,
    data_kind String,
    target_region String,
    region_group String,
    data_center String,
    measurement_source String,
    source_type String,
    provider String,
    probe_site String,
    cycle_id String,
    measure_time String,
    has_ping UInt8,
    has_trace UInt8,
    import_status String,
    ping_rows UInt64,
    trace_rows UInt64,
    error_message String,
    created_at DateTime,
    updated_at DateTime
)
ENGINE = MergeTree
ORDER BY (target_region, measure_time, file_id);
