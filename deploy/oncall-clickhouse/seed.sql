-- Deterministic, distribution-shaped Ukraine telemetry. 732 two-hour cycles
-- (2024-06-01 00:00 through 2024-07-31 22:00), 10,000 destinations/cycle.
WITH
    ['AWS_frankfurt','GCP_warsaw','Azure_west_europe','AWS_stockholm','Vultr_warsaw','Hetzner_nuremberg','OVH_paris','AWS_london','GCP_prague','DigitalOcean_amsterdam'] AS dcs,
    [25299,31133,9009,3326,1299,16509,3356,6939] AS asns,
    [47.10,50.45,52.37,59.33,52.23,49.45,48.86,51.51,50.08,52.37] AS lats,
    [37.54,30.52,4.90,18.07,21.01,11.08,2.35,-0.13,14.44,4.90] AS lons,
    ['Донецька область','Київська область','Львівська область','Одеська область','Харківська область','Дніпропетровська область'] AS regions,
    ['Маріуполь','Київ','Львів','Одеса','Харків','Дніпро'] AS cities,
    ['my-trinity.ru','datagroup.ua','ukrtelecom.ua','lifecell.ua','kyivstar.ua'] AS isps
INSERT INTO net_measure.UKRAINE__ping
SELECT
    toUInt64(formatDateTime(t, '%Y%m%d%H%i')) AS cycle_id,
    t + toIntervalMicrosecond(toUInt64(modulo(cityHash64(toString(e), toString(c)), 900000))) AS measure_time,
    dcs[1 + modulo(e, length(dcs))] AS data_center,
    concat('217.', toString(199 + modulo(e, 4)), '.', toString(modulo(e, 240)), '.0') AS prefix24,
    toIPv4(concat('217.', toString(199 + modulo(e, 4)), '.', toString(modulo(e, 240)), '.', toString(2 + modulo(e * 17 + c, 250)))) AS dst_ip,
    toUInt32(3657430000 + e) AS dst_ip_num,
    toUInt8(48 + modulo(e, 5)) AS ttl,
    toFloat32(18 + modulo(cityHash64(toString(e), toString(c), 'rtt'), 185) / 3.0) AS rtt_ms,
    toUInt64(toUnixTimestamp64Micro(t)) AS probe_ts_us,
    concat('217.', toString(199 + modulo(e, 4)), '.', toString(modulo(e, 240)), '.', toString(2 + modulo(e * 17 + c, 250)), ':', toString(48 + modulo(e, 5)), ':', toString(round(18 + modulo(cityHash64(toString(e), toString(c), 'raw'), 185) / 3.0, 3)), ':', toString(toUnixTimestamp64Micro(t))) AS raw_ping,
    asns[1 + modulo(e, length(asns))] AS ip_asn,
    concat('AS', toString(asns[1 + modulo(e, length(asns))])) AS ip_as_name,
    toFloat32(lats[1 + modulo(e, length(lats))] + modulo(e, 17) / 100.0),
    toFloat32(lons[1 + modulo(e, length(lons))] + modulo(e, 13) / 100.0),
    regions[1 + modulo(e, length(regions))] AS ip_geo_region,
    '乌克兰' AS ip_geo_country,
    cities[1 + modulo(e, length(cities))] AS ip_geo_city,
    isps[1 + modulo(e, length(isps))] AS ip_isp_domain
FROM
(
    SELECT toDateTime64('2024-06-01 00:00:00', 6) + toIntervalHour(cycles.number * 2) AS t, endpoints.number AS e, cycles.number AS c
    FROM numbers(732) AS cycles CROSS JOIN numbers(10000) AS endpoints
)
SETTINGS max_insert_threads = 4;

WITH
    ['AWS_frankfurt','GCP_warsaw','Azure_west_europe','AWS_stockholm','Vultr_warsaw','Hetzner_nuremberg','OVH_paris','AWS_london','GCP_prague','DigitalOcean_amsterdam'] AS dcs,
    [25299,31133,9009,3326,1299,16509,3356,6939] AS asns
INSERT INTO net_measure.UKRAINE__quarter_traceroute
SELECT
    toUInt64(formatDateTime(t, '%Y%m%d%H%i')) AS cycle_id,
    t + toIntervalMicrosecond(toUInt64(modulo(cityHash64(toString(e), toString(c)), 900000))) AS measure_time,
    dcs[1 + modulo(e, length(dcs))] AS data_center,
    concat('217.', toString(199 + modulo(e, 4)), '.', toString(modulo(e, 240)), '.0') AS prefix24,
    toIPv4(concat('217.', toString(199 + modulo(e, 4)), '.', toString(modulo(e, 240)), '.', toString(2 + modulo(e * 17 + c, 250)))) AS dst_ip,
    toUInt8(9 + modulo(e, 8)) AS hop_count,
    toUInt8(7 + modulo(e, 5)) AS responded_hop_count,
    toUInt8(modulo(e, 3)) AS star_hop_count,
    toUInt8(modulo(e, 10) > 1) AS reached_target,
    concat('99.150.19.83>240.0.88.12>242.1.85.161>240.0.96.34>217.199.225.91') AS hop_path,
    concat('99.150.19.83-24.09-255|240.0.88.12-18.61-254|242.1.85.161-18.59-250|217.199.225.91-62.00-238') AS hop_info_path,
    '99.150.19.83>240.0.88.12>242.1.85.161>240.0.96.34>217.199.225.91' AS ip_path_text,
    cityHash64(toString(e), toString(c), 'ip') AS ip_path_hash,
    concat('AS16509->AS0->AS31133->AS', toString(asns[1 + modulo(e, length(asns))])) AS as_path_text,
    cityHash64(toString(e), toString(c), 'as') AS as_path_hash,
    '{"AS16509":["99.150.19.83"],"AS0":["240.0.88.12","242.1.85.161"],"AS31133":["240.0.96.34"]}' AS as_mid_nodes,
    concat('AS', toString(asns[1 + modulo(e, length(asns))])) AS as_term,
    'AS16509-未知->AS0-未知->AS31133-乌克兰' AS asgeo_path_text,
    cityHash64(toString(e), toString(c), 'geo') AS asgeo_path_hash,
    '{"AS16509-未知":["99.150.19.83"],"AS31133-乌克兰":["240.0.96.34"]}' AS asgeo_mid_nodes,
    '乌克兰' AS asgeo_term,
    concat('{"hops":', toString(9 + modulo(e, 8)), ',"target":"', toString(dst_ip), '","reached":', toString(modulo(e, 10) > 1), '}') AS raw_trace,
    toUInt64(toUnixTimestamp64Micro(t)) AS probe_ts_us
FROM
(
    SELECT toDateTime64('2024-06-01 00:00:00', 6) + toIntervalHour(cycles.number * 2) AS t, endpoints.number AS e, cycles.number AS c
    FROM numbers(732) AS cycles CROSS JOIN numbers(2500) AS endpoints
)
SETTINGS max_insert_threads = 4;

INSERT INTO net_measure.import_files
SELECT 'ukraine-synthetic-202406-202407', '/var/lib/clickhouse/user_files/ukraine-synthetic', 'ukraine-synthetic-202406-202407', 'ping+quarter_traceroute', 'UKRAINE', 'Europe', 'multi-region', 'synthetic-shaped-from-sample', 'generated', 'public-probes', '202406010000-202407312200', '2024-06-01 00:00:00..2024-07-31 22:00:00', 1, 1, 'completed', (SELECT count() FROM net_measure.UKRAINE__ping), (SELECT count() FROM net_measure.UKRAINE__quarter_traceroute), '', now(), now();
