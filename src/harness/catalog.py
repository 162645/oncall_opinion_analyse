"""Reviewable query catalog used by the Planner and exposed to the UI."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Dict, Tuple, Type

from typing_extensions import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class QueryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query_type: str
    region: str
    start_time: str
    end_time: str
    limit: int = Field(default=100, ge=1, le=1000)

    @field_validator("region")
    @classmethod
    def validate_region(cls, value: str) -> str:
        value = value.upper()
        if not _REGION.fullmatch(value):
            raise ValueError("region must be an uppercase ClickHouse table identifier")
        return value


class PingSummaryInput(QueryInput):
    query_type: Literal["ping_stats"] = "ping_stats"


class PingTrendInput(QueryInput):
    query_type: Literal["ping_trend"] = "ping_trend"
    interval: Literal["hour"] = "hour"


class PingByASNInput(QueryInput):
    query_type: Literal["ping_stats"] = "ping_stats"
    group_by: Tuple[Literal["ip_asn"], ...] = ("ip_asn",)


class PingByPrefixInput(QueryInput):
    query_type: Literal["ping_stats"] = "ping_stats"


class PingOutliersInput(QueryInput):
    query_type: Literal["ping_outliers"] = "ping_outliers"


class TracePathsInput(QueryInput):
    query_type: Literal["trace_stats"] = "trace_stats"


class TracePathChangeInput(QueryInput):
    query_type: Literal["trace_path_change"] = "trace_path_change"


class SummaryRow(BaseModel):
    total_samples: int
    valid_samples: int
    mean_rtt: float | None = None
    median_rtt: float | None = None
    p95_rtt: float | None = None
    p99_rtt: float | None = None


class TrendRow(BaseModel):
    time_bucket: Any
    sample_count: int
    valid_samples: int
    mean_rtt: float | None = None
    median_rtt: float | None = None
    p95_rtt: float | None = None


class ASNRow(BaseModel):
    ip_asn: int
    total_samples: int
    valid_samples: int
    mean_rtt: float | None = None
    p95_rtt: float | None = None


class PrefixRow(BaseModel):
    prefix24: str
    total_samples: int
    valid_samples: int
    mean_rtt: float | None = None
    p95_rtt: float | None = None


class OutlierRow(BaseModel):
    measure_time: Any
    rtt_ms: float
    ip_asn: int
    prefix24: str


class TracePathRow(BaseModel):
    ip_path_hash: int
    occurrence_count: int
    avg_hop_count: float
    reached_count: int


class PathChangeRow(BaseModel):
    time_bucket: Any
    path_count: int
    sample_count: int


@dataclass(frozen=True)
class QuerySpec:
    query_id: str
    description: str
    sql_file: str
    tool_query_type: str
    result_key: str
    columns: Tuple[str, ...]
    input_model: Type[QueryInput]
    output_model: Type[BaseModel]


CATALOG: Dict[str, QuerySpec] = {
    "ping.summary": QuerySpec("ping.summary", "整体 RTT 与 P95/P99", "ping_summary.sql", "ping_stats", "statistics", ("total_samples", "valid_samples", "mean_rtt", "median_rtt", "p95_rtt", "p99_rtt"), PingSummaryInput, SummaryRow),
    "ping.trend": QuerySpec("ping.trend", "按小时的 RTT 趋势", "ping_trend.sql", "ping_trend", "trend_data", ("time_bucket", "sample_count", "valid_samples", "mean_rtt", "median_rtt", "p95_rtt"), PingTrendInput, TrendRow),
    "ping.by_asn": QuerySpec("ping.by_asn", "按 AS 的 RTT 对比", "ping_by_asn.sql", "ping_stats", "statistics", ("ip_asn", "total_samples", "valid_samples", "mean_rtt", "p95_rtt"), PingByASNInput, ASNRow),
    "ping.by_prefix24": QuerySpec("ping.by_prefix24", "按 /24 前缀的 RTT 对比", "ping_by_prefix24.sql", "ping_stats", "statistics", ("prefix24", "total_samples", "valid_samples", "mean_rtt", "p95_rtt"), PingByPrefixInput, PrefixRow),
    "ping.outliers": QuerySpec("ping.outliers", "异常 RTT 样本", "ping_outliers.sql", "ping_outliers", "outliers", ("measure_time", "rtt_ms", "ip_asn", "prefix24"), PingOutliersInput, OutlierRow),
    "trace.paths": QuerySpec("trace.paths", "Traceroute 路径稳定性", "trace_paths.sql", "trace_stats", "paths", ("ip_path_hash", "occurrence_count", "avg_hop_count", "reached_count"), TracePathsInput, TracePathRow),
    "trace.path_change": QuerySpec("trace.path_change", "按小时的路径变化", "trace_path_change.sql", "trace_path_change", "path_changes", ("time_bucket", "path_count", "sample_count"), TracePathChangeInput, PathChangeRow),
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
    validated = spec.input_model.model_validate(params)
    normalized = validated.model_dump(mode="python")
    region = normalized["region"]
    sql = read_sql(query_id).replace("{region}", region)
    if "{" in sql or "}" in sql:
        raise ValueError(f"unresolved template placeholder in {query_id}")
    values = {"start_time": normalized["start_time"], "end_time": normalized["end_time"], "limit": normalized["limit"]}
    return sql, values
