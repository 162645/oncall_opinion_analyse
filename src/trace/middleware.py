"""
追踪中间件
为 FastAPI 应用添加追踪能力
"""

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

from .tracer import get_tracer

logger = logging.getLogger(__name__)


class TracingMiddleware(BaseHTTPMiddleware):
    """
    追踪中间件

    为每个 HTTP 请求创建追踪跨度
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 获取追踪器
        tracer = get_tracer()

        # 创建跨度
        span = tracer.start_span(
            name=f"{request.method} {request.url.path}",
            attributes={
                "http.method": request.method,
                "http.url": str(request.url),
                "http.path": request.url.path,
                "http.query": str(request.query_params),
            },
        )

        start_time = time.time()

        try:
            # 执行请求
            response = await call_next(request)

            # 记录响应信息
            tracer.set_attribute("http.status_code", response.status_code)

            # 结束跨度
            tracer.end_span(span, "OK" if response.status_code < 400 else "ERROR")

            return response

        except Exception as e:
            tracer.record_exception(e)
            tracer.end_span(span, "ERROR")
            raise


def setup_tracing(app):
    """
    设置追踪

    Args:
        app: FastAPI 应用实例
    """
    # 添加中间件
    app.add_middleware(TracingMiddleware)

    logger.info("Tracing middleware enabled")
