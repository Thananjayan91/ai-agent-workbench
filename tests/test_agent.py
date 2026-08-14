import json
from unittest.mock import Mock

import pytest

from backend import agent, conversations
from backend.db import get_session
from backend.tools.file_tools import WORKSPACE_DIR
from tests.fakes import final_answer as _final_answer
from tests.fakes import tool_call_response as _tool_call_response


@pytest.fixture
def session():
    s = get_session()
    yield s
    s.close()


@pytest.fixture
def conversation(session):
    return conversations.create_conversation(session, "Test conversation")


def test_simple_tool_call_then_final_answer(monkeypatch, session, conversation):
    responses = [
        _tool_call_response("call_1", "calculator", {"expression": "2 + 2"}),
        _final_answer("The answer is 4."),
    ]
    monkeypatch.setattr(agent._client.chat.completions, "create", Mock(side_effect=responses))

    result = agent.send_message(session, conversation, "what is 2+2?")

    assert result == {"status": "done", "answer": "The answer is 4."}
    tool_calls = conversations.get_tool_calls(session, conversation.id)
    assert len(tool_calls) == 1
    assert tool_calls[0].tool_name == "calculator"
    assert tool_calls[0].status == "success"
    assert json.loads(tool_calls[0].result_json)["result"] == 4


def test_dangerous_action_pauses_for_approval_then_resumes(monkeypatch, session, conversation):
    responses = [
        _tool_call_response(
            "call_1", "save_report", {"filename": "report.txt", "content": "hello"}
        ),
        _final_answer("Saved the report."),
    ]
    monkeypatch.setattr(agent._client.chat.completions, "create", Mock(side_effect=responses))

    result = agent.send_message(session, conversation, "save a report")

    assert result["status"] == "awaiting_approval"
    assert result["tool_call"]["tool_name"] == "save_report"
    assert conversation.status == "awaiting_approval"
    assert not (WORKSPACE_DIR / "report.txt").exists()

    result = agent.resolve_approval(session, conversation, approve=True)

    assert result == {"status": "done", "answer": "Saved the report."}
    assert (WORKSPACE_DIR / "report.txt").read_text() == "hello"


def test_dangerous_action_rejected_does_not_execute(monkeypatch, session, conversation):
    responses = [
        _tool_call_response(
            "call_1", "save_report", {"filename": "rejected.txt", "content": "hello"}
        ),
        _final_answer("Understood, I will not save it."),
    ]
    monkeypatch.setattr(agent._client.chat.completions, "create", Mock(side_effect=responses))

    agent.send_message(session, conversation, "save a report")
    result = agent.resolve_approval(session, conversation, approve=False)

    assert result == {"status": "done", "answer": "Understood, I will not save it."}
    assert not (WORKSPACE_DIR / "rejected.txt").exists()
    tool_calls = conversations.get_tool_calls(session, conversation.id)
    assert tool_calls[0].status == "rejected"


def test_tool_failure_retries_then_surfaces_error_to_model(monkeypatch, session, conversation):
    responses = [
        _tool_call_response("call_1", "calculator", {"expression": "not valid("}),
        _final_answer("I couldn't calculate that."),
    ]
    monkeypatch.setattr(agent._client.chat.completions, "create", Mock(side_effect=responses))

    result = agent.send_message(session, conversation, "calculate something invalid")

    assert result == {"status": "done", "answer": "I couldn't calculate that."}
    tool_calls = conversations.get_tool_calls(session, conversation.id)
    assert tool_calls[0].status == "error"
    assert tool_calls[0].attempts == 3  # 1 initial attempt + 2 retries (default TOOL_MAX_RETRIES)
    assert tool_calls[0].error is not None


def test_send_message_blocked_while_awaiting_approval(monkeypatch, session, conversation):
    responses = [
        _tool_call_response("call_1", "save_report", {"filename": "x.txt", "content": "y"}),
    ]
    monkeypatch.setattr(agent._client.chat.completions, "create", Mock(side_effect=responses))
    agent.send_message(session, conversation, "save a report")

    with pytest.raises(ValueError):
        agent.send_message(session, conversation, "another message")
