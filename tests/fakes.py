import json

from unittest.mock import Mock


class _FakeFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class _FakeToolCall:
    def __init__(self, call_id, name, arguments):
        self.id = call_id
        self.function = _FakeFunction(name, arguments)


class _FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class _FakeCompletion:
    def __init__(self, message):
        self.choices = [Mock(message=message)]


def final_answer(text):
    return _FakeCompletion(_FakeMessage(content=text, tool_calls=None))


def tool_call_response(call_id, name, arguments):
    tool_call = _FakeToolCall(call_id, name, json.dumps(arguments))
    return _FakeCompletion(_FakeMessage(content=None, tool_calls=[tool_call]))
