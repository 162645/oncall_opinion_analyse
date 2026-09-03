"""
存储服务基类
定义文件存储接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, BinaryIO


@dataclass
class FileInfo:
    """文件信息"""
    file_id: str
    file_name: str
    file_path: str
    file_size: int
    content_type: str
    etag: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_id": self.file_id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "content_type": self.content_type,
            "etag": self.etag,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class StorageService(ABC):
    """
    存储服务基类

    所有存储服务都应继承此类
    """

    @abstractmethod
    async def upload(
        self,
        file_name: str,
        file_data: BinaryIO,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FileInfo:
        """
        上传文件

        Args:
            file_name: 文件名
            file_data: 文件数据 (二进制流)
            content_type: 内容类型
            metadata: 元数据

        Returns:
            FileInfo: 文件信息
        """
        pass

    @abstractmethod
    async def download(self, file_path: str) -> bytes:
        """
        下载文件

        Args:
            file_path: 文件路径

        Returns:
            bytes: 文件内容
        """
        pass

    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """
        删除文件

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否成功
        """
        pass

    @abstractmethod
    async def get_info(self, file_path: str) -> Optional[FileInfo]:
        """
        获取文件信息

        Args:
            file_path: 文件路径

        Returns:
            FileInfo: 文件信息，不存在返回 None
        """
        pass

    @abstractmethod
    async def list_files(
        self,
        prefix: Optional[str] = None,
        limit: int = 100,
    ) -> List[FileInfo]:
        """
        列出文件

        Args:
            prefix: 路径前缀
            limit: 最大数量

        Returns:
            List[FileInfo]: 文件列表
        """
        pass

    @abstractmethod
    async def get_presigned_url(
        self,
        file_path: str,
        expires: int = 3600,
    ) -> Optional[str]:
        """
        获取预签名 URL

        Args:
            file_path: 文件路径
            expires: 过期时间 (秒)

        Returns:
            str: 预签名 URL
        """
        pass
