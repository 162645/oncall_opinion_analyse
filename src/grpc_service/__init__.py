"""
gRPC 服务模块
提供 Go <-> Python 之间的高性能通信
"""

from src.grpc_service.server import serve_grpc, serve_dual
from src.grpc_service.servicer import AgentServicer

__all__ = [
    "serve_grpc",
    "serve_dual",
    "AgentServicer",
]
