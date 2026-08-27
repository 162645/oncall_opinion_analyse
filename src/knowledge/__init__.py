"""
知识模块
实现文档解析、存储和检索
"""

from .models import (
    KnowledgeDocument,
    DocumentChunk,
    DocumentType,
    DocumentStatus,
    KnowledgeStats,
    SearchResult,
    get_doc_type_from_extension,
    get_mime_type,
)
from .parser import (
    ParserFactory,
    BaseParser,
    ParseResult,
    PDFParser,
    WordParser,
    MarkdownParser,
    TextParser,
)

# 索引和检索
from .index.fusion import (
    VectorIndex,
    KeywordIndex,
    FusionRetriever,
    IndexResult,
)

# RAG 模块
from .rag.iterative import (
    IterativeRetriever,
    QueryRewriter,
    RetrievalContext,
    SubQuestion,
)
from .rag.reranker import Reranker

# 知识图谱
from .graph.builder import (
    KnowledgeGraph,
    GraphBuilder,
    GraphNode,
    GraphEdge,
    NodeType,
    RelationType,
)

# 服务
from .service import get_knowledge_service, KnowledgeService

__all__ = [
    # 数据模型
    "KnowledgeDocument",
    "DocumentChunk",
    "DocumentType",
    "DocumentStatus",
    "KnowledgeStats",
    "SearchResult",
    "get_doc_type_from_extension",
    "get_mime_type",
    # 解析器
    "ParserFactory",
    "BaseParser",
    "ParseResult",
    "PDFParser",
    "WordParser",
    "MarkdownParser",
    "TextParser",
    # 索引和检索
    "VectorIndex",
    "KeywordIndex",
    "FusionRetriever",
    "IndexResult",
    # RAG 模块
    "IterativeRetriever",
    "QueryRewriter",
    "RetrievalContext",
    "SubQuestion",
    "Reranker",
    # 知识图谱
    "KnowledgeGraph",
    "GraphBuilder",
    "GraphNode",
    "GraphEdge",
    "NodeType",
    "RelationType",
    # 服务
    "get_knowledge_service",
    "KnowledgeService",
]
