-- query_id: trace.path_change
SELECT toStartOfHour(measure_time) AS time_bucket,
       uniqExact(ip_path_hash) AS path_count,
       count() AS sample_count
FROM {region}__quarter_traceroute
WHERE measure_time >= %(start_time)s
  AND measure_time < %(end_time)s
GROUP BY time_bucket
ORDER BY time_bucket
