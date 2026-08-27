#!/usr/bin/env python3
"""
全链路测试验证

运行方式: python3 tests/test_full_chain.py
"""

import asyncio
import sys
import os
import pytest

# 确保从项目根目录运行
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_project_root)
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, 'proto_gen', 'python'))

# 先导入 grpc
import grpc

# 然后导入 proto
import agent_pb2
import agent_pb2_grpc

# 导入项目模块
from src.grpc_service.servicer import AgentServicer
from src.grpc_service.server import serve_grpc


class ChainTestResult:
    """测试结果"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def pass_(self, name):
        self.passed += 1
        print(f"  ✅ {name}")

    def fail(self, name, error):
        self.failed += 1
        self.errors.append((name, error))
        print(f"  ❌ {name}: {error}")


def run_proto_messages():
    """测试 Proto 消息定义"""
    print("\n📡 测试 Proto 消息定义")
    result = ChainTestResult()

    # DiagnoseRequest
    try:
        req = agent_pb2.DiagnoseRequest(
            session_id="test-session",
            query="网络延迟诊断",
            mode="sequential",
        )
        assert req.session_id == "test-session"
        result.pass_("DiagnoseRequest 创建")
    except Exception as e:
        result.fail("DiagnoseRequest 创建", str(e))

    # DiagnoseResponse
    try:
        resp = agent_pb2.DiagnoseResponse(
            success=True,
            message="诊断完成",
            confidence=0.95,
        )
        assert resp.success is True
        result.pass_("DiagnoseResponse 创建")
    except Exception as e:
        result.fail("DiagnoseResponse 创建", str(e))

    # TraceStep
    try:
        step = agent_pb2.TraceStep(
            step_id=1,
            step_type="agent",
            agent_name="KnowledgeAgent",
            action="search",
            duration_ms=100,
            status="success",
        )
        assert step.agent_name == "KnowledgeAgent"
        result.pass_("TraceStep 创建")
    except Exception as e:
        result.fail("TraceStep 创建", str(e))

    # HealthCheckResponse
    try:
        resp = agent_pb2.HealthCheckResponse(
            status=agent_pb2.HealthCheckResponse.SERVING,
            version="5.0.0",
        )
        assert resp.status == agent_pb2.HealthCheckResponse.SERVING
        result.pass_("HealthCheckResponse 创建")
    except Exception as e:
        result.fail("HealthCheckResponse 创建", str(e))

    # 序列化测试
    try:
        req = agent_pb2.DiagnoseRequest(query="test")
        serialized = req.SerializeToString()
        req2 = agent_pb2.DiagnoseRequest()
        req2.ParseFromString(serialized)
        assert req2.query == "test"
        result.pass_("Proto 序列化/反序列化")
    except Exception as e:
        result.fail("Proto 序列化/反序列化", str(e))

    return result


def run_module_imports():
    """测试模块导入"""
    print("\n📦 测试模块导入")
    result = ChainTestResult()

    try:
        result.pass_("Proto 模块导入")
    except Exception as e:
        result.fail("Proto 模块导入", str(e))

    try:
        from src.grpc_service.servicer import AgentServicer
        result.pass_("AgentServicer 导入")
    except Exception as e:
        result.fail("AgentServicer 导入", str(e))

    try:
        from src.grpc_service.server import serve_grpc, serve_dual
        result.pass_("gRPC 服务器导入")
    except Exception as e:
        result.fail("gRPC 服务器导入", str(e))

    try:
        from src.agents.service import get_agent_service
        result.pass_("AgentService 导入")
    except Exception as e:
        result.fail("AgentService 导入", str(e))

    try:
        from src.knowledge.service import get_knowledge_service
        result.pass_("KnowledgeService 导入")
    except Exception as e:
        result.fail("KnowledgeService 导入", str(e))

    try:
        from src.visualization import AdvancedVisualizationService
        result.pass_("VisualizationService 导入")
    except Exception as e:
        result.fail("VisualizationService 导入", str(e))

    try:
        from src.skill.service import SkillService
        result.pass_("SkillService 导入")
    except Exception as e:
        result.fail("SkillService 导入", str(e))

    try:
        from src.llm import get_llm_gateway
        result.pass_("LLMGateway 导入")
    except Exception as e:
        result.fail("LLMGateway 导入", str(e))

    return result


@pytest.mark.asyncio
async def run_grpc_server():
    """测试 gRPC 服务器启动"""
    print("\n🚀 测试 gRPC 服务器")
    result = ChainTestResult()

    try:
        server = await serve_grpc(port=50052)
        result.pass_("gRPC 服务器启动成功")

        await server.stop(0)
        result.pass_("gRPC 服务器停止成功")
    except Exception as e:
        result.fail("gRPC 服务器", str(e))

    return result


@pytest.mark.asyncio
async def run_servicer():
    """测试 Servicer 方法"""
    print("\n🔧 测试 Servicer 方法")
    result = ChainTestResult()

    try:
        from unittest.mock import Mock, AsyncMock, patch

        mock_agent = Mock()
        mock_agent.process = AsyncMock(return_value=Mock(
            success=True,
            message="测试成功",
            intent="diagnosis",
            confidence=0.9,
            trace=[],
            chart_data=None,
            skill_recommendation=None,
        ))

        with patch('src.grpc_service.servicer.get_agent_service', return_value=mock_agent):
            with patch('src.grpc_service.servicer.get_knowledge_service', return_value=Mock()):
                servicer = AgentServicer()

                # 测试 HealthCheck
                request = agent_pb2.HealthCheckRequest()
                response = await servicer.HealthCheck(request, Mock())
                if response.status == agent_pb2.HealthCheckResponse.SERVING:
                    result.pass_("HealthCheck 方法")
                else:
                    result.fail("HealthCheck 方法", "状态异常")

    except Exception as e:
        result.fail("Servicer 方法测试", str(e))

    return result


def main():
    """运行所有测试"""
    print("=" * 60)
    print("🔬 全链路测试验证")
    print("=" * 60)

    results = []

    # 运行测试
    results.append(run_proto_messages())
    results.append(run_module_imports())

    # 异步测试
    try:
        results.append(asyncio.run(run_grpc_server()))
    except Exception as e:
        print(f"  ❌ gRPC 服务器测试失败: {e}")

    try:
        results.append(asyncio.run(run_servicer()))
    except Exception as e:
        print(f"  ❌ Servicer 测试失败: {e}")

    # 汇总
    total_passed = sum(r.passed for r in results)
    total_failed = sum(r.failed for r in results)

    print("\n" + "=" * 60)
    print(f"📊 总体结果: {total_passed}/{total_passed + total_failed} 测试通过")
    print("=" * 60)

    return total_failed == 0


def test_proto_messages():
    assert run_proto_messages().failed == 0


def test_module_imports():
    assert run_module_imports().failed == 0


@pytest.mark.asyncio
async def test_grpc_server():
    assert (await run_grpc_server()).failed == 0


@pytest.mark.asyncio
async def test_servicer():
    assert (await run_servicer()).failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
