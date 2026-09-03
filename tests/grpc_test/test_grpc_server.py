"""
gRPC 服务端测试

测试内容:
1. Proto 文件导入测试
2. 服务器启动测试
3. Servicer 方法测试
4. 边界情况测试
"""

import asyncio
import sys
import os
import pytest
from unittest.mock import Mock, AsyncMock, patch

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'proto_gen', 'python'))

import agent_pb2
import agent_pb2_grpc


class TestProtoDefinitions:
    """Proto 定义测试"""

    def test_diagnose_request_fields(self):
        """测试 DiagnoseRequest 字段"""
        req = agent_pb2.DiagnoseRequest(
            session_id="test-session",
            query="网络延迟诊断",
            mode="sequential",
        )
        assert req.session_id == "test-session"
        assert req.query == "网络延迟诊断"
        assert req.mode == "sequential"

    def test_diagnose_response_fields(self):
        """测试 DiagnoseResponse 字段"""
        resp = agent_pb2.DiagnoseResponse(
            success=True,
            message="诊断完成",
            confidence=0.95,
        )
        assert resp.success is True
        assert resp.message == "诊断完成"
        assert abs(resp.confidence - 0.95) < 0.01

    def test_trace_step(self):
        """测试 TraceStep 字段"""
        step = agent_pb2.TraceStep(
            step_id=1,
            step_type="agent",
            agent_name="KnowledgeAgent",
            action="search",
            duration_ms=100,
            status="success",
        )
        assert step.step_id == 1
        assert step.agent_name == "KnowledgeAgent"

    def test_search_request(self):
        """测试 SearchRequest 字段"""
        req = agent_pb2.SearchRequest(
            query="网络问题",
            top_k=5,
        )
        assert req.query == "网络问题"
        assert req.top_k == 5

    def test_health_check_response(self):
        """测试健康检查响应"""
        resp = agent_pb2.HealthCheckResponse(
            status=agent_pb2.HealthCheckResponse.SERVING,
            version="5.0.0",
        )
        assert resp.status == agent_pb2.HealthCheckResponse.SERVING
        assert resp.version == "5.0.0"

    def test_proto_serialization(self):
        """测试 Proto 序列化/反序列化"""
        req = agent_pb2.DiagnoseRequest(
            session_id="test",
            query="test query",
            mode="parallel",
        )
        serialized = req.SerializeToString()
        req2 = agent_pb2.DiagnoseRequest()
        req2.ParseFromString(serialized)
        assert req2.session_id == "test"
        assert req2.query == "test query"


class TestServicerMethods:
    """Servicer 方法测试 - 使用同步方式测试"""

    def test_servicer_import(self):
        """测试 Servicer 导入"""
        from src.grpc_service.servicer import AgentServicer
        assert AgentServicer is not None

    def test_health_check_sync(self):
        """测试健康检查 - 同步包装"""
        async def run_test():
            from src.grpc_service.servicer import AgentServicer
            servicer = AgentServicer()
            request = agent_pb2.HealthCheckRequest()
            context = Mock()
            response = await servicer.HealthCheck(request, context)
            assert response.status == agent_pb2.HealthCheckResponse.SERVING
            assert response.version == "5.0.0"

        asyncio.run(run_test())


class TestGRPCServer:
    """gRPC 服务器测试"""

    def test_server_import(self):
        """测试服务器导入"""
        from src.grpc_service.server import serve_grpc, serve_dual
        assert serve_grpc is not None
        assert serve_dual is not None

    def test_server_start_stop(self):
        """测试服务器启动和停止"""
        async def run_test():
            from src.grpc_service.server import serve_grpc
            server = await serve_grpc(port=50052)
            assert server is not None
            await server.stop(0)

        asyncio.run(run_test())


class TestEdgeCases:
    """边界情况测试"""

    def test_empty_query(self):
        """测试空查询"""
        req = agent_pb2.DiagnoseRequest(query="", mode="sequential")
        assert req.query == ""

    def test_long_query(self):
        """测试超长查询"""
        long_query = "网络延迟问题 " * 2000  # ~14000 chars
        req = agent_pb2.DiagnoseRequest(query=long_query, mode="sequential")
        assert len(req.query) > 10000

    def test_unicode_query(self):
        """测试 Unicode 查询"""
        req = agent_pb2.DiagnoseRequest(
            query="网络延迟⚡️🔥 问题诊断",
            mode="sequential",
        )
        assert "⚡️" in req.query

    def test_special_characters(self):
        """测试特殊字符"""
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        req = agent_pb2.DiagnoseRequest(query=special_chars, mode="sequential")
        assert req.query == special_chars


# 运行测试的命令
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
