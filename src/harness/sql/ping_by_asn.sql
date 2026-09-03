-- query_id: ping.by_asn
SELECT ip_asn,
       count() AS total_samples,
       countIf(rtt_ms > 0) AS valid_samples,
       avgIf(rtt_ms, rtt_ms > 0) AS mean_rtt,
       quantileIf(0.95)(rtt_ms, rtt_ms > 0) AS p95_rtt
FROM {region}__ping
WHERE measure_time >= %(start_time)s
  AND measure_time < %(end_time)s
GROUP BY ip_asn
ORDER BY p95_rtt DESC, valid_samples DESC
LIMIT %(limit)s
