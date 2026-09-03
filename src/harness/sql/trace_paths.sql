-- query_id: trace.paths
SELECT ip_path_hash,
       count() AS occurrence_count,
       avg(hop_count) AS avg_hop_count,
       sum(if(reached_target, 1, 0)) AS reached_count
FROM {region}__quarter_traceroute
WHERE measure_time >= %(start_time)s
  AND measure_time < %(end_time)s
  AND (%(prefix24)s = '' OR prefix24 = %(prefix24)s)
GROUP BY ip_path_hash
ORDER BY occurrence_count DESC
LIMIT %(limit)s
