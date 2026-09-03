"""Reviewable query catalog used by the Planner and exposed to the UI."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class QuerySpec:
    query_id: str
    description: str
    sql_file: str
    tool_query_type: str
    result_key: str
    columns: Tuple[str, ...]


CATALOG: Dict[str, QuerySpec] = {
    "ping.summary": QuerySpec("ping.summary", "整体 RTT 与 P95/P99", "ping_summary.sql", "ping_stats", "statistics", ("total_samples", "valid_samples", "mean_rtt", "median_rtt", "p95_rtt", "p99_rtt")),
    "ping.trend": QuerySpec("ping.trend", "按小时的 RTT 趋势", "ping_trend.sql", "ping_trend", "trend_data", ("time_bucket", "sample_count", "valid_samples", "mean_rtt", "median_rtt", "p95_rtt")),
    "ping.by_asn": QuerySpec("ping.by_asn", "按 AS 的 RTT 对比", "ping_by_asn.sql", "ping_stats", "statistics", ("ip_asn", "total_samples", "valid_samples", "mean_rtt", "p95_rtt")),
    "trace.paths": QuerySpec("trace.paths", "Traceroute 路径稳定性", "trace_paths.sql", "trace_stats", "paths", ("ip_path_hash", "occurrence_count", "avg_hop_count", "reached_count")),
}

_REGION = re.compile(r"^[A-Z][A-Z0-9_]{1,31}$")


def get_query_spec(query_id: str) -> QuerySpec:
    if query_id not in CATALOG:
        raise KeyError(f"Unsupported query_id: {query_id}")
    return CATALOG[query_id]


def catalog_description() -> Tuple[dict, ...]:
    return tuple({"query_id": item.query_id, "description": item.description, "tool_query_type": item.tool_query_type}
                 for item in CATALOG.values())


def read_sql(query_id: str) -> str:
    spec = get_query_spec(query_id)
    return (Path(__file__).with_name("sql") / spec.sql_file).read_text(encoding="utf-8")


def compile_sql(query_id: str, params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Compile a catalog query with identifiers and values separated safely."""
    spec = get_query_spec(query_id)
    region = str(params.get("region", "")).upper()
    if not _REGION.fullmatch(region):
        raise ValueError("region must be an uppercase ClickHouse table identifier")
    limit = int(params.get("limit", 100))
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    sql = read_sql(query_id).replace("{region}", region)
    if "{" in sql or "}" in sql:
        raise ValueError(f"unresolved template placeholder in {query_id}")
    values = {"start_time": params["start_time"], "end_time": params["end_time"], "limit": limit}
    return sql, values
