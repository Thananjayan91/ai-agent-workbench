import pytest

from backend.tools.calculator import evaluate, execute


def test_evaluate_basic_arithmetic():
    assert evaluate("2 + 3 * 4") == 14


def test_evaluate_parentheses_and_division():
    assert evaluate("(10 - 4) / 2") == 3


def test_evaluate_power_and_unary_minus():
    assert evaluate("-2 ** 2") == -4


def test_evaluate_rejects_names():
    with pytest.raises(ValueError):
        evaluate("__import__('os').system('echo hi')")


def test_evaluate_rejects_function_calls():
    with pytest.raises(ValueError):
        evaluate("abs(-5)")


def test_evaluate_rejects_invalid_syntax():
    with pytest.raises(ValueError):
        evaluate("2 +")


def test_execute_wraps_result():
    assert execute("1 + 1") == {"expression": "1 + 1", "result": 2}
