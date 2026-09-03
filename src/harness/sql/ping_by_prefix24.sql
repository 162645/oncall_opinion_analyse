-- query_id: ping.by_prefix24
SELECT prefix24,
       count() AS total_samples,
       countIf(rtt_ms > 0) AS valid_samples,
       avgIf(rtt_ms, rtt_ms > 0) AS mean_rtt,
       quantileIf(0.95)(rtt_ms, rtt_ms > 0) AS p95_rtt
FROM {region}__ping
WHERE measure_time >= %(start_time)s
  AND measure_time < %(end_time)s
  AND (%(asn)s = 0 OR ip_asn = %(asn)s)
GROUP BY prefix24
ORDER BY p95_rtt DESC, valid_samples DESC
LIMIT %(limit)s
