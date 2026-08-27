"""
gRPC Agent 服务实现
将现有 AgentService 封装为 gRPC 服务

设计理念:
- 复用现有的 Agent 服务逻辑
- 仅做协议转换，不改变业务逻辑
- 支持流式响应，适合长时间任务
"""

import logging
import sys
import os
from typing import AsyncIterator

# 添加 proto_gen 到路径
_proto_gen_path = os.path.join(os.path.dirname(__file__), '..', '..', 'proto_gen', 'python')
if _proto_gen_path not in sys.path:
    sys.path.insert(0, os.path.abspath(_proto_gen_path))

from src.agents.service import get_agent_service, AgentServiceResult
from src.knowledge.service import get_knowledge_service

logger = logging.getLogger(__name__)

# 导入 proto 生成的代码
try:
    import agent_pb2
    import agent_pb2_grpc
    logger.info("✅ gRPC proto files loaded successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import proto files: {e}")
    logger.error("Run: python -m grpc_tools.protoc -I./proto --python_out=./proto_gen/python --grpc_python_out=./proto_gen/python proto/agent.proto")
    raise


class AgentServicer(agent_pb2_grpc.AgentServiceServicer):
    """
    Agent gRPC 服务实现

    实现 proto 中定义的所有 RPC 方法:
    - Diagnose: 智能诊断
    - SearchKnowledge: 知识检索
    - Visualize: 可视化生成
    - DiagnoseStream: 流式诊断
    - HealthCheck: 健康检查
    """

    def __init__(self):
        self.agent_service = get_agent_service()
        logger.info("AgentServicer initialized")

    async def Diagnose(self, request, context) -> agent_pb2.DiagnoseResponse:
        """
        智能诊断

        对应原 HTTP API: POST /api/chat/send

        流程:
        1. 接收请求参数
        2. 调用 Agent 服务处理
        3. 转换为 gRPC 响应格式
        """
        logger.info(f"[gRPC] Diagnose called: session={request.session_id}, query={request.query[:50] if request.query else 'N/A'}...")

        try:
            # 调用现有 Agent 服务
            result = await self.agent_service.process(
                query=request.query,
                mode=request.mode or "sequential",
                session_id=request.session_id or None,
            )

            # 转换为 gRPC 响应
            return self._convert_response(result)
        except Exception as e:
            logger.error(f"[gRPC] Diagnose failed: {e}")
            return agent_pb2.DiagnoseResponse(
                success=False,
                message=f"诊断失败: {str(e)}",
                confidence=0.0,
            )

    async def SearchKnowledge(self, request, context) -> agent_pb2.SearchResponse:
        """
        知识检索

        对应原 HTTP API: POST /api/knowledge/search
        """
        logger.info(f"[gRPC] SearchKnowledge called: query={request.query[:50] if request.query else 'N/A'}...")

        try:
            # 调用知识检索服务
            service = get_knowledge_service()
            search_result = await service.search(
                query=request.query,
                top_k=request.top_k or 5,
            )

            # 转换结果
            results = []
            for i, r in enumerate(search_result.results):
                results.append(agent_pb2.SearchResult(
                    doc_id=getattr(r, 'doc_id', str(i)),
                    content=getattr(r, 'content', ''),
                    score=getattr(r, 'score', 0.0),
                    metadata=dict(getattr(r, 'metadata', {})) if hasattr(r, 'metadata') else {},
                    chunk_index=i,
                ))

            return agent_pb2.SearchResponse(
                success=True,
                results=results,
                total=len(results),
            )
        except Exception as e:
            logger.error(f"[gRPC] SearchKnowledge failed: {e}")
            return agent_pb2.SearchResponse(
                success=False,
                results=[],
                total=0,
                error=str(e),
            )

    async def Visualize(self, request, context) -> agent_pb2.VisualizeResponse:
        """
        可视化生成

        对应原 HTTP API: POST /api/chat/visualize
        """
        logger.info(f"[gRPC] Visualize called: query={request.query[:50] if request.query else 'N/A'}...")

        try:
            from src.visualization import AdvancedVisualizationService

            viz_service = AdvancedVisualizationService()
            result = await viz_service.visualize(request.query)

            if result.success:
                return agent_pb2.VisualizeResponse(
                    success=True,
                    chart_base64=result.chart_base64 or "",
                    chart_html=result.chart_html or "",
                    title=result.title,
                    description=result.description,
                    chart_type=getattr(result.intent, 'chart_type', agent_pb2.ChartType.LINE) if result.intent and hasattr(result.intent, 'chart_type') else "line",
                )

            return agent_pb2.VisualizeResponse(
                success=False,
                error=result.error or "Visualization failed",
            )
        except Exception as e:
            logger.error(f"[gRPC] Visualize failed: {e}")
            return agent_pb2.VisualizeResponse(
                success=False,
                error=str(e),
            )

    async def DiagnoseStream(self, request, context) -> AsyncIterator[agent_pb2.DiagnoseChunk]:
        """
        流式诊断

        实时返回诊断进度，适合:
        - 长时间诊断任务
        - 需要实时反馈的场景
        - 大规模数据处理
        """
        logger.info(f"[gRPC] DiagnoseStream called: session={request.session_id}")

        # 定义诊断阶段
        stages = [
            ("intent_analysis", "analyzing", "正在分析用户意图..."),
            ("knowledge_retrieval", "searching", "正在检索知识库..."),
            ("agent_execution", "processing", "Agent 正在执行..."),
            ("result_generation", "generating", "正在生成结果..."),
        ]

        # 逐阶段发送进度
        for step_name, status, message in stages:
            yield agent_pb2.DiagnoseChunk(
                step_name=step_name,
                status=status,
                message=message,
                is_final=False,
            )

        # 执行实际诊断
        result = await self.agent_service.process(
            query=request.query,
            mode=request.mode or "sequential",
            session_id=request.session_id or None,
        )

        # 发送最终结果
        yield agent_pb2.DiagnoseChunk(
            step_name="complete",
            status="done",
            message="诊断完成",
            is_final=True,
            final_result=self._convert_response(result),
        )

    async def HealthCheck(self, request, context) -> agent_pb2.HealthCheckResponse:
        """
        健康检查

        返回服务状态和组件健康信息
        """
        components = {}

        # 检查知识服务
        try:
            service = get_knowledge_service()
            components["knowledge_service"] = "healthy"
        except Exception as e:
            components["knowledge_service"] = f"unhealthy: {str(e)}"

        # 检查 LLM Gateway
        try:
            from src.llm import get_llm_gateway
            gateway = get_llm_gateway()
            components["llm_gateway"] = "healthy"
        except Exception as e:
            components["llm_gateway"] = f"unhealthy: {str(e)}"

        # 检查 gRPC
        components["grpc_server"] = "healthy"

        return agent_pb2.HealthCheckResponse(
            status=agent_pb2.HealthCheckResponse.SERVING,
            version="5.0.0",
            components=components,
        )

    def _convert_response(self, result: AgentServiceResult) -> agent_pb2.DiagnoseResponse:
        """将 AgentServiceResult 转换为 gRPC 响应"""

        # 转换 trace
        trace = []
        for i, step in enumerate(result.trace or []):
            trace.append(agent_pb2.TraceStep(
                step_id=step.get("step_id", i + 1),
                step_type=step.get("step_type", ""),
                agent_name=step.get("agent_name", ""),
                action=step.get("action", ""),
                reasoning=step.get("reasoning", ""),
                duration_ms=step.get("duration_ms", 0),
                status=step.get("status", ""),
            ))

        # 转换 chart_data
        chart_data = None
        if result.chart_data:
            chart_data = agent_pb2.ChartData(
                base64=result.chart_data.get("base64", ""),
                title=result.chart_data.get("title", ""),
                description=result.chart_data.get("description", ""),
                chart_type=result.chart_data.get("type", "line"),
            )

        # 转换 skill_recommendation
        skill_rec = None
        if result.skill_recommendation:
            skill_rec = agent_pb2.SkillRecommendation(
                recommended=result.skill_recommendation.get("recommended", False),
                reason=result.skill_recommendation.get("reason", ""),
                suggested_name=result.skill_recommendation.get("suggested_name", ""),
                suggested_description=result.skill_recommendation.get("suggested_description", ""),
                confidence=result.skill_recommendation.get("confidence", 0.0),
            )

        return agent_pb2.DiagnoseResponse(
            success=result.success,
            message=result.message or "",
            intent=result.intent or "",
            confidence=result.confidence,
            trace=trace,
            chart_data=chart_data,
            skill_recommendation=skill_rec,
        )
