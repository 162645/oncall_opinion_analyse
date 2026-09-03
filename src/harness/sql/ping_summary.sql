-- query_id: ping.summary
-- table is resolved from the validated region identifier by ClickHouseClient.
SELECT count() AS total_samples,
       countIf(rtt_ms > 0) AS valid_samples,
       avgIf(rtt_ms, rtt_ms > 0) AS mean_rtt,
       quantileIf(0.50)(rtt_ms, rtt_ms > 0) AS median_rtt,
       quantileIf(0.95)(rtt_ms, rtt_ms > 0) AS p95_rtt,
       quantileIf(0.99)(rtt_ms, rtt_ms > 0) AS p99_rtt
FROM {region}__ping
WHERE measure_time >= %(start_time)s
  AND measure_time < %(end_time)s
