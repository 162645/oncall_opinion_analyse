"""
gRPC 服务器

支持两种运行模式:
1. 独立 gRPC 服务
2. 同时运行 HTTP (FastAPI) 和 gRPC 服务

架构:
┌───────────────────────────────────────────────┐
│                   Python 服务                   │
│  ┌─────────────────┐  ┌──────────────────┐    │
│  │  HTTP Server    │  │  gRPC Server     │    │
│  │  (FastAPI)      │  │  (asyncio)       │    │
│  │  Port: 8000     │  │  Port: 50051     │    │
│  └────────┬────────┘  └────────┬─────────┘    │
│           │                    │               │
│           └──────────┬─────────┘               │
│                      │                         │
│           ┌──────────▼──────────┐             │
│           │   AgentService      │             │
│           │   (共享业务逻辑)     │             │
│           └─────────────────────┘             │
└───────────────────────────────────────────────┘
"""

import asyncio
import logging
import os
import sys
from concurrent import futures

# 添加 proto_gen 到路径
_proto_gen_path = os.path.join(os.path.dirname(__file__), '..', '..', 'proto_gen', 'python')
if _proto_gen_path not in sys.path:
    sys.path.insert(0, os.path.abspath(_proto_gen_path))

logger = logging.getLogger(__name__)


async def serve_grpc(port: int = 50051, max_workers: int = 10):
    """
    启动 gRPC 服务器

    Args:
        port: gRPC 服务端口
        max_workers: 最大工作线程数

    Returns:
        gRPC 服务器实例
    """
    try:
        from grpc import aio
        from opentelemetry.instrumentation.grpc import GrpcAioInstrumentorServer
        import agent_pb2_grpc
        from src.grpc_service.servicer import AgentServicer
    except ImportError as e:
        logger.error(f"Failed to import gRPC modules: {e}")
        logger.error("Please generate proto files first:")
        logger.error("  python -m grpc_tools.protoc -I./proto --python_out=./proto_gen/python --grpc_python_out=./proto_gen/python proto/agent.proto")
        raise

    GrpcAioInstrumentorServer().instrument()

    # 创建异步 gRPC 服务器
    server = aio.server(
        futures.ThreadPoolExecutor(max_workers=max_workers),
        options=[
            # 消息大小限制
            ('grpc.max_receive_message_length', 50 * 1024 * 1024),  # 50MB
            ('grpc.max_send_message_length', 50 * 1024 * 1024),
            # keepalive 设置
            ('grpc.keepalive_time_ms', 30000),
            ('grpc.keepalive_timeout_ms', 10000),
            ('grpc.keepalive_permit_without_calls', True),
        ]
    )

    # 注册服务
    agent_pb2_grpc.add_AgentServiceServicer_to_server(
        AgentServicer(),
        server
    )

    # 绑定端口
    server.add_insecure_port(f'[::]:{port}')

    # 启动服务
    await server.start()
    logger.info(f"✅ gRPC server started on port {port}")

    return server


async def serve_http(http_port: int = 8000):
    """
    启动 HTTP 服务器 (FastAPI)

    Args:
        http_port: HTTP 服务端口
    """
    import uvicorn
    from src.api.main import app

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=http_port,
        log_level="info",
    )
    server = uvicorn.Server(config)

    logger.info(f"✅ HTTP server starting on port {http_port}")
    await server.serve()


async def serve_dual(http_port: int = 8000, grpc_port: int = 50051):
    """
    同时启动 HTTP 和 gRPC 服务

    这是推荐的运行模式，支持两种协议:
    - HTTP: 兼容现有前端、调试方便
    - gRPC: 高性能、Go 服务调用

    Args:
        http_port: HTTP 端口
        grpc_port: gRPC 端口
    """
    import uvicorn
    from src.api.main import app

    logger.info("=" * 60)
    logger.info("Starting dual-mode server (HTTP + gRPC)")
    logger.info(f"  HTTP:  http://0.0.0.0:{http_port}")
    logger.info(f"  gRPC:  localhost:{grpc_port}")
    logger.info("=" * 60)

    # 启动 gRPC 服务 (后台运行)
    grpc_server = await serve_grpc(grpc_port)

    # 启动 HTTP 服务 (主线程)
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=http_port,
        log_level="info",
    )
    http_server = uvicorn.Server(config)

    try:
        await http_server.serve()
    finally:
        # 确保 gRPC 服务正确关闭
        logger.info("Shutting down gRPC server...")
        await grpc_server.stop(0)
        logger.info("Server stopped")


def create_standalone_grpc_app():
    """
    创建独立的 gRPC 应用 (不启动 HTTP)

    用于只需要 gRPC 的场景
    """
    async def run():
        server = await serve_grpc()
        try:
            await server.wait_for_termination()
        except KeyboardInterrupt:
            await server.stop(0)

    return run


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Agent Server")
    parser.add_argument("--mode", choices=["dual", "http", "grpc"], default="dual",
                       help="Server mode: dual (HTTP+gRPC), http only, grpc only")
    parser.add_argument("--http-port", type=int, default=8000, help="HTTP port")
    parser.add_argument("--grpc-port", type=int, default=50051, help="gRPC port")

    args = parser.parse_args()

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    if args.mode == "dual":
        asyncio.run(serve_dual(args.http_port, args.grpc_port))
    elif args.mode == "http":
        asyncio.run(serve_http(args.http_port))
    else:
        run_grpc = create_standalone_grpc_app()
        asyncio.run(run_grpc())
