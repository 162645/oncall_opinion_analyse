"""
文档解析器基类
定义解析器接口和数据结构
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class ParseStatus(Enum):
    """解析状态"""
    SUCCESS = "success"
    PARTIAL = "partial"      # 部分成功
    FAILED = "failed"


@dataclass
class ParseResult:
    """解析结果"""
    status: ParseStatus
    content: str                                    # 提取的文本内容
    title: Optional[str] = None                     # 文档标题
    author: Optional[str] = None                    # 作者
    metadata: Dict[str, Any] = field(default_factory=dict)
    sections: List[Dict[str, Any]] = field(default_factory=list)  # 文档结构
    tables: List[Dict[str, Any]] = field(default_factory=list)    # 表格数据
    images: List[Dict[str, Any]] = field(default_factory=list)    # 图片信息
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.status in [ParseStatus.SUCCESS, ParseStatus.PARTIAL]

    @property
    def word_count(self) -> int:
        """字数统计"""
        return len(self.content) if self.content else 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "content": self.content,
            "title": self.title,
            "author": self.author,
            "metadata": self.metadata,
            "sections": self.sections,
            "tables": self.tables,
            "images": self.images,
            "word_count": self.word_count,
            "error": self.error,
            "warnings": self.warnings,
        }


class BaseParser(ABC):
    """
    文档解析器基类

    所有解析器都应继承此类并实现 parse 方法
    """

    # 支持的文件扩展名
    supported_extensions: List[str] = []

    # 解析器名称
    name: str = "base"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    @abstractmethod
    async def parse(self, file_path: str) -> ParseResult:
        """
        解析文档

        Args:
            file_path: 文件路径

        Returns:
            ParseResult: 解析结果
        """
        pass

    def can_parse(self, file_path: str) -> bool:
        """检查是否可以解析该文件"""
        ext = file_path.lower().split(".")[-1] if "." in file_path else ""
        return ext in self.supported_extensions

    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """从内容中提取元数据"""
        # 默认实现：统计基本信息
        lines = content.split("\n") if content else []
        return {
            "line_count": len(lines),
            "word_count": len(content) if content else 0,
            "char_count": len(content) if content else 0,
        }

    def _clean_content(self, content: str) -> str:
        """清理内容"""
        if not content:
            return ""

        # 移除多余的空白行
        lines = content.split("\n")
        cleaned_lines = []
        prev_empty = False

        for line in lines:
            line = line.rstrip()
            is_empty = not line.strip()

            # 跳过连续的空行
            if is_empty and prev_empty:
                continue

            cleaned_lines.append(line)
            prev_empty = is_empty

        return "\n".join(cleaned_lines)
