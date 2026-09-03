"""
LlamaIndex 知识服务
集成高级 RAG 功能
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """检索结果"""
    content: str
    score: float
    metadata: Dict[str, Any]
    source: str  # vector, keyword, hybrid


class LlamaIndexKnowledgeService:
    """
    LlamaIndex 知识服务

    特性:
    1. 混合检索 (向量 + 关键词)
    2. 查询优化和重写
    3. 自动重排序
    4. 智能分块

    注意: 需要安装 llama-index 相关包才能使用完整功能
    """

    def __init__(
        self,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        collection_name: str = "oncall_knowledge_v2",
        embed_model: str = "BAAI/bge-m3",
    ):
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.collection_name = collection_name
        self.embed_model_name = embed_model

        # 延迟初始化
        self._index = None
        self._embed_model = None
        self._llama_available = self._check_llama_index()

    def _check_llama_index(self) -> bool:
        """检查 LlamaIndex 是否可用"""
        try:
            import llama_index
            return True
        except ImportError:
            logger.warning(
                "LlamaIndex not installed. "
                "Install with: pip install llama-index llama-index-vector-stores-qdrant"
            )
            return False

    def _init_index(self):
        """初始化索引"""
        if not self._llama_available:
            return None

        try:
            from llama_index.core import VectorStoreIndex, Settings
            from llama_index.vector_stores.qdrant import QdrantVectorStore
            from qdrant_client import QdrantClient

            # 配置 Embedding
            self._init_embed_model()

            # 初始化向量存储
            client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
            vector_store = QdrantVectorStore(
                client=client,
                collection_name=self.collection_name,
            )

            # 创建索引
            self._index = VectorStoreIndex.from_vector_store(vector_store)
            return self._index

        except Exception as e:
            logger.error(f"Failed to initialize LlamaIndex: {e}")
            return None

    def _init_embed_model(self):
        """初始化 Embedding 模型"""
        if self._embed_model is not None:
            return

        try:
            from llama_index.core import Settings
            from llama_index.embeddings.flag_embedding import FlagEmbeddingModel

            self._embed_model = FlagEmbeddingModel(
                model_name=self.embed_model_name,
            )
            Settings.embed_model = self._embed_model

        except ImportError:
            # 使用 OpenAI embedding 作为备选
            try:
                from llama_index.embeddings.openai import OpenAIEmbedding
                from llama_index.core import Settings

                self._embed_model = OpenAIEmbedding()
                Settings.embed_model = self._embed_model
            except Exception as e:
                logger.warning(f"Failed to init embed model: {e}")

    async def ingest_documents(
        self,
        file_paths: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        导入文档

        Args:
            file_paths: 文件路径列表
            metadata: 元数据

        Returns:
            导入的文档数量
        """
        if not self._llama_available:
            logger.warning("LlamaIndex not available, skipping document ingestion")
            return 0

        try:
            from llama_index.core import SimpleDirectoryReader, Settings
            from llama_index.core.node_parser import SentenceSplitter

            # 配置分块器
            Settings.node_parser = SentenceSplitter(
                chunk_size=512,
                chunk_overlap=50,
            )

            # 读取文档
            documents = SimpleDirectoryReader(
                input_files=file_paths,
            ).load_data()

            # 添加元数据
            if metadata:
                for doc in documents:
                    doc.metadata.update(metadata)

            # 解析节点
            nodes = Settings.node_parser.get_nodes_from_documents(documents)

            # 添加到索引
            if self._index is None:
                self._init_index()

            if self._index:
                self._index.insert_nodes(nodes)
                logger.info(f"Ingested {len(nodes)} nodes from {len(file_paths)} files")
                return len(documents)

        except Exception as e:
            logger.error(f"Document ingestion failed: {e}")

        return 0

    async def query(
        self,
        query_text: str,
        mode: str = "hybrid",
        top_k: int = 5,
        use_reranker: bool = False,
    ) -> List[RetrievalResult]:
        """
        知识检索

        Args:
            query_text: 查询文本
            mode: 检索模式 (vector, keyword, hybrid)
            top_k: 返回数量
            use_reranker: 是否使用重排序

        Returns:
            List[RetrievalResult]
        """
        if not self._llama_available:
            return await self._fallback_query(query_text, top_k)

        try:
            from llama_index.core import Settings

            # 初始化索引
            if self._index is None:
                self._index = self._init_index()

            if self._index is None:
                return await self._fallback_query(query_text, top_k)

            # 配置检索器
            if mode == "hybrid":
                from .hybrid_retriever import HybridRetriever
                retriever = HybridRetriever(self._index, top_k=top_k)
            else:
                retriever = self._index.as_retriever(similarity_top_k=top_k)

            # 执行检索
            nodes = retriever.retrieve(query_text)

            # 重排序
            if use_reranker:
                nodes = await self._rerank(query_text, nodes, top_k)

            # 转换结果
            results = []
            for node in nodes[:top_k]:
                results.append(RetrievalResult(
                    content=node.node.text,
                    score=node.score,
                    metadata=node.node.metadata,
                    source=mode,
                ))

            return results

        except Exception as e:
            logger.error(f"Query failed: {e}")
            return await self._fallback_query(query_text, top_k)

    async def _rerank(
        self,
        query: str,
        nodes: list,
        top_k: int,
    ) -> list:
        """重排序"""
        try:
            from llama_index.postprocessor.cohere_rerank import CohereRerank

            reranker = CohereRerank(top_n=top_k)
            return reranker.postprocess_nodes(nodes, query_str=query)

        except ImportError:
            # Cohere 不可用，返回原结果
            return nodes

    async def _fallback_query(
        self,
        query: str,
        top_k: int,
    ) -> List[RetrievalResult]:
        """回退查询"""
        # 使用现有的 KnowledgeService
        from src.knowledge.service import get_knowledge_service

        service = get_knowledge_service()
        result = await service.search(query, top_k=top_k)

        return [
            RetrievalResult(
                content=r.content,
                score=r.score,
                metadata=r.metadata,
                source=r.source,
            )
            for r in result.results
        ]

    async def optimize_query(self, query: str) -> str:
        """优化查询"""
        from .query_optimizer import QueryOptimizer

        optimizer = QueryOptimizer()
        return await optimizer.optimize(query)


# 全局实例
_service: Optional[LlamaIndexKnowledgeService] = None


def get_llama_index_service() -> LlamaIndexKnowledgeService:
    """获取 LlamaIndex 服务实例"""
    global _service
    if _service is None:
        _service = LlamaIndexKnowledgeService()
    return _service
