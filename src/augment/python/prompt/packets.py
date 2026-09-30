#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from augment.python.prompt.code_excerpt import safe_relative_path


def source_outline(project_root: Path, filepath: str) -> dict[str, Any]:
    """Return exact class and function declarations for one target file."""

    safe_relative_path(filepath)
    path = project_root / filepath
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(text, filename=filepath)
    except SyntaxError:
        return {"filepath": filepath, "status": "syntax_error", "declarations": []}

    declarations: list[dict[str, Any]] = []

    def visit(body: list[ast.stmt], scope: list[str]) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                qualname = ".".join([*scope, node.name])
                declarations.append(declaration_view(node, qualname, "class"))
                visit(node.body, [*scope, node.name])
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qualname = ".".join([*scope, node.name])
                kind = (
                    "async_function"
                    if isinstance(node, ast.AsyncFunctionDef)
                    else "function"
                )
                declarations.append(declaration_view(node, qualname, kind))
                visit(node.body, [*scope, node.name])

    visit(tree.body, [])
    return {
        "filepath": filepath,
        "status": "found",
        "declarations": declarations,
    }


def declaration_view(
    node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
    qualname: str,
    kind: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "kind": kind,
        "qualname": qualname,
        "start_line": int(node.lineno),
        "end_line": int(getattr(node, "end_lineno", node.lineno)),
    }
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        result["parameters"] = function_parameters(node.args)
    return result


def function_parameters(arguments: ast.arguments) -> list[str]:
    parameters = [arg.arg for arg in [*arguments.posonlyargs, *arguments.args]]
    if arguments.vararg:
        parameters.append(f"*{arguments.vararg.arg}")
    parameters.extend(arg.arg for arg in arguments.kwonlyargs)
    if arguments.kwarg:
        parameters.append(f"**{arguments.kwarg.arg}")
    return parameters
