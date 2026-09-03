"""
健康检查路由
"""

from datetime import datetime
import socket
from urllib.parse import urlparse

from fastapi import APIRouter

from src.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "oncall-opinion-analyse",
        "version": "4.0.0",
    }


@router.get("/ready")
async def readiness_check():
    """依赖就绪检查。

    This endpoint intentionally reports degraded dependencies instead of
    returning a hard-coded success response.  It does not expose credentials
    and uses short TCP probes so it remains safe to call from a load balancer.
    """
    checks = {
        "database": _tcp_check(settings.CLICKHOUSE_HOST, settings.CLICKHOUSE_PORT),
        "vector_store": _url_check(settings.QDRANT_URL, 6333),
        "session_store": _url_check(settings.REDIS_URL, 6379),
        "knowledge_graph": _url_check(settings.NEO4J_URI, 7687),
    }
    # Neo4j enriches explanations but is optional for the core Ping/Traceroute
    # flow. Keep the demo ready when core stores work, while exposing a clear
    # degraded status instead of hiding the graph outage.
    core_dependencies = ("database", "vector_store", "session_store")
    ready = all(checks[name] == "ok" for name in core_dependencies)
    degraded = any(value != "ok" for value in checks.values())
    return {
        "ready": ready,
        "status": "degraded" if degraded else "ready",
        "checks": checks,
        "timestamp": datetime.now().isoformat(),
    }


def _tcp_check(host: str, port: int) -> str:
    """Return a stable public status without leaking connection details."""
    try:
        with socket.create_connection((host, int(port)), timeout=1.0):
            return "ok"
    except (OSError, TypeError, ValueError):
        return "unreachable"


def _url_check(url: str, default_port: int) -> str:
    parsed = urlparse(url)
    return _tcp_check(parsed.hostname or "localhost", parsed.port or default_port)
