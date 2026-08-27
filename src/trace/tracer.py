"""
OpenTelemetry 追踪器
提供分布式追踪能力
"""

from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from functools import wraps
import time
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class Span:
    """追踪跨度"""
    name: str
    start_time: float
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = None
    events: list = None
    status: str = "OK"

    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}
        if self.events is None:
            self.events = []

    @property
    def duration_ms(self) -> int:
        """持续时间（毫秒）"""
        if self.end_time:
            return int((self.end_time - self.start_time) * 1000)
        return 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": self.events,
            "status": self.status,
        }


class Tracer:
    """
    追踪器

    功能:
    1. 创建和管理追踪跨度
    2. 记录事件和属性
    3. 导出追踪数据
    4. 与 OpenTelemetry 集成（可选）
    """

    def __init__(self, service_name: str = "oncall-opinion-analyse"):
        self.service_name = service_name
        self._spans: list = []
        self._current_span: Optional[Span] = None
        self._otel_tracer = None
        self._otel_available = self._check_otel()

    def _check_otel(self) -> bool:
        """检查 OpenTelemetry 是否可用"""
        try:
            from opentelemetry import trace
            return True
        except ImportError:
            logger.debug("OpenTelemetry not installed, using simple tracing")
            return False

    def start_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """
        开始一个跨度

        Args:
            name: 跨度名称
            attributes: 属性字典

        Returns:
            Span
        """
        span = Span(
            name=name,
            start_time=time.time(),
            attributes=attributes or {},
        )

        self._spans.append(span)
        self._current_span = span

        return span

    def end_span(self, span: Span, status: str = "OK"):
        """
        结束跨度

        Args:
            span: 要结束的跨度
            status: 状态 (OK, ERROR)
        """
        span.end_time = time.time()
        span.status = status

        if self._current_span == span:
            self._current_span = None

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """
        添加事件到当前跨度

        Args:
            name: 事件名称
            attributes: 事件属性
        """
        if self._current_span:
            self._current_span.events.append({
                "name": name,
                "timestamp": time.time(),
                "attributes": attributes or {},
            })

    def set_attribute(self, key: str, value: Any):
        """
        设置当前跨度的属性

        Args:
            key: 属性名
            value: 属性值
        """
        if self._current_span:
            self._current_span.attributes[key] = value

    def record_exception(self, exception: Exception):
        """
        记录异常

        Args:
            exception: 异常对象
        """
        if self._current_span:
            self._current_span.status = "ERROR"
            self._current_span.events.append({
                "name": "exception",
                "timestamp": time.time(),
                "attributes": {
                    "type": type(exception).__name__,
                    "message": str(exception),
                },
            })

    def get_spans(self) -> list:
        """获取所有跨度"""
        return [s.to_dict() for s in self._spans]

    def clear(self):
        """清除所有跨度"""
        self._spans = []
        self._current_span = None

    def export_traces(self) -> Dict[str, Any]:
        """
        导出追踪数据

        Returns:
            追踪数据字典
        """
        return {
            "service_name": self.service_name,
            "spans": self.get_spans(),
            "total_spans": len(self._spans),
            "total_duration_ms": sum(s.duration_ms for s in self._spans),
        }


def trace_span(name: Optional[str] = None):
    """
    追踪装饰器

    用法:
        @trace_span("my_operation")
        async def my_function():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            span_name = name or func.__name__

            span = tracer.start_span(span_name, {
                "function": func.__name__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys()),
            })

            try:
                result = await func(*args, **kwargs)
                tracer.end_span(span, "OK")
                return result

            except Exception as e:
                tracer.record_exception(e)
                tracer.end_span(span, "ERROR")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()
            span_name = name or func.__name__

            span = tracer.start_span(span_name, {
                "function": func.__name__,
            })

            try:
                result = func(*args, **kwargs)
                tracer.end_span(span, "OK")
                return result

            except Exception as e:
                tracer.record_exception(e)
                tracer.end_span(span, "ERROR")
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# 全局追踪器实例
_tracer: Optional[Tracer] = None


def get_tracer() -> Tracer:
    """获取追踪器实例"""
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer
