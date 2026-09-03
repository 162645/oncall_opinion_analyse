"""
纯文本文档解析器
支持解析 TXT 格式
"""

import os
from typing import Any, Dict, Optional

from .base import BaseParser, ParseResult, ParseStatus


class TextParser(BaseParser):
    """
    纯文本文档解析器

    支持:
    - 编码自动检测
    - 基本结构识别
    """

    supported_extensions = ["txt", "text"]
    name = "text"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.encodings = config.get("encodings", ["utf-8", "gbk", "gb2312", "latin-1"]) if config else ["utf-8", "gbk", "gb2312", "latin-1"]

    async def parse(self, file_path: str) -> ParseResult:
        """解析文本文档"""
        if not os.path.exists(file_path):
            return ParseResult(
                status=ParseStatus.FAILED,
                content="",
                error=f"File not found: {file_path}",
            )

        # 尝试不同编码读取
        content = None
        used_encoding = None

        for encoding in self.encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read()
                used_encoding = encoding
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            return ParseResult(
                status=ParseStatus.FAILED,
                content="",
                error="Failed to decode file with supported encodings",
            )

        # 提取基本结构
        sections = self._extract_sections(content)

        # 尝试从第一行提取标题
        lines = content.strip().split("\n")
        title = lines[0].strip() if lines else None

        metadata = {
            "encoding": used_encoding,
            "line_count": len(lines),
        }

        return ParseResult(
            status=ParseStatus.SUCCESS,
            content=content,
            title=title if title and len(title) < 100 else None,
            metadata=metadata,
            sections=sections,
        )

    def _extract_sections(self, content: str) -> list:
        """提取文档结构"""
        sections = []
        lines = content.split("\n")

        current_section = None

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 检测可能是标题的行
            if stripped and len(stripped) < 100:
                # 全大写或以冒号结尾的行可能是标题
                if stripped.isupper() or stripped.endswith(":"):
                    if current_section:
                        sections.append(current_section)
                    current_section = {
                        "type": "section",
                        "title": stripped,
                        "line": i + 1,
                    }

        if current_section:
            sections.append(current_section)

        return sections
