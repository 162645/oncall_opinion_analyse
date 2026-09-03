"""
会话管理服务

使用 Redis 持久化存储会话数据，支持：
- 会话创建、获取、删除
- 消息历史记录
- 会话过期时间
"""

import json
import time
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.core.config import settings


class SessionService:
    """会话管理服务"""

    def __init__(self):
        self._redis = None
        self._prefix = "session:"
        self._expire_seconds = 3600 * 24  # 24小时过期
        self._memory_store: Dict[str, Dict] = {}  # 内存存储备用

    def _get_redis(self):
        """获取 Redis 客户端"""
        if self._redis is None:
            try:
                import redis
                self._redis = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True
                )
                # 测试连接
                self._redis.ping()
            except Exception as e:
                print(f"⚠️ Redis 连接失败，使用内存存储: {e}")
                self._redis = None
        return self._redis

    def _session_key(self, session_id: str) -> str:
        """生成 Redis key"""
        return f"{self._prefix}{session_id}"

    def _sessions_list_key(self) -> str:
        """会话列表 key"""
        return f"{self._prefix}list"

    async def create_session(
        self,
        session_id: str,
        mode: str = "sequential",
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """创建新会话"""
        now = datetime.now().isoformat()
        session = {
            "session_id": session_id,
            "created_at": now,
            "updated_at": now,
            "mode": mode,
            "messages": [],
            "message_count": 0,
            "metadata": metadata or {},
            "title": "新对话"
        }

        redis = self._get_redis()
        if redis:
            redis.setex(
                self._session_key(session_id),
                self._expire_seconds,
                json.dumps(session, ensure_ascii=False)
            )
            # 添加到会话列表
            redis.lpush(self._sessions_list_key(), session_id)
            redis.expire(self._sessions_list_key(), self._expire_seconds)
        else:
            self._memory_store[session_id] = session

        return session

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话"""
        redis = self._get_redis()
        if redis:
            data = redis.get(self._session_key(session_id))
            if data:
                return json.loads(data)
            return None
        else:
            return self._memory_store.get(session_id)

    async def update_session(
        self,
        session_id: str,
        messages: List[Dict],
        title: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """更新会话"""
        session = await self.get_session(session_id)
        if not session:
            return None

        session["messages"] = messages
        session["message_count"] = len(messages)
        session["updated_at"] = datetime.now().isoformat()

        # 自动生成标题（取第一条用户消息的前20字）
        if not title and messages:
            for msg in messages:
                if msg.get("role") == "user":
                    title = msg.get("content", "")[:20]
                    if len(msg.get("content", "")) > 20:
                        title += "..."
                    break
        if title:
            session["title"] = title

        redis = self._get_redis()
        if redis:
            redis.setex(
                self._session_key(session_id),
                self._expire_seconds,
                json.dumps(session, ensure_ascii=False)
            )
        else:
            self._memory_store[session_id] = session

        return session

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """添加消息到会话"""
        session = await self.get_session(session_id)
        if not session:
            return None

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        session["messages"].append(message)

        # 更新标题（如果是第一条用户消息）
        title = None
        if role == "user" and session["message_count"] == 0:
            title = content[:20]
            if len(content) > 20:
                title += "..."

        return await self.update_session(session_id, session["messages"], title)

    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        redis = self._get_redis()
        if redis:
            redis.delete(self._session_key(session_id))
            redis.lrem(self._sessions_list_key(), 0, session_id)
        else:
            if session_id in self._memory_store:
                del self._memory_store[session_id]
            else:
                return False
        return True

    async def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取会话列表"""
        redis = self._get_redis()
        sessions = []

        if redis:
            # 从列表获取 session IDs
            session_ids = redis.lrange(self._sessions_list_key(), offset, offset + limit - 1)
            for sid in session_ids:
                session = await self.get_session(sid)
                if session:
                    # 不返回完整消息，只返回摘要
                    sessions.append({
                        "session_id": session["session_id"],
                        "title": session.get("title", "新对话"),
                        "created_at": session["created_at"],
                        "updated_at": session.get("updated_at", session["created_at"]),
                        "message_count": session["message_count"],
                        "mode": session["mode"],
                    })
        else:
            # 内存存储
            for sid, session in self._memory_store.items():
                sessions.append({
                    "session_id": session["session_id"],
                    "title": session.get("title", "新对话"),
                    "created_at": session["created_at"],
                    "updated_at": session.get("updated_at", session["created_at"]),
                    "message_count": session["message_count"],
                    "mode": session["mode"],
                })

        # 按更新时间倒序排序
        sessions.sort(key=lambda x: x.get("updated_at", x.get("created_at", "")), reverse=True)
        return sessions[:limit]

    async def clear_all_sessions(self) -> int:
        """清空所有会话"""
        redis = self._get_redis()
        if redis:
            # 获取所有 session keys
            keys = redis.keys(f"{self._prefix}*")
            if keys:
                redis.delete(*keys)
                return len(keys) - 1  # 减去 list key
            return 0
        else:
            count = len(self._memory_store)
            self._memory_store.clear()
            return count


# 单例
_session_service: Optional[SessionService] = None


def get_session_service() -> SessionService:
    """获取会话服务单例"""
    global _session_service
    if _session_service is None:
        _session_service = SessionService()
    return _session_service
