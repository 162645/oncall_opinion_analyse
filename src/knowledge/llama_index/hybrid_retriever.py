"""
混合检索器
结合向量检索和关键词检索
"""

from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    混合检索器

    结合向量检索和关键词检索的优势:
    - 向量检索: 语义相似性，发现隐含关联
    - 关键词检索: 精确匹配，保证关键信息不遗漏
    """

    def __init__(
        self,
        index: Any = None,
        top_k: int = 10,
        vector_weight: float = 0.6,
        keyword_weight: float = 0.4,
    ):
        self.index = index
        self.top_k = top_k
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

    def retrieve(self, query: str) -> List[Any]:
        """
        执行混合检索

        Args:
            query: 查询文本

        Returns:
            检索结果列表
        """
        # 尝试使用 LlamaIndex 混合检索
        try:
            return self._llama_hybrid_retrieve(query)
        except Exception:
            # 回退到基础检索
            return self._basic_retrieve(query)

    def _llama_hybrid_retrieve(self, query: str) -> List[Any]:
        """LlamaIndex 混合检索"""
        if self.index is None:
            return []

        # 向量检索
        vector_retriever = self.index.as_retriever(
            similarity_top_k=self.top_k * 2,
        )
        vector_nodes = vector_retriever.retrieve(query)

        # 关键词检索 (如果可用)
        try:
            from llama_index.retrievers.bm25 import BM25Retriever

            keyword_retriever = BM25Retriever.from_defaults(
                docstore=self.index.docstore,
                similarity_top_k=self.top_k * 2,
            )
            keyword_nodes = keyword_retriever.retrieve(query)

            # 融合结果
            return self._fusion(vector_nodes, keyword_nodes)

        except ImportError:
            # BM25 不可用，只使用向量检索
            return vector_nodes[:self.top_k]

    def _basic_retrieve(self, query: str) -> List[Any]:
        """基础检索"""
        if self.index is None:
            return []

        retriever = self.index.as_retriever(similarity_top_k=self.top_k)
        return retriever.retrieve(query)

    def _fusion(
        self,
        vector_nodes: List[Any],
        keyword_nodes: List[Any],
    ) -> List[Any]:
        """
        融合检索结果

        使用 Reciprocal Rank Fusion (RRF) 算法
        """
        # 计算分数
        scores: Dict[str, float] = {}
        node_map: Dict[str, Any] = {}

        # 向量检索分数
        for i, node in enumerate(vector_nodes):
            node_id = node.node.node_id
            scores[node_id] = scores.get(node_id, 0) + self.vector_weight / (i + 60)
            node_map[node_id] = node

        # 关键词检索分数
        for i, node in enumerate(keyword_nodes):
            node_id = node.node.node_id
            scores[node_id] = scores.get(node_id, 0) + self.keyword_weight / (i + 60)
            node_map[node_id] = node

        # 按分数排序
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        # 返回排序后的节点
        results = []
        for node_id in sorted_ids[:self.top_k]:
            node = node_map[node_id]
            # 更新分数
            node.score = scores[node_id]
            results.append(node)

        return results
