"""
多级索引模块
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import hashlib


@dataclass
class IndexResult:
    """索引检索结果"""
    doc_id: str
    content: str
    score: float
    source: str  # vector / keyword / graph
    metadata: Dict[str, Any]


class VectorIndex:
    """向量索引"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection: str = "oncall_knowledge",
    ):
        self.host = host
        self.port = port
        self.collection = collection
        self._client = None
        self._point_ids: Dict[str, List[str]] = {}  # doc_id -> list of point_ids

    def _connect(self):
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
                self._client = QdrantClient(host=self.host, port=self.port)
            except ImportError:
                raise ImportError("请安装 qdrant-client")

    async def upsert(
        self,
        doc_id: str,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
    ) -> bool:
        """插入或更新向量"""
        self._connect()

        try:
            from qdrant_client.http import models

            # 生成 point IDs
            point_ids = []
            points = []
            for i, (vector, payload) in enumerate(zip(vectors, payloads)):
                point_id = f"{doc_id}-{i}"
                point_ids.append(point_id)
                points.append(models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                ))

            # 记录 point IDs
            self._point_ids[doc_id] = point_ids

            # 上传到 Qdrant
            self._client.upsert(
                collection_name=self.collection,
                points=points,
            )
            return True
        except Exception as e:
            print(f"向量插入失败: {e}")
            return False

    async def delete_by_doc_id(self, doc_id: str) -> bool:
        """根据文档ID删除所有相关向量"""
        self._connect()

        try:
            from qdrant_client.http import models

            # 使用过滤器删除
            self._client.delete(
                collection_name=self.collection,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="doc_id",
                                match=models.MatchValue(value=doc_id),
                            )
                        ]
                    )
                )
            )

            # 清理本地记录
            if doc_id in self._point_ids:
                del self._point_ids[doc_id]

            return True
        except Exception as e:
            print(f"向量删除失败: {e}")
            return False

    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict] = None,
    ) -> List[IndexResult]:
        """向量相似度搜索"""
        self._connect()

        results = self._client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            limit=top_k,
            query_filter=filters,
        )

        return [
            IndexResult(
                doc_id=hit.payload.get("doc_id", ""),
                content=hit.payload.get("content", ""),
                score=hit.score,
                source="vector",
                metadata=hit.payload.get("metadata", {}),
            )
            for hit in results
        ]


class KeywordIndex:
    """关键词索引 (BM25)"""

    def __init__(self, index_path: Optional[str] = None):
        self.index_path = index_path
        self._index = None
        self._documents = {}
        self._doc_id_map: Dict[str, int] = {}  # doc_id -> internal index

    def build_index(self, documents: List[Dict[str, Any]]):
        """构建索引"""
        try:
            from rank_bm25 import BM25Okapi
            import jieba

            self._documents = {i: doc for i, doc in enumerate(documents)}
            self._doc_id_map = {}

            # 分词
            tokenized = []
            for i, doc in enumerate(documents):
                text = doc.get("content", "")
                tokens = list(jieba.cut(text))
                tokenized.append(tokens)

                # 记录 doc_id 映射
                doc_id = doc.get("doc_id", str(i))
                self._doc_id_map[doc_id] = i

            self._index = BM25Okapi(tokenized)

        except ImportError:
            # 回退到简单匹配
            self._index = None
            self._documents = {i: doc for i, doc in enumerate(documents)}
            self._doc_id_map = {}

    def remove_document(self, doc_id: str) -> bool:
        """从索引中移除文档"""
        # 简单实现：重建索引时排除该文档
        remaining_docs = [
            doc for idx, doc in self._documents.items()
            if doc.get("doc_id") != doc_id
        ]

        # 重建索引
        self.build_index(remaining_docs)
        return True

    async def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> List[IndexResult]:
        """关键词搜索"""
        if not self._index:
            # 简单关键词匹配
            return self._simple_search(query, top_k)

        try:
            import jieba
            query_tokens = list(jieba.cut(query))
            scores = self._index.get_scores(query_tokens)

            # 排序并返回 top_k
            ranked = sorted(
                enumerate(scores),
                key=lambda x: x[1],
                reverse=True,
            )[:top_k]

            return [
                IndexResult(
                    doc_id=self._documents[idx].get("doc_id", str(idx)),
                    content=self._documents[idx].get("content", ""),
                    score=float(score),
                    source="keyword",
                    metadata=self._documents[idx].get("metadata", {}),
                )
                for idx, score in ranked
                if score > 0
            ]

        except ImportError:
            return self._simple_search(query, top_k)

    def _simple_search(
        self,
        query: str,
        top_k: int,
    ) -> List[IndexResult]:
        """简单关键词匹配"""
        query_words = set(query.lower().split())
        results = []

        for idx, doc in self._documents.items():
            content = doc.get("content", "").lower()
            content_words = set(content.split())

            # Jaccard 相似度
            intersection = len(query_words & content_words)
            union = len(query_words | content_words)
            score = intersection / union if union > 0 else 0

            if score > 0:
                results.append(IndexResult(
                    doc_id=doc.get("doc_id", str(idx)),
                    content=doc.get("content", ""),
                    score=score,
                    source="keyword",
                    metadata=doc.get("metadata", {}),
                ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]


class FusionRetriever:
    """
    融合检索器

    合并向量检索和关键词检索结果
    """

    def __init__(
        self,
        vector_index: Optional[VectorIndex] = None,
        keyword_index: Optional[KeywordIndex] = None,
        vector_weight: float = 0.6,
        keyword_weight: float = 0.4,
    ):
        self.vector_index = vector_index
        self.keyword_index = keyword_index
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

    async def search(
        self,
        query: str,
        query_vector: Optional[List[float]] = None,
        top_k: int = 10,
    ) -> List[IndexResult]:
        """
        融合检索

        Args:
            query: 查询文本
            query_vector: 查询向量（可选）
            top_k: 返回数量

        Returns:
            融合后的检索结果
        """
        results = []

        # 向量检索
        if self.vector_index and query_vector:
            vector_results = await self.vector_index.search(
                query_vector=query_vector,
                top_k=top_k * 2,
            )
            for r in vector_results:
                r.score *= self.vector_weight
            results.extend(vector_results)

        # 关键词检索
        if self.keyword_index:
            keyword_results = await self.keyword_index.search(
                query=query,
                top_k=top_k * 2,
            )
            for r in keyword_results:
                r.score *= self.keyword_weight
            results.extend(keyword_results)

        # 融合排序 (RRF - Reciprocal Rank Fusion)
        fused = self._rrf_fusion(results)

        return fused[:top_k]

    def _rrf_fusion(
        self,
        results: List[IndexResult],
        k: int = 60,
    ) -> List[IndexResult]:
        """
        Reciprocal Rank Fusion

        公式: RRF(d) = Σ 1/(k + rank(d))
        """
        doc_scores = {}

        for i, result in enumerate(results):
            doc_id = result.doc_id
            rank = i + 1
            rrf_score = 1.0 / (k + rank)

            if doc_id not in doc_scores:
                doc_scores[doc_id] = {
                    "result": result,
                    "score": 0,
                }

            doc_scores[doc_id]["score"] += rrf_score

        # 排序
        sorted_results = sorted(
            doc_scores.values(),
            key=lambda x: x["score"],
            reverse=True,
        )

        return [
            IndexResult(
                doc_id=item["result"].doc_id,
                content=item["result"].content,
                score=item["score"],
                source="fusion",
                metadata=item["result"].metadata,
            )
            for item in sorted_results
        ]
