"""
重排序模块
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import asyncio


@dataclass
class RerankResult:
    """重排序结果"""
    doc_id: str
    content: str
    score: float
    original_score: float
    metadata: Dict[str, Any]


class Reranker:
    """重排序器基类"""

    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> List[RerankResult]:
        raise NotImplementedError


class LLMReranker(Reranker):
    """基于 LLM 的重排序器"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> List[RerankResult]:
        """使用 LLM 对文档进行重排序"""
        if not documents:
            return []

        results = []

        # 批量评分
        for doc in documents[:20]:  # 限制处理数量
            score = await self._score_document(query, doc)
            results.append(RerankResult(
                doc_id=doc.get("doc_id", ""),
                content=doc.get("content", ""),
                score=score,
                original_score=doc.get("score", 0),
                metadata=doc.get("metadata", {}),
            ))

        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:top_k]

    async def _score_document(
        self,
        query: str,
        document: Dict,
    ) -> float:
        """使用 LLM 对单个文档评分"""
        if not self.llm_client:
            # 回退到原始分数
            return document.get("score", 0.5)

        content = document.get("content", "")[:500]

        prompt = f"""评估以下文档与查询的相关性。

查询: {query}

文档内容:
{content}

请输出一个 0-1 之间的相关性分数:
- 1.0: 完全相关，直接回答查询
- 0.7-0.9: 高度相关，包含关键信息
- 0.4-0.6: 部分相关，有间接信息
- 0.1-0.3: 弱相关
- 0.0: 不相关

只输出分数数值，不要其他内容。"""

        try:
            response = await self._llm_call(prompt)
            return float(response.strip())
        except Exception:
            return document.get("score", 0.5)

    async def _llm_call(self, prompt: str) -> str:
        # TODO: 实现
        return "0.5"


class CrossEncoderReranker(Reranker):
    """基于 Cross-Encoder 的重排序器"""

    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name)
            except ImportError:
                raise ImportError("请安装 sentence-transformers")

    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> List[RerankResult]:
        """使用 Cross-Encoder 重排序"""
        self._load_model()

        if not documents:
            return []

        # 构建输入对
        pairs = [
            (query, doc.get("content", ""))
            for doc in documents
        ]

        # 计算分数
        scores = self._model.predict(pairs)

        # 构建结果
        results = []
        for doc, score in zip(documents, scores):
            results.append(RerankResult(
                doc_id=doc.get("doc_id", ""),
                content=doc.get("content", ""),
                score=float(score),
                original_score=doc.get("score", 0),
                metadata=doc.get("metadata", {}),
            ))

        # 排序
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:top_k]


class MultiFactorReranker(Reranker):
    """多因素重排序器"""

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.weights = weights or {
            "relevance": 0.5,
            "recency": 0.2,
            "popularity": 0.15,
            "quality": 0.15,
        }

    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> List[RerankResult]:
        """多因素综合评分"""
        results = []

        for doc in documents:
            # 计算各因素分数
            relevance = doc.get("score", 0.5)
            recency = self._compute_recency_score(doc)
            popularity = self._compute_popularity_score(doc)
            quality = self._compute_quality_score(doc)

            # 加权综合
            final_score = (
                self.weights["relevance"] * relevance +
                self.weights["recency"] * recency +
                self.weights["popularity"] * popularity +
                self.weights["quality"] * quality
            )

            results.append(RerankResult(
                doc_id=doc.get("doc_id", ""),
                content=doc.get("content", ""),
                score=final_score,
                original_score=relevance,
                metadata={
                    **doc.get("metadata", {}),
                    "scores": {
                        "relevance": relevance,
                        "recency": recency,
                        "popularity": popularity,
                        "quality": quality,
                    },
                },
            ))

        results.sort(key=lambda x: x.score, reverse=True)

        return results[:top_k]

    def _compute_recency_score(self, doc: Dict) -> float:
        """计算时效性分数"""
        from datetime import datetime

        timestamp = doc.get("timestamp") or doc.get("created_at")
        if not timestamp:
            return 0.5

        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            else:
                dt = timestamp

            age_days = (datetime.now(dt.tzinfo) - dt).days

            # 30 天内得 1.0，之后线性衰减
            if age_days <= 30:
                return 1.0
            elif age_days <= 365:
                return 1.0 - (age_days - 30) / 335
            else:
                return 0.1

        except Exception:
            return 0.5

    def _compute_popularity_score(self, doc: Dict) -> float:
        """计算流行度分数"""
        # 基于引用次数、访问次数等
        views = doc.get("views", 0)
        citations = doc.get("citations", 0)

        # 简单归一化
        return min(1.0, (views + citations * 10) / 1000)

    def _compute_quality_score(self, doc: Dict) -> float:
        """计算质量分数"""
        # 基于文档长度、格式化程度等
        content = doc.get("content", "")

        if not content:
            return 0.0

        score = 0.5

        # 文档长度适中
        if 500 <= len(content) <= 5000:
            score += 0.2

        # 有结构化内容
        if any(marker in content for marker in ["##", "1.", "- ", "|"]):
            score += 0.15

        # 有代码块
        if "```" in content:
            score += 0.15

        return min(1.0, score)
