"""
本地文件存储
用于开发和测试环境
"""

import os
import uuid
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, BinaryIO

from .base import StorageService, FileInfo


class LocalStorage(StorageService):
    """
    本地文件存储

    用于开发和测试环境，将文件存储在本地文件系统
    """

    def __init__(self, base_path: str = "/tmp/oncall_storage"):
        """
        初始化本地存储

        Args:
            base_path: 存储根目录
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # 元数据存储
        self._metadata_file = self.base_path / ".metadata.json"
        self._metadata: Dict[str, Dict] = self._load_metadata()

    def _load_metadata(self) -> Dict[str, Dict]:
        """加载元数据"""
        if self._metadata_file.exists():
            try:
                import json
                with open(self._metadata_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_metadata(self) -> None:
        """保存元数据"""
        import json
        with open(self._metadata_file, "w") as f:
            json.dump(self._metadata, f, indent=2)

    def _get_file_path(self, file_id: str) -> Path:
        """获取文件物理路径"""
        # 使用文件 ID 的前 2 位作为子目录
        subdir = file_id[:2]
        return self.base_path / subdir / file_id

    async def upload(
        self,
        file_name: str,
        file_data: BinaryIO,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FileInfo:
        """上传文件"""
        # 生成文件 ID
        file_id = str(uuid.uuid4())

        # 读取文件内容
        content = file_data.read()
        file_size = len(content)

        # 计算 ETag
        etag = hashlib.md5(content).hexdigest()

        # 保存文件
        file_path = self._get_file_path(file_id)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(content)

        # 构建文件路径标识
        path_identifier = f"local://{file_id}/{file_name}"

        # 保存元数据
        now = datetime.now()
        self._metadata[file_id] = {
            "file_id": file_id,
            "file_name": file_name,
            "file_path": path_identifier,
            "file_size": file_size,
            "content_type": content_type or "application/octet-stream",
            "etag": etag,
            "metadata": metadata or {},
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        self._save_metadata()

        return FileInfo(
            file_id=file_id,
            file_name=file_name,
            file_path=path_identifier,
            file_size=file_size,
            content_type=content_type or "application/octet-stream",
            etag=etag,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )

    async def download(self, file_path: str) -> bytes:
        """下载文件"""
        # 从路径中提取文件 ID
        file_id = file_path.split("/")[2] if "://" in file_path else file_path

        file_path_disk = self._get_file_path(file_id)
        if not file_path_disk.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path_disk, "rb") as f:
            return f.read()

    async def delete(self, file_path: str) -> bool:
        """删除文件"""
        file_id = file_path.split("/")[2] if "://" in file_path else file_path

        file_path_disk = self._get_file_path(file_id)
        if not file_path_disk.exists():
            return False

        file_path_disk.unlink()

        # 删除元数据
        if file_id in self._metadata:
            del self._metadata[file_id]
            self._save_metadata()

        return True

    async def get_info(self, file_path: str) -> Optional[FileInfo]:
        """获取文件信息"""
        file_id = file_path.split("/")[2] if "://" in file_path else file_path

        if file_id not in self._metadata:
            return None

        meta = self._metadata[file_id]
        return FileInfo(
            file_id=meta["file_id"],
            file_name=meta["file_name"],
            file_path=meta["file_path"],
            file_size=meta["file_size"],
            content_type=meta["content_type"],
            etag=meta.get("etag"),
            metadata=meta.get("metadata", {}),
            created_at=datetime.fromisoformat(meta["created_at"]) if meta.get("created_at") else None,
            updated_at=datetime.fromisoformat(meta["updated_at"]) if meta.get("updated_at") else None,
        )

    async def list_files(
        self,
        prefix: Optional[str] = None,
        limit: int = 100,
    ) -> List[FileInfo]:
        """列出文件"""
        files = []

        for file_id, meta in self._metadata.items():
            if prefix and not meta["file_name"].startswith(prefix):
                continue

            files.append(FileInfo(
                file_id=meta["file_id"],
                file_name=meta["file_name"],
                file_path=meta["file_path"],
                file_size=meta["file_size"],
                content_type=meta["content_type"],
                etag=meta.get("etag"),
                metadata=meta.get("metadata", {}),
                created_at=datetime.fromisoformat(meta["created_at"]) if meta.get("created_at") else None,
                updated_at=datetime.fromisoformat(meta["updated_at"]) if meta.get("updated_at") else None,
            ))

            if len(files) >= limit:
                break

        return files

    async def get_presigned_url(
        self,
        file_path: str,
        expires: int = 3600,
    ) -> Optional[str]:
        """获取预签名 URL (本地存储不支持)"""
        # 本地存储不支持预签名 URL
        # 可以返回一个本地文件路径
        file_id = file_path.split("/")[2] if "://" in file_path else file_path
        file_path_disk = self._get_file_path(file_id)

        if file_path_disk.exists():
            return str(file_path_disk)

        return None
