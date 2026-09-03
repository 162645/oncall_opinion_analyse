"""
向量检索模块
支持 Qdrant 向量数据库检索
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import json


@dataclass
class RetrievalResult:
    """检索结果"""
    doc_id: str
    content: str
    score: float
    metadata: Dict[str, Any]


class QdrantRetriever:
    """
    Qdrant 向量检索器

    用于从 Qdrant 向量数据库检索相似文档
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection_name: str = "oncall_knowledge",
        api_key: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        """获取 Qdrant 客户端"""
        if self._client is None:
            try:
                from qdrant_client import QdrantClient

                self._client = QdrantClient(
                    host=self.host,
                    port=self.port,
                    api_key=self.api_key,
                )
            except ImportError:
                raise ImportError(
                    "请安装 qdrant-client: pip install qdrant-client"
                )
        return self._client

    def create_collection(
        self,
        vector_size: int = 1024,
        distance: str = "Cosine",
    ) -> bool:
        """
        创建集合

        Args:
            vector_size: 向量维度
            distance: 距离度量 (Cosine/Euclidean/Dot)
        """
        from qdrant_client.http import models

        client = self._get_client()

        try:
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance[distance.upper()],
                ),
            )
            return True
        except Exception as e:
            if "already exists" in str(e).lower():
                return True
            raise

    def upsert(
        self,
        doc_id: str,
        vector: List[float],
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        插入或更新文档

        Args:
            doc_id: 文档ID
            vector: 文档向量
            content: 文档内容
            metadata: 元数据
        """
        from qdrant_client.http import models

        client = self._get_client()

        # 生成数字 ID (用于 Qdrant)
        point_id = abs(hash(doc_id)) % (10 ** 10)

        client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "doc_id": doc_id,
                        "content": content,
                        "metadata": metadata or {},
                    },
                ),
            ],
        )
        return True

    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """
        向量相似度搜索

        Args:
            query_vector: 查询向量
            limit: 返回数量限制
            score_threshold: 分数阈值
            filters: 过滤条件
        """
        from qdrant_client.http import models

        client = self._get_client()

        # 构建过滤条件
        query_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(
                    models.FieldCondition(
                        key=f"metadata.{key}",
                        match=models.MatchValue(value=value),
                    )
                )
            if conditions:
                query_filter = models.Filter(must=conditions)

        results = client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter,
        )

        return [
            RetrievalResult(
                doc_id=hit.payload.get("doc_id", ""),
                content=hit.payload.get("content", ""),
                score=hit.score,
                metadata=hit.payload.get("metadata", {}),
            )
            for hit in results
        ]

    def delete(self, doc_id: str) -> bool:
        """删除文档"""
        client = self._get_client()
        point_id = abs(hash(doc_id)) % (10 ** 10)

        client.delete(
            collection_name=self.collection_name,
            points_selector=[point_id],
        )
        return True


class HybridRetriever:
    """
    混合检索器

    结合向量检索和关键词检索
    """

    def __init__(
        self,
        vector_retriever: QdrantRetriever,
        keyword_weight: float = 0.3,
        vector_weight: float = 0.7,
    ):
        self.vector_retriever = vector_retriever
        self.keyword_weight = keyword_weight
        self.vector_weight = vector_weight

    def search(
        self,
        query_vector: List[float],
        query_text: str,
        limit: int = 10,
    ) -> List[RetrievalResult]:
        """
        混合检索

        Args:
            query_vector: 查询向量
            query_text: 查询文本（用于关键词匹配）
            limit: 返回数量限制
        """
        # 向量检索
        vector_results = self.vector_retriever.search(
            query_vector=query_vector,
            limit=limit * 2,  # 获取更多候选
        )

        # 关键词匹配评分
        query_keywords = set(query_text.lower().split())

        scored_results = []
        for result in vector_results:
            # 向量分数
            vector_score = result.score

            # 关键词分数
            content_keywords = set(result.content.lower().split())
            keyword_score = len(query_keywords & content_keywords) / max(len(query_keywords), 1)

            # 综合分数
            final_score = (
                self.vector_weight * vector_score +
                self.keyword_weight * keyword_score
            )

            scored_results.append(RetrievalResult(
                doc_id=result.doc_id,
                content=result.content,
                score=final_score,
                metadata={
                    **result.metadata,
                    "vector_score": vector_score,
                    "keyword_score": keyword_score,
                },
            ))

        # 按综合分数排序
        scored_results.sort(key=lambda x: x.score, reverse=True)

        return scored_results[:limit]
