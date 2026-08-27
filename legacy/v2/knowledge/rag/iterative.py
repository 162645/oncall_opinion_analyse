"""
迭代检索 RAG
实现多轮检索、子问题生成、重排序
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import asyncio


@dataclass
class RetrievalContext:
    """检索上下文"""
    query: str
    sub_queries: List[str] = field(default_factory=list)
    documents: List[Dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    is_sufficient: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SubQuestion:
    """子问题"""
    question: str
    answer: Optional[str] = None
    source_docs: List[Dict] = field(default_factory=list)


class IterativeRetriever:
    """
    迭代检索器

    实现 Agentic RAG 的核心逻辑:
    1. 多轮迭代检索
    2. 自动生成子问题
    3. 判断检索是否充分
    """

    def __init__(
        self,
        vector_retriever=None,
        keyword_retriever=None,
        llm_client=None,
        max_iterations: int = 3,
        min_relevance_score: float = 0.6,
    ):
        self.vector_retriever = vector_retriever
        self.keyword_retriever = keyword_retriever
        self.llm_client = llm_client
        self.max_iterations = max_iterations
        self.min_relevance_score = min_relevance_score

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> Tuple[List[Dict[str, Any]], RetrievalContext]:
        """
        执行迭代检索

        Args:
            query: 用户查询
            top_k: 每轮检索数量

        Returns:
            (检索结果, 检索上下文)
        """
        context = RetrievalContext(query=query)

        for iteration in range(self.max_iterations):
            context.iterations = iteration + 1

            # 1. 生成搜索查询
            search_query = await self._generate_search_query(context)

            # 2. 执行检索
            docs = await self._search(search_query, top_k)
            context.documents.extend(docs)

            # 3. 评估是否充分
            is_sufficient, confidence = await self._evaluate_sufficiency(
                query, context.documents
            )
            context.is_sufficient = is_sufficient
            context.metadata["confidence"] = confidence

            if is_sufficient:
                break

            # 4. 生成子问题
            sub_questions = await self._generate_sub_questions(query, docs)
            context.sub_queries.extend([sq.question for sq in sub_questions])

            # 5. 对每个子问题进行检索
            for sq in sub_questions:
                sq_docs = await self._search(sq.question, top_k // 2)
                sq.source_docs = sq_docs
                context.documents.extend(sq_docs)

        # 6. 去重和排序
        unique_docs = self._deduplicate(context.documents)
        ranked_docs = await self._rerank(query, unique_docs)

        return ranked_docs[:top_k * 2], context

    async def _generate_search_query(
        self,
        context: RetrievalContext,
    ) -> str:
        """生成搜索查询"""
        if context.iterations == 1:
            return context.query

        # 基于已有文档和原始查询生成优化查询
        if self.llm_client:
            prompt = f"""基于以下信息生成一个优化的搜索查询:

原始问题: {context.query}

已检索到的信息:
{self._format_docs(context.documents[-3:])}

请生成一个更精确的搜索查询，帮助找到缺失的信息。
只输出查询，不要其他内容。"""
            return await self._llm_call(prompt)

        return context.query

    async def _search(
        self,
        query: str,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """执行混合检索"""
        docs = []

        # 向量检索
        if self.vector_retriever:
            vector_docs = await self.vector_retriever.search(query, top_k)
            docs.extend(vector_docs)

        # 关键词检索
        if self.keyword_retriever:
            keyword_docs = await self.keyword_retriever.search(query, top_k)
            docs.extend(keyword_docs)

        return docs

    async def _evaluate_sufficiency(
        self,
        query: str,
        documents: List[Dict],
    ) -> Tuple[bool, float]:
        """
        评估检索结果是否充分

        Returns:
            (是否充分, 置信度)
        """
        if not documents:
            return False, 0.0

        if self.llm_client:
            prompt = f"""评估以下检索结果是否能充分回答用户问题。

用户问题: {query}

检索到的文档数量: {len(documents)}

请输出:
1. 是否充分 (yes/no)
2. 置信度 (0-1)

格式: yes/no, 0.XX"""
            response = await self._llm_call(prompt)
            try:
                parts = response.strip().split(",")
                is_sufficient = parts[0].strip().lower() == "yes"
                confidence = float(parts[1].strip())
                return is_sufficient, confidence
            except Exception:
                pass

        # 基于文档数量的简单评估
        confidence = min(1.0, len(documents) / 10)
        return confidence >= self.min_relevance_score, confidence

    async def _generate_sub_questions(
        self,
        query: str,
        documents: List[Dict],
    ) -> List[SubQuestion]:
        """生成子问题"""
        if not self.llm_client:
            return []

        prompt = f"""基于用户问题和已检索信息，生成 2-3 个子问题来获取更多相关信息。

用户问题: {query}

已检索信息摘要:
{self._format_docs(documents[:3])}

请输出子问题，每行一个。"""

        response = await self._llm_call(prompt)
        questions = [
            line.strip()
            for line in response.strip().split("\n")
            if line.strip()
        ][:3]

        return [SubQuestion(question=q) for q in questions]

    async def _rerank(
        self,
        query: str,
        documents: List[Dict],
    ) -> List[Dict]:
        """重排序"""
        if not documents:
            return []

        if self.llm_client:
            # 使用 LLM 进行重排序评分
            for doc in documents:
                score = await self._compute_relevance(query, doc)
                doc["_rerank_score"] = score

            documents.sort(key=lambda x: x.get("_rerank_score", 0), reverse=True)
        else:
            # 简单基于原始分数排序
            documents.sort(
                key=lambda x: x.get("score", 0),
                reverse=True
            )

        return documents

    async def _compute_relevance(
        self,
        query: str,
        document: Dict,
    ) -> float:
        """计算相关性分数"""
        if self.llm_client:
            content = document.get("content", "")[:500]
            prompt = f"""评估文档与查询的相关性，输出 0-1 的分数。

查询: {query}

文档: {content}

只输出分数，不要其他内容。"""
            try:
                response = await self._llm_call(prompt)
                return float(response.strip())
            except Exception:
                pass

        return document.get("score", 0.5)

    def _deduplicate(
        self,
        documents: List[Dict],
    ) -> List[Dict]:
        """去重"""
        seen = set()
        unique = []

        for doc in documents:
            doc_id = doc.get("doc_id", doc.get("id", str(hash(doc.get("content", "")))))
            if doc_id not in seen:
                seen.add(doc_id)
                unique.append(doc)

        return unique

    def _format_docs(self, documents: List[Dict]) -> str:
        """格式化文档"""
        formatted = []
        for i, doc in enumerate(documents, 1):
            content = doc.get("content", "")[:200]
            formatted.append(f"{i}. {content}")
        return "\n".join(formatted)

    async def _llm_call(self, prompt: str) -> str:
        """调用 LLM"""
        if self.llm_client:
            # TODO: 实际 LLM 调用
            return ""
        return ""


class QueryRewriter:
    """查询重写器"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def rewrite(
        self,
        query: str,
        context: Optional[str] = None,
    ) -> str:
        """
        重写查询以提高检索效果

        - 扩展缩写
        - 添加同义词
        - 补充上下文
        """
        if not self.llm_client:
            return query

        prompt = f"""重写以下查询以提高检索效果。
保持原意，但可以:
1. 扩展缩写 (如 SLA -> Service Level Agreement)
2. 添加同义词
3. 补充必要的上下文

原查询: {query}
{"上下文: " + context if context else ""}

只输出重写后的查询，不要其他内容。"""

        return await self._llm_call(prompt)

    async def _llm_call(self, prompt: str) -> str:
        # TODO: 实现
        return ""
