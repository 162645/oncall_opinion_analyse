"""
知识库服务
整合文档解析、向量检索、关键词检索、融合检索
"""

import os
import uuid
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import asyncio
from concurrent.futures import ThreadPoolExecutor
from src.observability import get_telemetry

from src.knowledge import (
    KnowledgeDocument,
    DocumentChunk,
    DocumentType,
    DocumentStatus,
    ParserFactory,
    VectorIndex,
    KeywordIndex,
    FusionRetriever,
    IndexResult,
    KnowledgeGraph,
    GraphBuilder,
)


@dataclass
class SearchContext:
    """搜索上下文"""
    query: str
    results: List[IndexResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class KnowledgeService:
    """
    知识库服务

    功能:
    - 文档上传和解析
    - 向量索引构建
    - 混合检索 (向量 + 关键词)
    - 知识图谱构建
    """

    def __init__(
        self,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "",
    ):
        # 索引组件
        self.vector_index = VectorIndex(
            host=qdrant_host,
            port=qdrant_port,
            collection="oncall_knowledge",
        )
        self.keyword_index = KeywordIndex()

        # 融合检索器
        self.fusion_retriever = FusionRetriever(
            vector_index=self.vector_index,
            keyword_index=self.keyword_index,
        )

        # 知识图谱 (可选)
        self.graph: Optional[KnowledgeGraph] = None
        if neo4j_uri:
            try:
                self.graph = KnowledgeGraph(
                    uri=neo4j_uri,
                    user=neo4j_user,
                    password=neo4j_password,
                )
            except Exception:
                pass

        # 文档存储 (内存，生产环境用数据库)
        self._documents: Dict[str, KnowledgeDocument] = {}
        self._chunks: Dict[str, List[DocumentChunk]] = {}

        # 解析器工厂
        self.parser_factory = ParserFactory()

        # 初始化 BM25 索引
        self._init_keyword_index()

    def _init_keyword_index(self):
        """初始化关键词索引"""
        # 从现有文档构建索引
        documents = []
        for doc_id, chunks in self._chunks.items():
            for chunk in chunks:
                documents.append({
                    "doc_id": doc_id,
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                })

        if documents:
            self.keyword_index.build_index(documents)

    # ===== 文档管理 =====

    async def upload_document(
        self,
        file_content: bytes,
        file_name: str,
        title: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> KnowledgeDocument:
        """
        上传文档

        Args:
            file_content: 文件内容
            file_name: 文件名
            title: 文档标题
            metadata: 元数据

        Returns:
            KnowledgeDocument
        """
        # 生成文档ID
        doc_id = str(uuid.uuid4())
        file_hash = hashlib.md5(file_content).hexdigest()

        # 判断文档类型
        ext = file_name.split(".")[-1].lower() if "." in file_name else "txt"
        doc_type = self._get_doc_type(ext)

        # 创建文档对象
        document = KnowledgeDocument(
            id=doc_id,
            title=title or file_name,
            content="",  # 解析后填充
            doc_type=doc_type,
            file_path=f"/tmp/{doc_id}.{ext}",
            file_name=file_name,
            file_size=len(file_content),
            file_hash=file_hash,
            status=DocumentStatus.PROCESSING,
            metadata=metadata or {},
        )

        # 保存到内存
        self._documents[doc_id] = document

        # 同步处理文档（简单快速，不阻塞事件循环太久）
        try:
            # 直接解析内容（不写临时文件）
            try:
                text = file_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text = file_content.decode('gbk')
                except:
                    text = file_content.decode('utf-8', errors='ignore')

            # 提取标题
            import re
            title_match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
            if title_match:
                document.title = title_match.group(1)

            document.content = text
            document.metadata["line_count"] = len(text.split('\n'))
            document.metadata["word_count"] = len(text)

            # 分块
            chunks = self._chunk_document(document)
            self._chunks[doc_id] = chunks
            document.chunks = chunks
            document.status = DocumentStatus.READY

        except Exception as e:
            document.status = DocumentStatus.FAILED
            document.metadata["error"] = str(e)

        return document

    async def _process_document(
        self,
        document: KnowledgeDocument,
        content: bytes,
    ):
        """处理文档：解析、分块、索引"""
        import tempfile

        try:
            # 更新状态
            document.status = DocumentStatus.PROCESSING

            # 将内容保存到临时文件
            ext = document.file_name.split(".")[-1].lower() if "." in document.file_name else "txt"
            with tempfile.NamedTemporaryFile(mode='wb', suffix=f'.{ext}', delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            # 同步解析（直接调用，不使用线程池避免事件循环问题）
            parsed = self.parser_factory.parse_sync(tmp_path, document.doc_type.value)

            # 删除临时文件
            try:
                os.unlink(tmp_path)
            except:
                pass

            if not parsed.success:
                document.status = DocumentStatus.FAILED
                document.metadata["error"] = parsed.error or "Parse failed"
                return

            document.content = parsed.content
            if parsed.title:
                document.title = parsed.title
            document.metadata.update(parsed.metadata)

            # 分块
            chunks = self._chunk_document(document)
            self._chunks[document.id] = chunks
            document.chunks = chunks
            document.status = DocumentStatus.READY

            # 更新关键词索引
            self._update_keyword_index(document.id, chunks)

        except Exception as e:
            document.status = DocumentStatus.FAILED
            document.metadata["error"] = str(e)

    def _sync_parse(self, file_path: str, doc_type: str):
        """同步解析文档（在线程池中运行）"""
        return self.parser_factory.parse_sync(file_path, doc_type)

    def _chunk_document(
        self,
        document: KnowledgeDocument,
        chunk_size: int = 500,
        overlap: int = 50,
    ) -> List[DocumentChunk]:
        """文档分块"""
        chunks = []
        content = document.content
        total_len = len(content)

        if total_len == 0:
            return chunks

        start = 0
        chunk_idx = 0

        while start < total_len:
            end = min(start + chunk_size, total_len)
            chunk_content = content[start:end]

            chunk = DocumentChunk(
                chunk_id=f"{document.id}-{chunk_idx}",
                doc_id=document.id,
                content=chunk_content,
                position=chunk_idx,
                metadata={
                    "doc_title": document.title,
                    "doc_type": document.doc_type.value,
                    "start": start,
                    "end": end,
                },
            )

            chunks.append(chunk)
            chunk_idx += 1

            # 移动到下一个位置（确保至少前进 chunk_size - overlap）
            next_start = end - overlap
            if next_start <= start:
                # 避免无限循环：如果计算的位置没有前进，直接移动到 end
                start = end
            else:
                start = next_start

            if start >= total_len:
                break

        return chunks

    def _update_keyword_index(
        self,
        doc_id: str,
        chunks: List[DocumentChunk],
    ):
        """更新关键词索引"""
        documents = [
            {
                "doc_id": chunk.doc_id,
                "content": chunk.content,
                "metadata": chunk.metadata,
            }
            for chunk in chunks
        ]

        # 合并现有文档
        existing = []
        for existing_doc_id, existing_chunks in self._chunks.items():
            if existing_doc_id != doc_id:
                for chunk in existing_chunks:
                    existing.append({
                        "doc_id": chunk.doc_id,
                        "content": chunk.content,
                        "metadata": chunk.metadata,
                    })

        self.keyword_index.build_index(existing + documents)

    def _get_doc_type(self, ext: str) -> DocumentType:
        """根据扩展名获取文档类型"""
        type_map = {
            "pdf": DocumentType.PDF,
            "doc": DocumentType.WORD,
            "docx": DocumentType.WORD,
            "md": DocumentType.MARKDOWN,
            "markdown": DocumentType.MARKDOWN,
            "txt": DocumentType.TEXT,
            "json": DocumentType.JSON,
            "csv": DocumentType.CSV,
        }
        return type_map.get(ext, DocumentType.TEXT)

    # ===== 检索功能 =====

    async def search(
        self,
        query: str,
        top_k: int = 10,
        use_vector: bool = True,
        use_keyword: bool = True,
    ) -> SearchContext:
        """
        知识检索

        Args:
            query: 查询文本
            top_k: 返回数量
            use_vector: 是否使用向量检索
            use_keyword: 是否使用关键词检索

        Returns:
            SearchContext
        """
        context = SearchContext(query=query)
        span = get_telemetry().tracer.start_span("rag.retrieve", attributes={
            "rag.top_k": top_k,
            "rag.vector.enabled": use_vector,
            "rag.keyword.enabled": use_keyword,
        })
        results = []

        # 向量检索 (如果可用)
        if use_vector:
            try:
                query_vector = self._local_embedding_fallback(query)
                vector_results = await self.vector_index.search(
                    query_vector=query_vector,
                    top_k=top_k * 2,
                )
                results.extend(vector_results)
            except Exception:
                # 向量检索不可用，跳过
                pass

        # 关键词检索
        if use_keyword:
            try:
                keyword_results = await self.keyword_index.search(
                    query=query,
                    top_k=top_k * 2,
                )
                results.extend(keyword_results)
            except Exception:
                pass

        # 融合排序或回退搜索
        if results:
            try:
                fused = self.fusion_retriever._rrf_fusion(results)
                context.results = fused[:top_k]
            except Exception:
                context.results = results[:top_k]
        else:
            # 回退到简单的内存搜索
            context.results = self._fallback_search(query, top_k)

        context.metadata = {
            "total": len(context.results),
            "query": query,
            "methods": {
                "vector": use_vector,
                "keyword": use_keyword,
            },
        }

        span.set_attribute("rag.results.count", len(context.results))
        span.end()
        return context

    def _local_embedding_fallback(self, text: str) -> List[float]:
        """Deterministic local embedding fallback used when no model is configured."""
        import hashlib

        # 基于文本生成固定向量
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()

        # 生成 768 维向量
        vector = []
        for i in range(768):
            byte_idx = i % len(hash_bytes)
            vector.append((hash_bytes[byte_idx] - 128) / 128.0)

        return vector

    def _fallback_search(
        self,
        query: str,
        top_k: int,
    ) -> List[IndexResult]:
        """回退搜索：简单的内存搜索"""
        results = []
        query_lower = query.lower()

        for doc_id, chunks in self._chunks.items():
            for chunk in chunks:
                if query_lower in chunk.content.lower():
                    results.append(IndexResult(
                        doc_id=doc_id,
                        content=chunk.content[:300],
                        score=0.8,
                        source="fallback",
                        metadata=chunk.metadata,
                    ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    # ===== 文档管理 =====

    def get_document(self, doc_id: str) -> Optional[KnowledgeDocument]:
        """获取文档"""
        return self._documents.get(doc_id)

    def list_documents(
        self,
        page: int = 1,
        page_size: int = 20,
        doc_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """列出文档"""
        docs = list(self._documents.values())

        # 筛选
        if doc_type:
            docs = [d for d in docs if d.doc_type.value == doc_type]

        if status:
            docs = [d for d in docs if d.status.value == status]

        # 排序
        docs.sort(key=lambda x: x.updated_at, reverse=True)

        # 分页
        total = len(docs)
        start = (page - 1) * page_size
        end = start + page_size

        return {
            "total": total,
            "documents": docs[start:end],
            "page": page,
            "page_size": page_size,
        }

    async def delete_document_async(self, doc_id: str) -> bool:
        """
        异步删除文档

        完整删除流程：
        1. 删除向量数据库中的向量
        2. 从关键词索引中移除
        3. 删除内存中的文档和分块
        """
        if doc_id not in self._documents:
            return False

        # 1. 删除向量数据库中的向量
        try:
            await self.vector_index.delete_by_doc_id(doc_id)
        except Exception as e:
            # 向量删除失败不影响整体流程
            print(f"Warning: 删除向量失败: {e}")

        # 2. 从关键词索引中移除
        try:
            self.keyword_index.remove_document(doc_id)
        except Exception as e:
            print(f"Warning: 更新关键词索引失败: {e}")

        # 3. 删除知识图谱中的节点（如果有）
        if self.graph:
            try:
                self.graph.delete_document_nodes(doc_id)
            except Exception:
                pass

        # 4. 删除内存数据
        del self._documents[doc_id]
        if doc_id in self._chunks:
            del self._chunks[doc_id]

        return True

    def delete_document(self, doc_id: str) -> bool:
        """删除文档（同步版本）"""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果在 async 上下文中，创建新任务
                asyncio.create_task(self.delete_document_async(doc_id))
            else:
                loop.run_until_complete(self.delete_document_async(doc_id))
        except RuntimeError:
            # 没有事件循环，创建新的
            asyncio.run(self.delete_document_async(doc_id))

        # 同步删除内存数据（确保立即生效）
        if doc_id in self._documents:
            del self._documents[doc_id]
        if doc_id in self._chunks:
            del self._chunks[doc_id]

        return True

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        docs = list(self._documents.values())

        by_type = {}
        by_status = {}
        total_size = 0
        total_chunks = 0

        for doc in docs:
            doc_type = doc.doc_type.value
            by_type[doc_type] = by_type.get(doc_type, 0) + 1

            status = doc.status.value
            by_status[status] = by_status.get(status, 0) + 1

            total_size += doc.file_size
            total_chunks += len(doc.chunks)

        return {
            "total_documents": len(docs),
            "total_chunks": total_chunks,
            "total_size": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "by_type": by_type,
            "by_status": by_status,
        }


# 全局服务实例
_knowledge_service: Optional[KnowledgeService] = None


def get_knowledge_service() -> KnowledgeService:
    """获取知识库服务实例"""
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
    return _knowledge_service
