"""
存储模块
提供文件存储服务
"""

from .minio_storage import MinIOStorage
from .local_storage import LocalStorage
from .base import StorageService, FileInfo

__all__ = [
    "MinIOStorage",
    "LocalStorage",
    "StorageService",
    "FileInfo",
]
