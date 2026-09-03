"""
知识库文档数据模型
定义文档、分块、元数据等核心数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class DocumentStatus(Enum):
    """文档状态"""
    PENDING = "pending"          # 待处理
    PROCESSING = "processing"    # 处理中
    READY = "ready"              # 就绪
    FAILED = "failed"            # 失败


class DocumentType(Enum):
    """文档类型"""
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    POWERPOINT = "powerpoint"
    MARKDOWN = "markdown"
    TEXT = "text"
    JSON = "json"
    CSV = "csv"
    HTML = "html"
    UNKNOWN = "unknown"


@dataclass
class DocumentChunk:
    """文档分块"""
    chunk_id: str
    doc_id: str
    content: str
    position: int                          # 在原文中的位置
    embedding: Optional[List[float]] = None
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "content": self.content,
            "position": self.position,
            "token_count": self.token_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentChunk":
        return cls(
            chunk_id=data["chunk_id"],
            doc_id=data["doc_id"],
            content=data["content"],
            position=data["position"],
            embedding=data.get("embedding"),
            token_count=data.get("token_count", 0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class KnowledgeDocument:
    """知识库文档"""
    id: str
    title: str
    content: str                           # 原始文本内容
    doc_type: DocumentType
    file_path: str                         # 存储路径
    file_name: str                         # 原始文件名
    file_size: int                         # 文件大小 (bytes)
    file_hash: str                         # 文件 MD5 哈希
    status: DocumentStatus = DocumentStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunks: List[DocumentChunk] = field(default_factory=list)
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    @property
    def chunk_count(self) -> int:
        """分块数量"""
        return len(self.chunks)

    @property
    def token_count(self) -> int:
        """总 Token 数"""
        return sum(chunk.token_count for chunk in self.chunks)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content[:500] + "..." if len(self.content) > 500 else self.content,
            "doc_type": self.doc_type.value,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "file_hash": self.file_hash,
            "status": self.status.value,
            "metadata": self.metadata,
            "chunk_count": self.chunk_count,
            "token_count": self.token_count,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeDocument":
        return cls(
            id=data["id"],
            title=data["title"],
            content=data["content"],
            doc_type=DocumentType(data["doc_type"]),
            file_path=data["file_path"],
            file_name=data["file_name"],
            file_size=data["file_size"],
            file_hash=data["file_hash"],
            status=DocumentStatus(data["status"]),
            metadata=data.get("metadata", {}),
            chunks=[DocumentChunk.from_dict(c) for c in data.get("chunks", [])],
            error_message=data.get("error_message"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            processed_at=datetime.fromisoformat(data["processed_at"]) if data.get("processed_at") else None,
        )


@dataclass
class KnowledgeStats:
    """知识库统计信息"""
    total_documents: int = 0
    total_chunks: int = 0
    total_tokens: int = 0
    total_size: int = 0                          # 总文件大小 (bytes)
    by_type: Dict[str, int] = field(default_factory=dict)  # 按类型统计
    by_status: Dict[str, int] = field(default_factory=dict)  # 按状态统计
    recent_uploads: int = 0                      # 最近 24 小时上传数

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_documents": self.total_documents,
            "total_chunks": self.total_chunks,
            "total_tokens": self.total_tokens,
            "total_size": self.total_size,
            "total_size_mb": round(self.total_size / (1024 * 1024), 2),
            "by_type": self.by_type,
            "by_status": self.by_status,
            "recent_uploads": self.recent_uploads,
        }


@dataclass
class SearchResult:
    """检索结果"""
    chunk_id: str
    doc_id: str
    doc_title: str
    content: str
    score: float                              # 相似度分数
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "doc_title": self.doc_title,
            "content": self.content,
            "score": self.score,
            "metadata": self.metadata,
        }


# 工具函数

def get_doc_type_from_extension(filename: str) -> DocumentType:
    """根据文件扩展名判断文档类型"""
    ext = filename.lower().split(".")[-1] if "." in filename else ""

    type_mapping = {
        "pdf": DocumentType.PDF,
        "doc": DocumentType.WORD,
        "docx": DocumentType.WORD,
        "xls": DocumentType.EXCEL,
        "xlsx": DocumentType.EXCEL,
        "ppt": DocumentType.POWERPOINT,
        "pptx": DocumentType.POWERPOINT,
        "md": DocumentType.MARKDOWN,
        "markdown": DocumentType.MARKDOWN,
        "txt": DocumentType.TEXT,
        "json": DocumentType.JSON,
        "csv": DocumentType.CSV,
        "html": DocumentType.HTML,
        "htm": DocumentType.HTML,
    }

    return type_mapping.get(ext, DocumentType.UNKNOWN)


def get_mime_type(doc_type: DocumentType) -> str:
    """获取 MIME 类型"""
    mime_mapping = {
        DocumentType.PDF: "application/pdf",
        DocumentType.WORD: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        DocumentType.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        DocumentType.POWERPOINT: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        DocumentType.MARKDOWN: "text/markdown",
        DocumentType.TEXT: "text/plain",
        DocumentType.JSON: "application/json",
        DocumentType.CSV: "text/csv",
        DocumentType.HTML: "text/html",
        DocumentType.UNKNOWN: "application/octet-stream",
    }
    return mime_mapping.get(doc_type, "application/octet-stream")
