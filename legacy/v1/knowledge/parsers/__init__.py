"""
文档解析器
支持工单、SOP文档、解决方案等多种格式
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ParsedDocument:
    """解析后的文档结构"""
    doc_id: str
    title: str
    content: str
    doc_type: str
    metadata: dict
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DocumentParser(ABC):
    """文档解析器基类"""

    @abstractmethod
    def parse(self, raw_content: str, **kwargs) -> ParsedDocument:
        """解析文档内容"""
        pass

    def clean_text(self, text: str) -> str:
        """清理文本内容"""
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        # 移除特殊字符
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        return text.strip()


class TicketParser(DocumentParser):
    """工单解析器"""

    def parse(self, raw_content: str, **kwargs) -> ParsedDocument:
        """
        解析工单内容

        工单格式示例:
        ---
        ticket_id: TK-12345
        title: 网络延迟异常
        severity: critical
        psm: example.service
        created_at: 2025-01-15T10:30:00Z
        ---
        ## 问题描述
        ...

        ## 根因分析
        ...

        ## 解决方案
        ...
        """
        metadata = {}

        # 解析 YAML frontmatter
        if raw_content.startswith('---'):
            parts = raw_content.split('---', 2)
            if len(parts) >= 3:
                frontmatter = parts[1].strip()
                content = parts[2].strip()

                # 解析 frontmatter 字段
                for line in frontmatter.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        metadata[key.strip()] = value.strip()
            else:
                content = raw_content
        else:
            content = raw_content

        # 提取结构化信息
        sections = self._extract_sections(content)

        return ParsedDocument(
            doc_id=metadata.get('ticket_id', kwargs.get('doc_id', '')),
            title=metadata.get('title', ''),
            content=self.clean_text(content),
            doc_type='ticket',
            metadata={
                **metadata,
                'sections': sections,
                'severity': metadata.get('severity', 'unknown'),
                'psm': metadata.get('psm', ''),
            },
            created_at=self._parse_datetime(metadata.get('created_at')),
        )

    def _extract_sections(self, content: str) -> dict:
        """提取文档章节"""
        sections = {}
        current_section = None
        current_content = []

        for line in content.split('\n'):
            if line.startswith('## '):
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = line[3:].strip()
                current_content = []
            else:
                current_content.append(line)

        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()

        return sections

    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """解析时间字符串"""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except ValueError:
            return None


class SOPParser(DocumentParser):
    """SOP 文档解析器"""

    def parse(self, raw_content: str, **kwargs) -> ParsedDocument:
        """
        解析 SOP 文档

        SOP 格式示例:
        ---
        sop_id: SOP-001
        title: 网络延迟排查流程
        category: network
        tags: [latency, troubleshooting]
        ---
        ## 适用场景
        ...

        ## 操作步骤
        1. ...
        2. ...

        ## 注意事项
        ...
        """
        metadata = {}

        # 解析 YAML frontmatter
        if raw_content.startswith('---'):
            parts = raw_content.split('---', 2)
            if len(parts) >= 3:
                frontmatter = parts[1].strip()
                content = parts[2].strip()

                for line in frontmatter.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        metadata[key.strip()] = value.strip()
            else:
                content = raw_content
        else:
            content = raw_content

        # 提取操作步骤
        steps = self._extract_steps(content)

        return ParsedDocument(
            doc_id=metadata.get('sop_id', kwargs.get('doc_id', '')),
            title=metadata.get('title', ''),
            content=self.clean_text(content),
            doc_type='sop',
            metadata={
                **metadata,
                'steps': steps,
                'category': metadata.get('category', 'general'),
                'tags': self._parse_tags(metadata.get('tags', '')),
            },
        )

    def _extract_steps(self, content: str) -> list:
        """提取操作步骤"""
        steps = []
        in_steps = False

        for line in content.split('\n'):
            if '## 操作步骤' in line or '## 步骤' in line:
                in_steps = True
                continue
            if in_steps and line.startswith('## '):
                in_steps = False
            if in_steps and line.strip():
                # 匹配步骤格式: "1. xxx" 或 "- xxx"
                match = re.match(r'^(\d+\.|-)\s*(.+)', line)
                if match:
                    steps.append(match.group(2).strip())

        return steps

    def _parse_tags(self, tags_str: str) -> list:
        """解析标签"""
        if not tags_str:
            return []
        # 移除方括号
        tags_str = tags_str.strip('[]')
        return [t.strip() for t in tags_str.split(',') if t.strip()]
