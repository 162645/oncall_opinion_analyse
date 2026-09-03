"""
PDF 文档解析器
支持使用 PyMuPDF 或 pdfplumber 解析 PDF
"""

import os
from typing import Any, Dict, Optional

from .base import BaseParser, ParseResult, ParseStatus


class PDFParser(BaseParser):
    """
    PDF 文档解析器

    支持两种后端:
    1. PyMuPDF (fitz) - 更快，支持 OCR
    2. pdfplumber - 更好的表格提取
    """

    supported_extensions = ["pdf"]
    name = "pdf"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.preferred_backend = config.get("backend", "pymupdf") if config else "pymupdf"
        self._backend = None

    def _get_backend(self):
        """获取解析后端"""
        if self._backend is not None:
            return self._backend

        # 尝试加载 PyMuPDF
        if self.preferred_backend == "pymupdf":
            try:
                import fitz
                self._backend = "pymupdf"
                return "pymupdf"
            except ImportError:
                pass

        # 尝试加载 pdfplumber
        try:
            import pdfplumber
            self._backend = "pdfplumber"
            return "pdfplumber"
        except ImportError:
            pass

        return None

    async def parse(self, file_path: str) -> ParseResult:
        """解析 PDF 文档"""
        if not os.path.exists(file_path):
            return ParseResult(
                status=ParseStatus.FAILED,
                content="",
                error=f"File not found: {file_path}",
            )

        backend = self._get_backend()

        if backend == "pymupdf":
            return await self._parse_with_pymupdf(file_path)
        elif backend == "pdfplumber":
            return await self._parse_with_pdfplumber(file_path)
        else:
            return ParseResult(
                status=ParseStatus.FAILED,
                content="",
                error="No PDF parser available. Install pymupdf or pdfplumber.",
            )

    async def _parse_with_pymupdf(self, file_path: str) -> ParseResult:
        """使用 PyMuPDF 解析"""
        import fitz

        try:
            doc = fitz.open(file_path)
            content_parts = []
            metadata = {}
            sections = []
            tables = []

            # 提取元数据
            meta = doc.metadata
            if meta:
                metadata = {
                    "title": meta.get("title"),
                    "author": meta.get("author"),
                    "subject": meta.get("subject"),
                    "keywords": meta.get("keywords"),
                    "creator": meta.get("creator"),
                    "page_count": len(doc),
                }

            # 逐页提取文本
            for page_num, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    content_parts.append(text)
                    sections.append({
                        "type": "page",
                        "page": page_num + 1,
                        "content": text[:200] + "..." if len(text) > 200 else text,
                    })

                # 提取表格 (PyMuPDF 表格提取较弱)
                # 如果需要更好的表格提取，可以回退到 pdfplumber

            doc.close()

            content = "\n\n".join(content_parts)
            content = self._clean_content(content)

            return ParseResult(
                status=ParseStatus.SUCCESS,
                content=content,
                title=metadata.get("title"),
                author=metadata.get("author"),
                metadata=metadata,
                sections=sections,
                tables=tables,
            )

        except Exception as e:
            return ParseResult(
                status=ParseStatus.FAILED,
                content="",
                error=str(e),
            )

    async def _parse_with_pdfplumber(self, file_path: str) -> ParseResult:
        """使用 pdfplumber 解析"""
        import pdfplumber

        try:
            content_parts = []
            metadata = {}
            sections = []
            tables = []

            with pdfplumber.open(file_path) as pdf:
                metadata = {
                    "page_count": len(pdf.pages),
                }

                for page_num, page in enumerate(pdf.pages):
                    # 提取文本
                    text = page.extract_text()
                    if text:
                        content_parts.append(text)
                        sections.append({
                            "type": "page",
                            "page": page_num + 1,
                            "content": text[:200] + "..." if len(text) > 200 else text,
                        })

                    # 提取表格
                    page_tables = page.extract_tables()
                    for table in page_tables:
                        if table:
                            tables.append({
                                "page": page_num + 1,
                                "rows": len(table),
                                "data": table[:5],  # 只保存前 5 行
                            })

            content = "\n\n".join(content_parts)
            content = self._clean_content(content)

            return ParseResult(
                status=ParseStatus.SUCCESS,
                content=content,
                metadata=metadata,
                sections=sections,
                tables=tables,
            )

        except Exception as e:
            return ParseResult(
                status=ParseStatus.FAILED,
                content="",
                error=str(e),
            )
