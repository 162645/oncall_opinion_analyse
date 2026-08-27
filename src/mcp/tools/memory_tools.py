"""
内存/知识存储工具
提供持久化存储和知识检索功能
"""

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import threading

from ..base import ToolResult, ToolStatus


@dataclass
class MemoryItem:
    """内存项"""
    key: str
    value: Any
    created_at: float
    updated_at: float
    ttl: Optional[int] = None  # 秒
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() > self.created_at + self.ttl

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MemoryTools:
    """
    内存/知识存储工具

    提供:
    - save: 保存数据
    - load: 加载数据
    - delete: 删除数据
    - list_keys: 列出所有键
    - search: 搜索数据
    - clear: 清空存储
    """

    def __init__(self, storage_path: str = "/tmp/mcp_memory"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._memory_file = self.storage_path / "memory.json"
        self._lock = threading.Lock()
        self._cache: Dict[str, MemoryItem] = {}

        # 加载现有数据
        self._load_from_file()

    def get_handlers(self) -> Dict[str, Callable]:
        """获取工具处理器"""
        return {
            "memory_save": self.save,
            "memory_load": self.load,
            "memory_delete": self.delete,
            "memory_list": self.list_keys,
            "memory_search": self.search,
            "memory_clear": self.clear,
        }

    def _load_from_file(self) -> None:
        """从文件加载"""
        if self._memory_file.exists():
            try:
                with open(self._memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for key, item in data.items():
                        self._cache[key] = MemoryItem(**item)
            except Exception:
                pass

    def _save_to_file(self) -> None:
        """保存到文件"""
        try:
            with open(self._memory_file, "w", encoding="utf-8") as f:
                json.dump(
                    {k: v.to_dict() for k, v in self._cache.items()},
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception:
            pass

    async def save(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> ToolResult:
        """
        保存数据

        Args:
            key: 键名
            value: 值
            ttl: 过期时间（秒）
            tags: 标签
        """
        try:
            with self._lock:
                now = time.time()

                # 检查是否存在
                existing = self._cache.get(key)

                item = MemoryItem(
                    key=key,
                    value=value,
                    created_at=existing.created_at if existing else now,
                    updated_at=now,
                    ttl=ttl,
                    tags=tags or [],
                )

                self._cache[key] = item
                self._save_to_file()

                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        "key": key,
                        "created": item.created_at == now,
                        "ttl": ttl,
                    },
                )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )

    async def load(
        self,
        key: str,
        default: Any = None,
    ) -> ToolResult:
        """
        加载数据

        Args:
            key: 键名
            default: 默认值
        """
        try:
            with self._lock:
                item = self._cache.get(key)

                if item is None:
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={
                            "key": key,
                            "value": default,
                            "found": False,
                        },
                    )

                # 检查过期
                if item.is_expired():
                    del self._cache[key]
                    self._save_to_file()
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={
                            "key": key,
                            "value": default,
                            "found": False,
                            "expired": True,
                        },
                    )

                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        "key": key,
                        "value": item.value,
                        "found": True,
                        "tags": item.tags,
                        "created_at": item.created_at,
                        "updated_at": item.updated_at,
                    },
                )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )

    async def delete(self, key: str) -> ToolResult:
        """删除数据"""
        try:
            with self._lock:
                if key in self._cache:
                    del self._cache[key]
                    self._save_to_file()
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={"deleted": key},
                    )
                else:
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={"deleted": None, "not_found": True},
                    )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )

    async def list_keys(
        self,
        pattern: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> ToolResult:
        """
        列出键

        Args:
            pattern: 键名模式（支持 * 通配符）
            tag: 按标签过滤
        """
        try:
            with self._lock:
                keys = []

                for key, item in self._cache.items():
                    # 检查过期
                    if item.is_expired():
                        continue

                    # 模式匹配
                    if pattern:
                        import fnmatch
                        if not fnmatch.fnmatch(key, pattern):
                            continue

                    # 标签过滤
                    if tag and tag not in item.tags:
                        continue

                    keys.append({
                        "key": key,
                        "tags": item.tags,
                        "updated_at": item.updated_at,
                    })

                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        "keys": keys,
                        "total": len(keys),
                    },
                )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )

    async def search(
        self,
        query: str,
        search_value: bool = True,
    ) -> ToolResult:
        """
        搜索数据

        Args:
            query: 搜索关键词
            search_value: 是否搜索值
        """
        try:
            with self._lock:
                matches = []

                for key, item in self._cache.items():
                    if item.is_expired():
                        continue

                    matched = False
                    match_reason = []

                    # 搜索键
                    if query.lower() in key.lower():
                        matched = True
                        match_reason.append("key")

                    # 搜索值
                    if search_value:
                        value_str = json.dumps(item.value, ensure_ascii=False)
                        if query.lower() in value_str.lower():
                            matched = True
                            match_reason.append("value")

                    # 搜索标签
                    for tag in item.tags:
                        if query.lower() in tag.lower():
                            matched = True
                            match_reason.append("tag")

                    if matched:
                        matches.append({
                            "key": key,
                            "value": item.value,
                            "tags": item.tags,
                            "match_reason": match_reason,
                        })

                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        "query": query,
                        "matches": matches,
                        "total": len(matches),
                    },
                )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )

    async def clear(self) -> ToolResult:
        """清空存储"""
        try:
            with self._lock:
                count = len(self._cache)
                self._cache.clear()
                self._save_to_file()

                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"cleared": count},
                )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )
