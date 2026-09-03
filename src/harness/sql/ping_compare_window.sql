-- query_id: ping.compare_window
WITH current_window AS (
    SELECT quantileIf(0.50)(rtt_ms, rtt_ms > 0) AS current_p50,
           quantileIf(0.95)(rtt_ms, rtt_ms > 0) AS current_p95,
           quantileIf(0.99)(rtt_ms, rtt_ms > 0) AS current_p99
    FROM {region}__ping
    WHERE measure_time >= %(start_time)s AND measure_time < %(end_time)s
), baseline_window AS (
    SELECT quantileIf(0.50)(rtt_ms, rtt_ms > 0) AS baseline_p50,
           quantileIf(0.95)(rtt_ms, rtt_ms > 0) AS baseline_p95,
           quantileIf(0.99)(rtt_ms, rtt_ms > 0) AS baseline_p99
    FROM {region}__ping
    WHERE measure_time >= %(baseline_start)s AND measure_time < %(baseline_end)s
)
SELECT current_p50, current_p95, current_p99,
       baseline_p50, baseline_p95, baseline_p99,
       current_p95 - baseline_p95 AS p95_delta,
       if(baseline_p95 = 0, NULL, (current_p95 - baseline_p95) / baseline_p95) AS p95_relative_delta
FROM current_window CROSS JOIN baseline_window
