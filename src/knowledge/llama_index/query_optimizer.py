"""
查询优化器
优化和重写用户查询
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class QueryAnalysis:
    """查询分析结果"""
    original: str
    optimized: str
    keywords: List[str]
    entities: List[str]
    intent: str
    complexity: float


class QueryOptimizer:
    """
    查询优化器

    功能:
    1. 查询扩展 - 添加同义词和相关词
    2. 查询重写 - 简化和明确查询
    3. 关键词提取 - 提取关键信息
    4. 实体识别 - 识别实体名称
    """

    def __init__(self):
        # 同义词词典
        self._synonyms = {
            "故障": ["异常", "错误", "问题", "failure", "error"],
            "延迟": ["延时", "耗时", "latency", "delay"],
            "重启": ["重新启动", "restart", "reboot"],
            "监控": ["监测", "观测", "monitoring", "metrics"],
            "日志": ["log", "logging", "记录"],
            "配置": ["设置", "参数", "config", "configuration"],
            "服务": ["service", "微服务", "应用"],
            "机器": ["服务器", "主机", "server", "host"],
            "内存": ["memory", "RAM", "内存使用"],
            "CPU": ["处理器", "processor", "CPU使用率"],
        }

        # 停用词
        self._stopwords = {
            "的", "了", "是", "在", "有", "和", "与", "或", "我", "你",
            "他", "她", "它", "这", "那", "什么", "怎么", "如何", "为什么",
        }

    async def optimize(self, query: str) -> str:
        """
        优化查询

        Args:
            query: 原始查询

        Returns:
            优化后的查询
        """
        analysis = await self.analyze(query)
        return analysis.optimized

    async def analyze(self, query: str) -> QueryAnalysis:
        """
        分析查询

        Args:
            query: 原始查询

        Returns:
            QueryAnalysis
        """
        # 提取关键词
        keywords = self._extract_keywords(query)

        # 提取实体
        entities = self._extract_entities(query)

        # 识别意图
        intent = self._identify_intent(query)

        # 计算复杂度
        complexity = self._calculate_complexity(query, keywords, entities)

        # 生成优化查询
        optimized = self._generate_optimized(query, keywords, entities)

        return QueryAnalysis(
            original=query,
            optimized=optimized,
            keywords=keywords,
            entities=entities,
            intent=intent,
            complexity=complexity,
        )

    def _extract_keywords(self, query: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取
        # 分词 (简化处理)
        words = re.findall(r'[一-鿿]+|[a-zA-Z]+|\d+', query)

        # 过滤停用词
        keywords = [w for w in words if w not in self._stopwords and len(w) > 1]

        return keywords

    def _extract_entities(self, query: str) -> List[str]:
        """提取实体"""
        entities = []

        # 服务名模式 (以 service, srv, app 结尾)
        service_pattern = r'\b\w+(?:service|srv|app)\b'
        entities.extend(re.findall(service_pattern, query, re.IGNORECASE))

        # IP 地址
        ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        entities.extend(re.findall(ip_pattern, query))

        # 区域名称
        region_pattern = r'(新加坡|美国|欧洲|东京|上海|北京|深圳|[A-Z]{2,3}(?:-?[A-Z]+)*)'
        entities.extend(re.findall(region_pattern, query))

        return list(set(entities))

    def _identify_intent(self, query: str) -> str:
        """识别意图"""
        query_lower = query.lower()

        # 意图关键词映射
        intent_keywords = {
            "diagnosis": ["故障", "异常", "错误", "问题", "排查", "诊断"],
            "query": ["是什么", "怎么", "如何", "什么是", "查询"],
            "action": ["重启", "修改", "执行", "部署", "发布"],
            "analysis": ["分析", "统计", "趋势", "对比"],
            "visualization": ["图表", "趋势", "画", "显示"],
        }

        for intent, keywords in intent_keywords.items():
            if any(kw in query for kw in keywords):
                return intent

        return "query"

    def _calculate_complexity(
        self,
        query: str,
        keywords: List[str],
        entities: List[str],
    ) -> float:
        """计算查询复杂度"""
        complexity = 0.0

        # 长度因素
        if len(query) > 100:
            complexity += 0.2
        elif len(query) > 50:
            complexity += 0.1

        # 关键词数量
        if len(keywords) > 5:
            complexity += 0.2
        elif len(keywords) > 3:
            complexity += 0.1

        # 实体数量
        complexity += min(len(entities) * 0.1, 0.3)

        # 复杂查询词
        complex_words = ["分析", "对比", "关联", "根因", "趋势", "详细"]
        for word in complex_words:
            if word in query:
                complexity += 0.1

        return min(complexity, 1.0)

    def _generate_optimized(
        self,
        query: str,
        keywords: List[str],
        entities: List[str],
    ) -> str:
        """生成优化查询"""
        # 如果查询已经很短，直接返回
        if len(query) < 20:
            return query

        # 提取核心信息
        core = " ".join(keywords[:5])

        # 添加同义词扩展
        expansions = []
        for keyword in keywords[:3]:
            if keyword in self._synonyms:
                expansions.extend(self._synonyms[keyword][:2])

        if expansions:
            return f"{core} ({' '.join(expansions[:3])})"

        return core

    async def expand_query(self, query: str) -> List[str]:
        """
        查询扩展

        生成多个查询变体以提高召回率
        """
        analysis = await self.analyze(query)
        variants = [query]

        # 添加关键词组合
        if analysis.keywords:
            variants.append(" ".join(analysis.keywords))

        # 添加同义词扩展
        for keyword in analysis.keywords[:3]:
            if keyword in self._synonyms:
                for synonym in self._synonyms[keyword][:2]:
                    expanded = query.replace(keyword, synonym)
                    variants.append(expanded)

        return list(set(variants))
