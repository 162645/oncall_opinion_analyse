"""
Markdown 文档解析器
支持解析 Markdown 格式，包括 YAML frontmatter
"""

import os
import re
from typing import Any, Dict, Optional

from .base import BaseParser, ParseResult, ParseStatus


class MarkdownParser(BaseParser):
    """
    Markdown 文档解析器

    支持:
    - 标准 Markdown
    - YAML frontmatter
    - 标题层级提取
    - 代码块识别
    """

    supported_extensions = ["md", "markdown"]
    name = "markdown"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.extract_frontmatter = config.get("extract_frontmatter", True) if config else True

    async def parse(self, file_path: str) -> ParseResult:
        """解析 Markdown 文档"""
        if not os.path.exists(file_path):
            return ParseResult(
                status=ParseStatus.FAILED,
                content="",
                error=f"File not found: {file_path}",
            )

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_content = f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(file_path, "r", encoding="gbk") as f:
                    raw_content = f.read()
            except Exception as e:
                return ParseResult(
                    status=ParseStatus.FAILED,
                    content="",
                    error=f"Failed to read file: {e}",
                )

        metadata = {}
        frontmatter = {}
        content = raw_content

        # 提取 YAML frontmatter
        if self.extract_frontmatter and raw_content.startswith("---"):
            frontmatter, content = self._extract_frontmatter(raw_content)
            metadata["frontmatter"] = frontmatter

        # 提取标题结构
        sections = self._extract_sections(content)
        metadata["section_count"] = len(sections)

        # 提取代码块
        code_blocks = self._extract_code_blocks(content)
        metadata["code_block_count"] = len(code_blocks)

        # 提取标题
        title = frontmatter.get("title")
        if not title:
            # 从第一个标题提取
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            if title_match:
                title = title_match.group(1)

        return ParseResult(
            status=ParseStatus.SUCCESS,
            content=content,
            title=title,
            author=frontmatter.get("author"),
            metadata=metadata,
            sections=sections,
        )

    def _extract_frontmatter(self, content: str) -> tuple:
        """提取 YAML frontmatter"""
        import yaml

        if not content.startswith("---"):
            return {}, content

        # 查找结束标记
        end_match = re.search(r"\n---\n", content[4:])
        if not end_match:
            return {}, content

        frontmatter_str = content[4:end_match.end() + 1]
        remaining_content = content[end_match.end() + 4:]

        try:
            frontmatter = yaml.safe_load(frontmatter_str)
            if not isinstance(frontmatter, dict):
                frontmatter = {}
        except yaml.YAMLError:
            frontmatter = {}

        return frontmatter, remaining_content

    def _extract_sections(self, content: str) -> list:
        """提取文档结构"""
        sections = []
        lines = content.split("\n")

        for line in lines:
            # 匹配标题
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2)
                sections.append({
                    "type": "heading",
                    "level": level,
                    "content": title,
                })

        return sections

    def _extract_code_blocks(self, content: str) -> list:
        """提取代码块"""
        code_blocks = []
        pattern = r"```(\w*)\n(.*?)```"

        for match in re.finditer(pattern, content, re.DOTALL):
            code_blocks.append({
                "language": match.group(1) or "unknown",
                "content": match.group(2)[:100] + "..." if len(match.group(2)) > 100 else match.group(2),
            })

        return code_blocks
