INSERT INTO net_measure.import_files
(file_id,file_path,file_name,data_kind,target_region,region_group,data_center,measurement_source,source_type,provider,probe_site,cycle_id,measure_time,has_ping,has_trace,import_status,ping_rows,trace_rows,error_message,created_at,updated_at)
SELECT
 'ukraine-synthetic-202406-202407',
 '/var/lib/clickhouse/user_files/ukraine-synthetic',
 'ukraine-synthetic-202406-202407',
 'ping+quarter_traceroute', 'UKRAINE', 'Europe', 'multi-region',
 'synthetic-shaped-from-sample', 'generated', 'public-probes', 'public-probes',
 '202406010000-202407312200', '2024-06-01 00:00:00..2024-07-31 22:00:00',
 1, 1, 'completed',
 (SELECT count() FROM net_measure.UKRAINE__ping),
 (SELECT count() FROM net_measure.UKRAINE__quarter_traceroute),
 '', now(), now();
