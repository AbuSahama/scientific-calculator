#!/usr/bin/env python3
"""Colourful scientific calculator web app.

Run with:
    python3 calculator_app.py

Then open http://localhost:8000
"""

from __future__ import annotations

import ast
import html
import math
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs


ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "templates" / "index.html"
STYLE = ROOT / "static" / "style.css"
import os

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 8000))

CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}

FUNCTIONS = {
    "sqrt": math.sqrt,
    "log": math.log10,
    "ln": math.log,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "abs": abs,
}

OPERATORS = {
    ast.Add: lambda left, right: left + right,
    ast.Sub: lambda left, right: left - right,
    ast.Mult: lambda left, right: left * right,
    ast.Div: lambda left, right: left / right,
    ast.Mod: lambda left, right: left % right,
    ast.Pow: lambda left, right: left**right,
}

UNARY_OPERATORS = {
    ast.UAdd: lambda value: value,
    ast.USub: lambda value: -value,
}


class CalculatorError(ValueError):
    """Raised when the calculator expression cannot be evaluated safely."""


def evaluate_expression(expression: str) -> float:
    cleaned = expression.strip().replace("^", "**")
    if not cleaned:
        raise CalculatorError("Enter a calculation first.")

    try:
        tree = ast.parse(cleaned, mode="eval")
    except SyntaxError as exc:
        raise CalculatorError("That expression is not complete.") from exc

    return float(evaluate_node(tree.body))


def evaluate_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)

    if isinstance(node, ast.Name) and node.id in CONSTANTS:
        return CONSTANTS[node.id]

    if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
        left = evaluate_node(node.left)
        right = evaluate_node(node.right)
        return OPERATORS[type(node.op)](left, right)

    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPERATORS:
        return UNARY_OPERATORS[type(node.op)](evaluate_node(node.operand))

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        function = FUNCTIONS.get(node.func.id)
        if function is None or len(node.args) != 1 or node.keywords:
            raise CalculatorError("Unsupported function.")
        return function(evaluate_node(node.args[0]))

    raise CalculatorError("Only calculator numbers, operators, and functions are allowed.")


def format_result(value: float) -> str:
    if not math.isfinite(value):
        raise CalculatorError("Result is outside the calculator range.")
    if value.is_integer():
        return str(int(value))
    return f"{value:.12g}"


def apply_key(expression: str, key: str) -> tuple[str, str]:
    if key == "clear":
        return "", ""
    if key == "backspace":
        return expression[:-1], ""
    if key == "equals":
        result = format_result(evaluate_expression(expression))
        return result, result
    if key == "sqrt":
        return expression + "sqrt(", ""
    if key == "square":
        return expression + "^2", ""
    if key == "log":
        return expression + "log(", ""
    if key == "ln":
        return expression + "ln(", ""
    if key in {"sin", "cos", "tan"}:
        return expression + f"{key}(", ""
    return expression + key, ""


class CalculatorHandler(BaseHTTPRequestHandler):
    def do_GET(self):

        if self.path == "/static/style.css":
            self.respond(STYLE.read_text(), "text/css")
            return

        if self.path == "/static/images/Background.png":
            image = (ROOT / "static" / "images" / "Background.png").read_bytes()

            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(image)))
            self.end_headers()
            self.wfile.write(image)
            return

        self.render_page("", "", "")

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        fields = parse_qs(self.rfile.read(length).decode())
        expression = fields.get("expression", [""])[0]
        key = fields.get("key", [""])[0]
        result = ""
        error = ""

        try:
            expression, result = apply_key(expression, key)
        except (CalculatorError, ZeroDivisionError, ValueError, OverflowError):
            error = "Please check the calculation."

        self.render_page(expression, result, error)

    def render_page(self, expression: str, result: str, error: str) -> None:
        page = TEMPLATE.read_text()
        page = page.replace("{{ expression }}", html.escape(expression))
        page = page.replace("{{ result }}", html.escape(result))
        page = page.replace("{{ error }}", html.escape(error))
        self.respond(page, "text/html")

    def respond(self, body: str, content_type: str) -> None:
        encoded = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), CalculatorHandler)
    print(f"Calculator running at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
