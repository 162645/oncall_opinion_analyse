-- query_id: ping.trend
SELECT toStartOfHour(measure_time) AS time_bucket,
       count() AS sample_count,
       countIf(rtt_ms > 0) AS valid_samples,
       avgIf(rtt_ms, rtt_ms > 0) AS mean_rtt,
       quantileIf(0.50)(rtt_ms, rtt_ms > 0) AS median_rtt,
       quantileIf(0.95)(rtt_ms, rtt_ms > 0) AS p95_rtt
FROM {region}__ping
WHERE measure_time >= %(start_time)s
  AND measure_time < %(end_time)s
GROUP BY time_bucket
ORDER BY time_bucket
