"""
Redis 客户端
封装 Redis 连接和基本操作
"""

import json
import time
from typing import Any, Dict, List, Optional, Union
import redis
from redis import Redis
from redis.asyncio import Redis as AsyncRedis


class RedisClient:
    """
    Redis 客户端

    支持同步和异步操作
    """

    def __init__(
        self,
        url: str = "redis://localhost:6379",
        db: int = 0,
        password: Optional[str] = None,
        decode_responses: bool = True,
    ):
        """
        初始化 Redis 客户端

        Args:
            url: Redis 连接 URL
            db: 数据库编号
            password: 密码
            decode_responses: 是否自动解码响应
        """
        self.url = url
        self.db = db
        self.password = password
        self.decode_responses = decode_responses
        self._sync_client: Optional[Redis] = None
        self._async_client: Optional[AsyncRedis] = None

    @property
    def sync(self) -> Redis:
        """获取同步客户端"""
        if self._sync_client is None:
            self._sync_client = redis.from_url(
                self.url,
                db=self.db,
                password=self.password,
                decode_responses=self.decode_responses,
            )
        return self._sync_client

    @property
    def async_client(self) -> AsyncRedis:
        """获取异步客户端"""
        if self._async_client is None:
            self._async_client = AsyncRedis.from_url(
                self.url,
                db=self.db,
                password=self.password,
                decode_responses=self.decode_responses,
            )
        return self._async_client

    # ===== 同步操作 =====

    def get(self, key: str) -> Optional[str]:
        """获取值"""
        return self.sync.get(key)

    def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None,
    ) -> bool:
        """设置值"""
        if ttl:
            return self.sync.setex(key, ttl, value)
        return self.sync.set(key, value)

    def delete(self, *keys: str) -> int:
        """删除键"""
        return self.sync.delete(*keys)

    def exists(self, *keys: str) -> int:
        """检查键是否存在"""
        return self.sync.exists(*keys)

    def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        return self.sync.expire(key, seconds)

    def ttl(self, key: str) -> int:
        """获取剩余过期时间"""
        return self.sync.ttl(key)

    def incr(self, key: str) -> int:
        """递增"""
        return self.sync.incr(key)

    def decr(self, key: str) -> int:
        """递减"""
        return self.sync.decr(key)

    # ===== Hash 操作 =====

    def hget(self, name: str, key: str) -> Optional[str]:
        """获取 Hash 字段"""
        return self.sync.hget(name, key)

    def hset(self, name: str, key: str, value: str) -> int:
        """设置 Hash 字段"""
        return self.sync.hset(name, key, value)

    def hgetall(self, name: str) -> Dict[str, str]:
        """获取所有 Hash 字段"""
        return self.sync.hgetall(name)

    def hdel(self, name: str, *keys: str) -> int:
        """删除 Hash 字段"""
        return self.sync.hdel(name, *keys)

    # ===== List 操作 =====

    def lpush(self, name: str, *values: str) -> int:
        """左侧插入列表"""
        return self.sync.lpush(name, *values)

    def rpush(self, name: str, *values: str) -> int:
        """右侧插入列表"""
        return self.sync.rpush(name, *values)

    def lpop(self, name: str) -> Optional[str]:
        """左侧弹出"""
        return self.sync.lpop(name)

    def rpop(self, name: str) -> Optional[str]:
        """右侧弹出"""
        return self.sync.rpop(name)

    def lrange(self, name: str, start: int, end: int) -> List[str]:
        """获取列表范围"""
        return self.sync.lrange(name, start, end)

    # ===== Set 操作 =====

    def sadd(self, name: str, *values: str) -> int:
        """添加到集合"""
        return self.sync.sadd(name, *values)

    def srem(self, name: str, *values: str) -> int:
        """从集合移除"""
        return self.sync.srem(name, *values)

    def smembers(self, name: str) -> set:
        """获取集合所有成员"""
        return self.sync.smembers(name)

    # ===== 异步操作 =====

    async def async_get(self, key: str) -> Optional[str]:
        """异步获取值"""
        return await self.async_client.get(key)

    async def async_set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None,
    ) -> bool:
        """异步设置值"""
        if ttl:
            return await self.async_client.setex(key, ttl, value)
        return await self.async_client.set(key, value)

    async def async_delete(self, *keys: str) -> int:
        """异步删除键"""
        return await self.async_client.delete(*keys)

    async def async_exists(self, *keys: str) -> int:
        """异步检查键是否存在"""
        return await self.async_client.exists(*keys)

    # ===== 工具方法 =====

    def ping(self) -> bool:
        """测试连接"""
        try:
            return self.sync.ping()
        except Exception:
            return False

    async def async_ping(self) -> bool:
        """异步测试连接"""
        try:
            return await self.async_client.ping()
        except Exception:
            return False

    def info(self) -> Dict[str, Any]:
        """获取服务器信息"""
        return self.sync.info()

    def flushdb(self) -> bool:
        """清空当前数据库"""
        return self.sync.flushdb()

    def close(self) -> None:
        """关闭连接"""
        if self._sync_client:
            self._sync_client.close()
        if self._async_client:
            import asyncio
            asyncio.create_task(self._async_client.close())


# 全局客户端实例
_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """获取全局 Redis 客户端"""
    global _client
    if _client is None:
        import os
        url = os.getenv("REDIS_URL", "redis://localhost:6379")
        _client = RedisClient(url=url)
    return _client
