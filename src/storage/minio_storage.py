"""
MinIO 对象存储
生产环境推荐使用
"""

import io
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, BinaryIO

from .base import StorageService, FileInfo


class MinIOStorage(StorageService):
    """
    MinIO 对象存储

    S3 兼容的对象存储服务，适合生产环境
    """

    def __init__(
        self,
        endpoint: str = "localhost:9000",
        access_key: str = "minioadmin",
        secret_key: str = "minioadmin",
        bucket_name: str = "oncall-knowledge",
        secure: bool = False,
    ):
        """
        初始化 MinIO 存储

        Args:
            endpoint: MinIO 服务地址
            access_key: 访问密钥
            secret_key: 秘密密钥
            bucket_name: 存储桶名称
            secure: 是否使用 HTTPS
        """
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.secure = secure
        self._client = None

    def _get_client(self):
        """获取 MinIO 客户端"""
        if self._client is None:
            try:
                from minio import Minio
                self._client = Minio(
                    self.endpoint,
                    access_key=self.access_key,
                    secret_key=self.secret_key,
                    secure=self.secure,
                )

                # 确保存储桶存在
                if not self._client.bucket_exists(self.bucket_name):
                    self._client.make_bucket(self.bucket_name)

            except ImportError:
                raise ImportError(
                    "minio package not installed. Run: pip install minio"
                )

        return self._client

    def _generate_object_name(self, file_name: str) -> str:
        """生成对象名称"""
        # 使用日期和 UUID 组织路径
        date_prefix = datetime.now().strftime("%Y/%m/%d")
        file_id = str(uuid.uuid4())
        ext = file_name.rsplit(".", 1)[-1] if "." in file_name else ""
        object_name = f"{date_prefix}/{file_id}"
        if ext:
            object_name += f".{ext}"
        return object_name

    async def upload(
        self,
        file_name: str,
        file_data: BinaryIO,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FileInfo:
        """上传文件"""
        client = self._get_client()

        # 生成对象名称
        object_name = self._generate_object_name(file_name)

        # 读取内容
        content = file_data.read()
        file_size = len(content)

        # 计算 ETag
        etag = hashlib.md5(content).hexdigest()

        # 上传
        client.put_object(
            self.bucket_name,
            object_name,
            io.BytesIO(content),
            file_size,
            content_type=content_type or "application/octet-stream",
            metadata=metadata,
        )

        # 构建路径
        file_path = f"minio://{self.bucket_name}/{object_name}"

        now = datetime.now()
        return FileInfo(
            file_id=object_name.split("/")[-1].rsplit(".", 1)[0],
            file_name=file_name,
            file_path=file_path,
            file_size=file_size,
            content_type=content_type or "application/octet-stream",
            etag=etag,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )

    async def download(self, file_path: str) -> bytes:
        """下载文件"""
        client = self._get_client()

        # 从路径提取对象名称
        # minio://bucket/path/to/object
        parts = file_path.replace("minio://", "").split("/", 1)
        if len(parts) == 2:
            bucket, object_name = parts
        else:
            object_name = file_path

        # 下载
        response = client.get_object(self.bucket_name, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    async def delete(self, file_path: str) -> bool:
        """删除文件"""
        client = self._get_client()

        parts = file_path.replace("minio://", "").split("/", 1)
        if len(parts) == 2:
            _, object_name = parts
        else:
            object_name = file_path

        try:
            client.remove_object(self.bucket_name, object_name)
            return True
        except Exception:
            return False

    async def get_info(self, file_path: str) -> Optional[FileInfo]:
        """获取文件信息"""
        client = self._get_client()

        parts = file_path.replace("minio://", "").split("/", 1)
        if len(parts) == 2:
            _, object_name = parts
        else:
            object_name = file_path

        try:
            stat = client.stat_object(self.bucket_name, object_name)

            return FileInfo(
                file_id=object_name.split("/")[-1].rsplit(".", 1)[0],
                file_name=object_name.split("/")[-1],
                file_path=file_path,
                file_size=stat.size,
                content_type=stat.content_type,
                etag=stat.etag,
                metadata=dict(stat.metadata) if stat.metadata else {},
                created_at=stat.last_modified,
                updated_at=stat.last_modified,
            )
        except Exception:
            return None

    async def list_files(
        self,
        prefix: Optional[str] = None,
        limit: int = 100,
    ) -> List[FileInfo]:
        """列出文件"""
        client = self._get_client()

        files = []
        objects = client.list_objects(
            self.bucket_name,
            prefix=prefix,
            recursive=True,
        )

        for obj in objects:
            if len(files) >= limit:
                break

            files.append(FileInfo(
                file_id=obj.object_name.split("/")[-1].rsplit(".", 1)[0],
                file_name=obj.object_name.split("/")[-1],
                file_path=f"minio://{self.bucket_name}/{obj.object_name}",
                file_size=obj.size,
                content_type=obj.content_type or "application/octet-stream",
                etag=obj.etag,
                metadata={},
                created_at=obj.last_modified,
                updated_at=obj.last_modified,
            ))

        return files

    async def get_presigned_url(
        self,
        file_path: str,
        expires: int = 3600,
    ) -> Optional[str]:
        """获取预签名 URL"""
        client = self._get_client()

        parts = file_path.replace("minio://", "").split("/", 1)
        if len(parts) == 2:
            _, object_name = parts
        else:
            object_name = file_path

        try:
            url = client.presigned_get_object(
                self.bucket_name,
                object_name,
                expires=timedelta(seconds=expires),
            )
            return url
        except Exception:
            return None
