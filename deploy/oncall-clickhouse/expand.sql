-- Add five short re-measurement batches. Each batch has a small time/RTT
-- perturbation, preserving the sample's distribution without byte-for-byte duplicates.
INSERT INTO net_measure.UKRAINE__ping
SELECT cycle_id, measure_time + toIntervalSecond(retries.number * 17), data_center, prefix24, dst_ip,
       dst_ip_num, ttl, rtt_ms + toFloat32(retries.number) * 0.17, probe_ts_us + retries.number * 17000000,
       concat(raw_ping, ':retry', toString(retries.number)), ip_asn, ip_as_name,
       ip_geo_latitude, ip_geo_longitude, ip_geo_region, ip_geo_country,
       ip_geo_city, ip_isp_domain
FROM net_measure.UKRAINE__ping
CROSS JOIN numbers(5) AS retries(r)
SETTINGS max_insert_threads = 4;

INSERT INTO net_measure.UKRAINE__quarter_traceroute
SELECT cycle_id, measure_time + toIntervalSecond(retries.number * 17), data_center, prefix24, dst_ip,
       hop_count, responded_hop_count, star_hop_count, reached_target,
       concat(hop_path, '|retry', toString(retries.number)), hop_info_path, ip_path_text,
       cityHash64(toString(ip_path_hash), toString(retries.number)), as_path_text,
       cityHash64(toString(as_path_hash), toString(retries.number)), as_mid_nodes, as_term,
       asgeo_path_text, cityHash64(toString(asgeo_path_hash), toString(retries.number)),
       asgeo_mid_nodes, asgeo_term, concat(raw_trace, '|retry', toString(retries.number)),
       probe_ts_us + retries.number * 17000000
FROM net_measure.UKRAINE__quarter_traceroute
CROSS JOIN numbers(5) AS retries(r)
SETTINGS max_insert_threads = 4;
