"""Reproducible engineering metrics for the Agent Harness."""

from __future__ import annotations

import asyncio
import math
import statistics
import time
from dataclasses import asdict, dataclass
from typing import Any, Awaitable, Callable, Dict, Iterable, List


def percentile(values: Iterable[float], p: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    rank = (len(ordered) - 1) * p / 100.0
    lower, upper = math.floor(rank), math.ceil(rank)
    if lower == upper:
        return float(ordered[lower])
    return float(ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower))


@dataclass
class LatencyStats:
    count: int
    success_rate: float
    throughput_per_second: float
    mean_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float


async def benchmark_async(
    operation: Callable[[int], Awaitable[Any]],
    *,
    requests: int,
    concurrency: int,
) -> LatencyStats:
    semaphore = asyncio.Semaphore(concurrency)
    latencies: List[float] = []
    successes = 0

    async def run(index: int):
        nonlocal successes
        async with semaphore:
            started = time.perf_counter()
            try:
                result = await operation(index)
                if getattr(result, "success", bool(result)):
                    successes += 1
            finally:
                latencies.append((time.perf_counter() - started) * 1000)

    wall_started = time.perf_counter()
    await asyncio.gather(*(run(index) for index in range(requests)))
    wall_seconds = max(time.perf_counter() - wall_started, 1e-9)
    return LatencyStats(
        count=requests,
        success_rate=successes / requests if requests else 0.0,
        throughput_per_second=requests / wall_seconds,
        mean_ms=statistics.fmean(latencies) if latencies else 0.0,
        p50_ms=percentile(latencies, 50),
        p95_ms=percentile(latencies, 95),
        p99_ms=percentile(latencies, 99),
    )


def to_dict(stats: LatencyStats) -> Dict[str, Any]:
    return asdict(stats)
