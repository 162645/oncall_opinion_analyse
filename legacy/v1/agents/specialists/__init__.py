"""
专业 Agent 实现
包括诊断 Agent、知识 Agent、分析 Agent
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json

from .core import (
    BaseAgent,
    AgentRole,
    AgentContext,
    AgentResult,
)


class KnowledgeAgent(BaseAgent):
    """
    知识检索 Agent

    负责从知识库检索历史案例和 SOP
    """

    def __init__(self, retriever=None, embedding_model=None):
        super().__init__(
            role=AgentRole.KNOWLEDGE,
            name="Knowledge Agent",
            description="从知识库检索历史案例和 SOP 文档",
            tools=["knowledge-search"],
        )
        self.retriever = retriever
        self.embedding_model = embedding_model

    def execute(self, context: AgentContext) -> AgentResult:
        """执行知识检索"""
        self.log_action("start_knowledge_search", context)

        findings = []
        recommendations = []
        next_actions = []

        # 构建查询
        query = self._build_query(context)

        # 如果有嵌入模型和检索器，执行真实检索
        if self.embedding_model and self.retriever:
            query_vector = self.embedding_model.embed_single(query)
            results = self.retriever.search(
                query_vector=query_vector,
                query_text=query,
                limit=5,
            )

            for result in results:
                findings.append({
                    "type": "similar_case",
                    "doc_id": result.doc_id,
                    "content": result.content[:500],  # 截断
                    "similarity": result.score,
                    "metadata": result.metadata,
                })

                # 从历史案例提取建议
                if "解决方案" in result.content:
                    recommendations.append(
                        f"参考案例 {result.doc_id}: 查看解决方案部分"
                    )
        else:
            # 模拟检索结果
            findings.append({
                "type": "simulated",
                "message": "知识检索需要配置 retriever 和 embedding_model",
                "query": query,
            })

        next_actions.append("analysis_agent")

        return AgentResult(
            success=True,
            role=self.role,
            findings=findings,
            recommendations=recommendations,
            next_actions=next_actions,
            confidence=0.85 if findings else 0.3,
        )

    def _build_query(self, context: AgentContext) -> str:
        """构建检索查询"""
        parts = []

        if context.alert_title:
            parts.append(context.alert_title)

        if context.psm:
            parts.append(f"PSM: {context.psm}")

        if context.region:
            parts.append(f"区域: {context.region}")

        if context.alert_description:
            parts.append(context.alert_description[:200])

        return " ".join(parts)


class AnalysisAgent(BaseAgent):
    """
    数据分析 Agent

    负责查询和分析网络测量数据
    """

    def __init__(self, toolbox_client=None):
        super().__init__(
            role=AgentRole.ANALYSIS,
            name="Analysis Agent",
            description="分析网络测量数据，包括延迟、流量、异常事件",
            tools=[
                "query-network-latency",
                "query-network-anomalies",
                "query-traffic-stats",
                "query-link-quality",
            ],
        )
        self.toolbox_client = toolbox_client

    def execute(self, context: AgentContext) -> AgentResult:
        """执行数据分析"""
        self.log_action("start_data_analysis", context)

        findings = []
        recommendations = []
        next_actions = []

        # 确定时间范围
        end_time = context.end_time or datetime.now()
        start_time = context.start_time or (end_time - timedelta(hours=1))

        # 分析步骤
        analysis_steps = [
            ("network_latency", self._analyze_latency),
            ("network_anomalies", self._analyze_anomalies),
            ("link_quality", self._analyze_link_quality),
        ]

        for step_name, step_func in analysis_steps:
            try:
                step_findings = step_func(context, start_time, end_time)
                findings.extend(step_findings)
            except Exception as e:
                findings.append({
                    "type": "error",
                    "step": step_name,
                    "message": str(e),
                })

        # 生成建议
        if any(f.get("type") == "latency_anomaly" for f in findings):
            recommendations.append("检测到延迟异常，建议检查链路状态")

        if any(f.get("type") == "packet_loss" for f in findings):
            recommendations.append("检测到丢包，建议检查网络设备状态")

        next_actions.append("diagnosis_agent")

        return AgentResult(
            success=len(findings) > 0,
            role=self.role,
            findings=findings,
            recommendations=recommendations,
            next_actions=next_actions,
            confidence=0.9 if findings else 0.4,
        )

    def _analyze_latency(
        self,
        context: AgentContext,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Dict[str, Any]]:
        """分析延迟数据"""
        findings = []

        # 模拟分析结果
        # 实际实现中应调用 MCP Toolbox
        findings.append({
            "type": "latency_summary",
            "source_region": context.region or "unknown",
            "avg_latency_ms": 45.2,
            "p99_latency_ms": 120.5,
            "packet_loss_rate": 0.002,
            "time_range": f"{start_time.isoformat()} - {end_time.isoformat()}",
        })

        return findings

    def _analyze_anomalies(
        self,
        context: AgentContext,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Dict[str, Any]]:
        """分析异常事件"""
        findings = []

        # 模拟异常事件分析
        findings.append({
            "type": "anomaly_detection",
            "event_count": 3,
            "events": [
                {
                    "event_type": "latency_spike",
                    "severity": "warning",
                    "timestamp": (end_time - timedelta(minutes=15)).isoformat(),
                },
            ],
        })

        return findings

    def _analyze_link_quality(
        self,
        context: AgentContext,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Dict[str, Any]]:
        """分析链路质量"""
        findings = []

        findings.append({
            "type": "link_quality",
            "health_score": 85,
            "status": "degraded",
            "alert_count": 2,
        })

        return findings


class DiagnosisAgent(BaseAgent):
    """
    故障诊断 Agent

    综合知识检索和数据分析结果，生成诊断结论
    """

    def __init__(self):
        super().__init__(
            role=AgentRole.DIAGNOSIS,
            name="Diagnosis Agent",
            description="综合多源信息，诊断故障根因",
            tools=["intelligent-diagnosis"],
        )

    def execute(self, context: AgentContext) -> AgentResult:
        """执行故障诊断"""
        self.log_action("start_diagnosis", context)

        findings = []
        recommendations = []
        next_actions = []

        # 获取前置 Agent 的结果
        knowledge_findings = context.metadata.get("knowledge_findings", [])
        analysis_findings = context.metadata.get("analysis_findings", [])

        # 综合分析
        root_cause = self._identify_root_cause(
            knowledge_findings,
            analysis_findings,
            context,
        )

        findings.append({
            "type": "diagnosis_result",
            "root_cause": root_cause,
            "confidence": 0.88,
            "evidence": self._collect_evidence(
                knowledge_findings,
                analysis_findings,
            ),
        })

        # 生成建议
        recommendations = self._generate_recommendations(root_cause)

        return AgentResult(
            success=True,
            role=self.role,
            findings=findings,
            recommendations=recommendations,
            next_actions=next_actions,
            confidence=0.88,
        )

    def _identify_root_cause(
        self,
        knowledge_findings: List[Dict],
        analysis_findings: List[Dict],
        context: AgentContext,
    ) -> Dict[str, Any]:
        """识别根因"""
        # 基于分析结果推断根因
        root_cause = {
            "category": "network",
            "subcategory": "latency",
            "description": "网络延迟异常，可能由链路拥塞或设备故障导致",
            "affected_components": [],
        }

        # 从分析结果提取组件
        for finding in analysis_findings:
            if finding.get("type") == "latency_summary":
                root_cause["affected_components"].append({
                    "component": "network_path",
                    "region": finding.get("source_region", "unknown"),
                })

        return root_cause

    def _collect_evidence(
        self,
        knowledge_findings: List[Dict],
        analysis_findings: List[Dict],
    ) -> List[Dict]:
        """收集证据"""
        evidence = []

        for finding in analysis_findings:
            if finding.get("type") in ["latency_summary", "anomaly_detection"]:
                evidence.append({
                    "source": "network_telemetry",
                    "type": finding["type"],
                    "summary": str(finding),
                })

        for finding in knowledge_findings:
            if finding.get("type") == "similar_case":
                evidence.append({
                    "source": "knowledge_base",
                    "type": "historical_case",
                    "doc_id": finding.get("doc_id"),
                })

        return evidence

    def _generate_recommendations(
        self,
        root_cause: Dict[str, Any],
    ) -> List[str]:
        """生成建议"""
        recommendations = []

        if root_cause.get("subcategory") == "latency":
            recommendations.extend([
                "1. 检查链路拥塞情况，确认是否有流量突发",
                "2. 检查网络设备状态，确认是否有设备故障",
                "3. 查看相关历史案例，参考解决方案",
                "4. 如需升级，联系网络运维团队",
            ])

        return recommendations
