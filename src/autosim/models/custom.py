"""Custom drag via safe expression evaluation."""

from __future__ import annotations

import ast
import math
import operator
from typing import Any

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}

_ALLOWED_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_ALLOWED_FUNCTIONS = {
    "abs": abs,
    "pow": pow,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "exp": math.exp,
    "log": math.log,
}


class _SafeEvaluator(ast.NodeVisitor):
    def __init__(self, variables: dict[str, float]) -> None:
        self.variables = variables

    def visit(self, node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return self.visit(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value)
            raise ValueError(f"unsupported constant: {node.value!r}")
        if isinstance(node, ast.Name):
            if node.id not in self.variables:
                raise ValueError(f"unknown variable: {node.id}")
            return self.variables[node.id]
        if isinstance(node, ast.BinOp):
            op = _ALLOWED_BINOPS.get(type(node.op))
            if op is None:
                raise ValueError(f"unsupported operator: {type(node.op).__name__}")
            return op(self.visit(node.left), self.visit(node.right))
        if isinstance(node, ast.UnaryOp):
            op = _ALLOWED_UNARYOPS.get(type(node.op))
            if op is None:
                raise ValueError(f"unsupported unary operator: {type(node.op).__name__}")
            return op(self.visit(node.operand))
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("only simple function calls allowed")
            fn = _ALLOWED_FUNCTIONS.get(node.func.id)
            if fn is None:
                raise ValueError(f"function not allowed: {node.func.id}")
            args = [self.visit(a) for a in node.args]
            return float(fn(*args))
        raise ValueError(f"unsupported expression node: {type(node).__name__}")


def evaluate_expression(expression: str, variables: dict[str, float]) -> float:
    tree = ast.parse(expression, mode="eval")
    return _SafeEvaluator(variables).visit(tree)


class CustomDragModel:
    name = "custom"

    def __init__(self, params: dict[str, Any]) -> None:
        if "expression" not in params:
            raise ValueError("custom drag requires 'expression' parameter")
        self.expression = str(params["expression"])
        self.params = {k: float(v) for k, v in params.items() if k != "expression"}
        # Validate expression parses (use abs_v for magnitude-based expressions)
        evaluate_expression(self.expression, {"v": 1.0, "abs_v": 1.0, **self.params})

    def drag_force(self, v: float) -> float:
        variables = {"v": v, "abs_v": abs(v), **self.params}
        raw = evaluate_expression(self.expression, variables)
        if v == 0:
            return 0.0
        import math
        return -math.copysign(abs(raw), v)

    def drag_sensitivity(self, v: float, eps: float = 1e-6) -> float:
        f_plus = self.drag_force(v + eps)
        f_minus = self.drag_force(v - eps)
        return (f_plus - f_minus) / (2 * eps)
