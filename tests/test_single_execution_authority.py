from types import SimpleNamespace

import pytest

from src.agents.service import AgentService


@pytest.mark.asyncio
async def test_agent_service_delegates_to_harness_only(monkeypatch):
    calls = []

    class FakeHarness:
        async def execute(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                success=True,
                message="grounded answer",
                confidence=0.9,
                trace=[{"agent_name": "verifier"}],
                chart_data={"verdict": "PASS", "evidence": []},
                state={"task": {"kind": "network_analysis"}},
            )

    monkeypatch.setattr("src.agents.service.get_harness", lambda: FakeHarness())
    service = AgentService()
    result = await service.process("分析 UKRAINE 的 Ping 延迟", mode="debate", session_id="s1")

    assert result.success is True
    assert result.message == "grounded answer"
    assert calls[0]["session_id"] == "s1"
    assert calls[0]["metadata"]["mode"] == "debate"
    assert not hasattr(service, "orchestrator")
