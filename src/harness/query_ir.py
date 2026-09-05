"""Validated Query IR for catalog gaps; never accepts raw SQL from an LLM."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import QueryIR

ALLOWED_TABLES = {"ping_measurements"}
ALLOWED_DIMENSIONS = {"hour", "ip_asn", "prefix24"}
ALLOWED_METRICS = {"avg", "quantile", "count"}
ALLOWED_FIELDS = {"rtt_ms", "ip_asn", "prefix24", "measure_time"}


def validate_query_ir(ir: QueryIR, *, max_window_hours: int = 168) -> QueryIR:
    if ir.table not in ALLOWED_TABLES:
        raise ValueError("query IR table is not allowed")
    if any(item not in ALLOWED_DIMENSIONS for item in ir.dimensions + ir.group_by):
        raise ValueError("query IR contains an unsupported dimension")
    if any(item not in ALLOWED_FIELDS for metric in ir.metrics for item in [metric.get("field", "")]):
        raise ValueError("query IR contains an unsupported field")
    if any(metric.get("function") not in ALLOWED_METRICS for metric in ir.metrics):
        raise ValueError("query IR contains an unsupported metric")
    if not ir.time_range:
        raise ValueError("query IR requires an explicit time range")
    try:
        start = datetime.fromisoformat(ir.time_range.start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(ir.time_range.end_time.replace("Z", "+00:00"))
        hours = (end - start).total_seconds() / 3600
        if hours <= 0 or hours > max_window_hours:
            raise ValueError("query IR time window is outside the allowed range")
    except ValueError as exc:
        raise ValueError("query IR time range is invalid") from exc
    region = ir.filters.get("region")
    if not isinstance(region, str) or not region.isidentifier() or not region.isupper():
        raise ValueError("query IR requires an uppercase region identifier")
    return ir


def compile_query_ir(ir: QueryIR) -> tuple[str, dict[str, Any]]:
    """Compile only the small allow-listed IR subset into bound SQL."""
    validate_query_ir(ir)
    region = ir.filters["region"]
    select: list[str] = []
    if "hour" in ir.dimensions or "hour" in ir.group_by:
        select.append("toStartOfHour(measure_time) AS hour")
    if "ip_asn" in ir.dimensions or "ip_asn" in ir.group_by:
        select.append("ip_asn")
    if "prefix24" in ir.dimensions or "prefix24" in ir.group_by:
        select.append("prefix24")
    for index, metric in enumerate(ir.metrics):
        function, field = metric["function"], metric.get("field", "rtt_ms")
        if function == "count":
            select.append("count() AS metric_%d" % index)
        elif function == "avg":
            select.append("avg(%s) AS metric_%d" % (field, index))
        else:
            percentile = float(metric.get("percentile", 0.95))
            if not 0 < percentile < 1:
                raise ValueError("quantile percentile must be between 0 and 1")
            select.append("quantile(%(percentile)s)(%(field)s) AS metric_%(index)s" %
                          {"percentile": percentile, "field": field, "index": index})
    if not select:
        raise ValueError("query IR must request at least one dimension or metric")
    clauses = ["measure_time >= %(start_time)s", "measure_time < %(end_time)s"]
    sql = "SELECT %s FROM %s__ping WHERE %s" % (", ".join(select), region, " AND ".join(clauses))
    groups = [item for item in ("hour", "ip_asn", "prefix24") if item in ir.group_by or item in ir.dimensions]
    if groups:
        sql += " GROUP BY " + ", ".join(groups)
    sql += " LIMIT %(limit)s"
    return sql, {"start_time": ir.time_range.start_time,
                 "end_time": ir.time_range.end_time, "limit": ir.limit}
