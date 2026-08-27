"""
缓存服务
提供高级缓存功能
"""

import json
import hashlib
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar
from dataclasses import dataclass

from .client import RedisClient, get_redis_client

T = TypeVar('T')


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float
    ttl: Optional[int] = None
    hits: int = 0

    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return time.time() > self.created_at + self.ttl


class CacheService:
    """
    缓存服务

    提供高级缓存功能:
    - 智能缓存键生成
    - 缓存过期管理
    - 缓存装饰器
    - 批量操作
    """

    # 默认缓存键前缀
    DEFAULT_PREFIX = "oncall:cache:"

    def __init__(
        self,
        client: Optional[RedisClient] = None,
        prefix: str = DEFAULT_PREFIX,
        default_ttl: int = 3600,  # 1 小时
    ):
        """
        初始化缓存服务

        Args:
            client: Redis 客户端
            prefix: 缓存键前缀
            default_ttl: 默认过期时间 (秒)
        """
        self.client = client or get_redis_client()
        self.prefix = prefix
        self.default_ttl = default_ttl

    def _make_key(self, key: str) -> str:
        """生成完整缓存键"""
        return f"{self.prefix}{key}"

    def _hash_key(self, *args, **kwargs) -> str:
        """根据参数生成哈希键"""
        data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.md5(data.encode()).hexdigest()

    # ===== 基本操作 =====

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在返回 None
        """
        full_key = self._make_key(key)
        value = self.client.get(full_key)

        if value is None:
            return None

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    async def async_get(self, key: str) -> Optional[Any]:
        """异步获取缓存值"""
        full_key = self._make_key(key)
        value = await self.client.async_get(full_key)

        if value is None:
            return None

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间 (秒)，None 表示永不过期

        Returns:
            是否成功
        """
        full_key = self._make_key(key)

        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)

        return self.client.set(full_key, str(value), ttl or self.default_ttl)

    async def async_set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """异步设置缓存值"""
        full_key = self._make_key(key)

        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)

        return await self.client.async_set(full_key, str(value), ttl or self.default_ttl)

    def delete(self, key: str) -> bool:
        """删除缓存"""
        full_key = self._make_key(key)
        return self.client.delete(full_key) > 0

    async def async_delete(self, key: str) -> bool:
        """异步删除缓存"""
        full_key = self._make_key(key)
        return await self.client.async_delete(full_key) > 0

    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        full_key = self._make_key(key)
        return self.client.exists(full_key) > 0

    # ===== 高级操作 =====

    def get_or_set(
        self,
        key: str,
        getter: Callable[[], T],
        ttl: Optional[int] = None,
    ) -> T:
        """
        获取缓存，不存在则计算并缓存

        Args:
            key: 缓存键
            getter: 获取值的函数
            ttl: 过期时间

        Returns:
            缓存值或计算值
        """
        value = self.get(key)

        if value is not None:
            return value

        # 计算新值
        value = getter()
        self.set(key, value, ttl)

        return value

    async def async_get_or_set(
        self,
        key: str,
        getter: Callable[[], T],
        ttl: Optional[int] = None,
    ) -> T:
        """异步获取缓存，不存在则计算并缓存"""
        value = await self.async_get(key)

        if value is not None:
            return value

        # 计算新值
        import asyncio
        if asyncio.iscoroutinefunction(getter):
            value = await getter()
        else:
            value = getter()

        await self.async_set(key, value, ttl)

        return value

    def mget(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取缓存"""
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result

    def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """批量设置缓存"""
        for key, value in mapping.items():
            self.set(key, value, ttl)
        return True

    def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的所有缓存"""
        full_pattern = self._make_key(pattern)
        keys = []

        # 扫描匹配的键
        cursor = 0
        while True:
            cursor, partial = self.client.sync.scan(
                cursor=cursor,
                match=full_pattern,
                count=100,
            )
            keys.extend(partial)
            if cursor == 0:
                break

        if keys:
            return self.client.delete(*keys)

        return 0

    # ===== 缓存装饰器 =====

    def cached(
        self,
        key_prefix: str = "",
        ttl: Optional[int] = None,
        key_builder: Optional[Callable] = None,
    ):
        """
        缓存装饰器

        Args:
            key_prefix: 缓存键前缀
            ttl: 过期时间
            key_builder: 自定义键生成函数

        使用示例:
        ```python
        cache = CacheService()

        @cache.cached(key_prefix="user:", ttl=300)
        def get_user(user_id: str):
            return db.query_user(user_id)
        ```
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 生成缓存键
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    cache_key = f"{key_prefix}{self._hash_key(*args, **kwargs)}"

                # 尝试获取缓存
                cached = self.get(cache_key)
                if cached is not None:
                    return cached

                # 计算并缓存
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl)

                return result

            return wrapper

        return decorator

    def async_cached(
        self,
        key_prefix: str = "",
        ttl: Optional[int] = None,
        key_builder: Optional[Callable] = None,
    ):
        """
        异步缓存装饰器

        使用示例:
        ```python
        cache = CacheService()

        @cache.async_cached(key_prefix="user:", ttl=300)
        async def get_user(user_id: str):
            return await db.query_user(user_id)
        ```
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 生成缓存键
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    cache_key = f"{key_prefix}{self._hash_key(*args, **kwargs)}"

                # 尝试获取缓存
                cached = await self.async_get(cache_key)
                if cached is not None:
                    return cached

                # 计算并缓存
                import asyncio
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                await self.async_set(cache_key, result, ttl)

                return result

            return wrapper

        return decorator


# 全局缓存服务实例
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """获取全局缓存服务"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
