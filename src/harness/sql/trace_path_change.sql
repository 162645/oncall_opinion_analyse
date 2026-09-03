-- query_id: trace.path_change
WITH path_counts AS (
    SELECT toStartOfHour(measure_time) AS time_bucket,
           ip_path_hash,
           count() AS occurrences
    FROM {region}__quarter_traceroute
    WHERE measure_time >= %(start_time)s
      AND measure_time < %(end_time)s
      AND (%(prefix24)s = '' OR prefix24 = %(prefix24)s)
    GROUP BY time_bucket, ip_path_hash
)
SELECT time_bucket,
       uniqExact(ip_path_hash) AS path_count,
       sum(occurrences) AS sample_count,
       argMax(ip_path_hash, occurrences) AS dominant_path_hash
FROM path_counts
GROUP BY time_bucket
ORDER BY time_bucket
