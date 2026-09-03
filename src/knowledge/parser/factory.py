"""
文档解析器工厂
根据文件类型自动选择合适的解析器
"""

from typing import Any, Dict, Optional, Type

from .base import BaseParser, ParseResult, ParseStatus
from .pdf_parser import PDFParser
from .word_parser import WordParser
from .markdown_parser import MarkdownParser
from .text_parser import TextParser


class ParserFactory:
    """
    文档解析器工厂

    根据文件扩展名自动选择合适的解析器
    """

    # 注册的解析器
    _parsers: Dict[str, Type[BaseParser]] = {
        "pdf": PDFParser,
        "doc": WordParser,
        "docx": WordParser,
        "md": MarkdownParser,
        "markdown": MarkdownParser,
        "txt": TextParser,
        "text": TextParser,
    }

    # MIME 类型映射
    _mime_mapping = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/msword": "doc",
        "text/markdown": "md",
        "text/plain": "txt",
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._instances: Dict[str, BaseParser] = {}

    def get_parser(self, file_path: str, file_type: Optional[str] = None) -> Optional[BaseParser]:
        """
        获取解析器

        Args:
            file_path: 文件路径
            file_type: 文件类型 (可选，用于覆盖扩展名检测)

        Returns:
            BaseParser: 解析器实例
        """
        # 确定文件类型
        if file_type:
            ext = file_type.lower()
        else:
            ext = file_path.lower().split(".")[-1] if "." in file_path else ""

        # 获取解析器类
        parser_class = self._parsers.get(ext)

        if not parser_class:
            # 尝试使用文本解析器作为后备
            parser_class = TextParser

        # 复用实例
        parser_key = parser_class.name
        if parser_key not in self._instances:
            self._instances[parser_key] = parser_class(self.config.get(parser_key))

        return self._instances[parser_key]

    def register_parser(self, extension: str, parser_class: Type[BaseParser]) -> None:
        """
        注册自定义解析器

        Args:
            extension: 文件扩展名
            parser_class: 解析器类
        """
        self._parsers[extension.lower()] = parser_class

    def get_supported_types(self) -> list:
        """获取支持的文件类型"""
        return list(self._parsers.keys())

    def can_parse(self, file_path: str) -> bool:
        """检查是否支持解析该文件"""
        ext = file_path.lower().split(".")[-1] if "." in file_path else ""
        return ext in self._parsers

    def parse_sync(self, file_path: str, file_type: Optional[str] = None) -> ParseResult:
        """
        同步解析文档（用于线程池）

        Args:
            file_path: 文件路径
            file_type: 文件类型 (可选)

        Returns:
            ParseResult: 解析结果
        """
        parser = self.get_parser(file_path, file_type)

        if not parser:
            return ParseResult(
                status="failed",
                content="",
                error=f"No parser available for file type: {file_path}",
            )

        # 直接读取文件内容（同步）
        import os
        if not os.path.exists(file_path):
            return ParseResult(
                status="failed",
                content="",
                error=f"File not found: {file_path}",
            )

        try:
            with open(file_path, 'rb') as f:
                content = f.read()

            # 简单解析：直接解码文本
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text = content.decode('gbk')
                except:
                    text = content.decode('utf-8', errors='ignore')

            # 提取标题
            title = os.path.basename(file_path)
            import re
            title_match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
            if title_match:
                title = title_match.group(1)

            return ParseResult(
                status=ParseStatus.SUCCESS,
                content=text,
                title=title,
                metadata={
                    "line_count": len(text.split('\n')),
                    "word_count": len(text),
                },
            )
        except Exception as e:
            return ParseResult(
                status="failed",
                content="",
                error=str(e),
            )

    async def parse(self, file_path: str, file_type: Optional[str] = None) -> ParseResult:
        """
        解析文档

        Args:
            file_path: 文件路径
            file_type: 文件类型 (可选)

        Returns:
            ParseResult: 解析结果
        """
        parser = self.get_parser(file_path, file_type)

        if not parser:
            return ParseResult(
                status="failed",
                content="",
                error=f"No parser available for file type: {file_path}",
            )

        return await parser.parse(file_path)

    @classmethod
    def from_mime_type(cls, mime_type: str) -> Optional[str]:
        """根据 MIME 类型获取文件类型"""
        return cls._mime_mapping.get(mime_type)
