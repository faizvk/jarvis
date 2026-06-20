"""Tests for the safe calculator tool."""
from types import SimpleNamespace

from jarvis.tools.calculator import HANDLERS

calc = HANDLERS["calculate"]
CTX = SimpleNamespace()


def test_basic_arithmetic():
    assert calc({"expression": "17 * 23"}, CTX) == "17 * 23 = 391"


def test_order_of_operations_and_parens():
    assert calc({"expression": "2 + 3 * 4"}, CTX).endswith("= 14")
    assert calc({"expression": "(2 + 3) * 4"}, CTX).endswith("= 20")


def test_integer_division_and_float_normalisation():
    assert calc({"expression": "10 / 2"}, CTX).endswith("= 5")  # 5.0 -> 5
    assert calc({"expression": "7 // 2"}, CTX).endswith("= 3")


def test_division_by_zero_is_handled():
    assert "zero" in calc({"expression": "1 / 0"}, CTX).lower()


def test_rejects_non_arithmetic():
    assert "couldn't" in calc({"expression": "__import__('os')"}, CTX).lower()
    assert "couldn't" in calc({"expression": "a + 1"}, CTX).lower()


def test_blocks_huge_exponent():
    assert "couldn't" in calc({"expression": "2 ** 100000"}, CTX).lower()


def test_empty_expression():
    assert "No expression" in calc({"expression": ""}, CTX)
