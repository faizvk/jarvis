"""A safe arithmetic calculator tool.

Uses an AST walk rather than ``eval`` so only arithmetic is ever evaluated — no
names, calls, attribute access, or other Python. This gives the model a proper
way to do math instead of shelling out through run_command.
"""
from __future__ import annotations

import ast
import operator

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("only numbers are allowed")
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and (abs(right) > 1000 or abs(left) > 1e6):
            raise ValueError("exponent too large")
        return _OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("unsupported expression")


SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": (
                "Evaluate an arithmetic expression such as '17 * 23' or "
                "'2 ** 10 + 5'. Always use this for math instead of running a shell "
                "command. Supports + - * / // % ** and parentheses."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "The arithmetic expression."}
                },
                "required": ["expression"],
            },
        },
    }
]


def _calculate(args: dict, ctx) -> str:
    expression = (args.get("expression") or "").strip()
    if not expression:
        return "No expression was provided."
    try:
        result = _eval(ast.parse(expression, mode="eval").body)
    except ZeroDivisionError:
        return "That divides by zero, which is undefined."
    except Exception:
        return f"I couldn't evaluate '{expression}'."
    if isinstance(result, float) and result.is_integer():
        result = int(result)
    return f"{expression} = {result}"


HANDLERS = {"calculate": _calculate}
