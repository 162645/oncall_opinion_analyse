from src.api.router.chat import ChatResponse


def test_chat_response_exposes_verification_contract():
    response = ChatResponse(
        success=False,
        session_id="session-1",
        message="无法基于真实数据给出结论",
        mode="sequential",
        verdict="ABSTAIN",
        run_id="run-1",
        evidence=[{
            "evidence_id": "E1",
            "query_id": "ping.summary",
            "status": "unavailable",
            "error": "ClickHouse unavailable",
        }],
    )
    payload = response.model_dump()
    assert payload["verdict"] == "ABSTAIN"
    assert payload["run_id"] == "run-1"
    assert payload["evidence"][0]["query_id"] == "ping.summary"
