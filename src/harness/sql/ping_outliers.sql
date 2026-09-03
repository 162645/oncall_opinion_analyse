-- query_id: ping.outliers
SELECT measure_time, rtt_ms, ip_asn, prefix24
FROM {region}__ping
WHERE measure_time >= %(start_time)s
  AND measure_time < %(end_time)s
  AND rtt_ms > (SELECT quantile(0.95)(rtt_ms)
                FROM {region}__ping
                WHERE measure_time >= %(start_time)s
                  AND measure_time < %(end_time)s
                  AND rtt_ms > 0)
ORDER BY rtt_ms DESC
LIMIT %(limit)s
