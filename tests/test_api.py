from unittest.mock import Mock

from fastapi.testclient import TestClient

from backend import agent
from backend.main import app
from tests.fakes import final_answer as _final_answer
from tests.fakes import tool_call_response as _tool_call_response

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_conversation_lifecycle():
    response = client.post("/conversations", json={"title": "My Conversation"})
    assert response.status_code == 200
    conversation_id = response.json()["id"]
    assert response.json()["status"] == "active"

    response = client.get("/conversations")
    assert any(c["id"] == conversation_id for c in response.json())

    response = client.get(f"/conversations/{conversation_id}")
    assert response.status_code == 200
    assert response.json()["messages"] == []  # system prompt is hidden from the UI view

    response = client.delete(f"/conversations/{conversation_id}")
    assert response.status_code == 200

    response = client.get(f"/conversations/{conversation_id}")
    assert response.status_code == 404


def test_get_unknown_conversation_returns_404():
    response = client.get("/conversations/999999")
    assert response.status_code == 404


def test_full_message_and_approval_flow(monkeypatch):
    responses = [
        _tool_call_response("call_1", "calculator", {"expression": "21 * 2"}),
        _tool_call_response("call_2", "save_report", {"filename": "api_test.txt", "content": "42"}),
        _final_answer("Done — calculated 42 and saved it."),
    ]
    monkeypatch.setattr(agent._client.chat.completions, "create", Mock(side_effect=responses))

    conversation_id = client.post("/conversations", json={"title": "Flow"}).json()["id"]

    response = client.post(
        f"/conversations/{conversation_id}/messages", json={"content": "calc and save"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "awaiting_approval"
    assert body["tool_call"]["tool_name"] == "save_report"

    response = client.post(f"/conversations/{conversation_id}/approve", json={"approve": True})
    assert response.status_code == 200
    assert response.json() == {"status": "done", "answer": "Done — calculated 42 and saved it."}

    logs = client.get(f"/conversations/{conversation_id}/logs").json()
    assert len(logs) == 2
    assert {log["tool_name"] for log in logs} == {"calculator", "save_report"}
    assert all(log["status"] == "success" for log in logs)


def test_sending_message_while_awaiting_approval_returns_409(monkeypatch):
    responses = [_tool_call_response("call_1", "save_report", {"filename": "x.txt", "content": "y"})]
    monkeypatch.setattr(agent._client.chat.completions, "create", Mock(side_effect=responses))

    conversation_id = client.post("/conversations", json={"title": "Blocked"}).json()["id"]
    client.post(f"/conversations/{conversation_id}/messages", json={"content": "save something"})

    response = client.post(
        f"/conversations/{conversation_id}/messages", json={"content": "another one"}
    )
    assert response.status_code == 409
