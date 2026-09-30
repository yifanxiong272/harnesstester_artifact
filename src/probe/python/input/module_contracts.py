#!/usr/bin/env python3
"""Extract prompt-safe Python module import and export contracts."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from common.utils.python.paths import safe_project_path, safe_relative_path


def read_module(path: Path) -> tuple[str, ast.Module | None]:
    """Read module text and parse its AST; malformed source has no tree."""
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        return text, ast.parse(text)
    except SyntaxError:
        return text, None


def module_names(
    filepath: str,
    *,
    import_roots: tuple[str, ...] = (),
) -> list[str]:
    """Return deterministic import candidates for a project-relative Python file."""

    safe_relative_path(filepath)
    path = Path(filepath)
    if path.suffix != ".py":
        return []
    parts = list(path.with_suffix("").parts)
    for root in import_roots:
        safe_relative_path(root)
        root_parts = list(Path(root).parts)
        if parts[: len(root_parts)] == root_parts:
            parts = parts[len(root_parts) :]
            break
    if parts and parts[-1] == "__init__":
        parts.pop()
    candidates = [parts]
    if parts and parts[0] in {"src", "lib"}:
        candidates.append(parts[1:])
    result = []
    for candidate in reversed(candidates):
        module = ".".join(candidate)
        if module and module not in result:
            result.append(module)
    return result


def module_contracts(
    project_root: Path,
    files: list[str],
    *,
    limit: int = 24,
    import_roots: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    """Return compact buggy-side import contracts for target modules."""

    contracts = []
    for filepath in sorted(set(files)):
        if len(contracts) >= limit:
            break
        path = safe_project_path(project_root, filepath)
        if not path.exists() or path.suffix != ".py":
            continue
        _, tree = read_module(path)
        if tree is None:
            continue
        contracts.append(
            {
                "filepath": filepath,
                "suggested_imports": module_names(
                    filepath,
                    import_roots=import_roots,
                ),
                "exports": exported_symbols(tree),
            }
        )
    return contracts


def exported_symbols(tree: ast.Module) -> list[dict[str, Any]]:
    explicit = explicit_all(tree)
    records = []
    for node in tree.body:
        for name, kind in declaration_names(node):
            if name.startswith("_") or (explicit is not None and name not in explicit):
                continue
            records.append(
                {
                    "name": name,
                    "kind": kind,
                    "line": int(getattr(node, "lineno", 0) or 0),
                }
            )
    return records


def explicit_all(tree: ast.Module) -> set[str] | None:
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in targets
        ):
            continue
        value = node.value
        if not isinstance(value, (ast.List, ast.Tuple, ast.Set)):
            return None
        names = {
            item.value
            for item in value.elts
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
        }
        return names
    return None


def declaration_names(node: ast.stmt) -> list[tuple[str, str]]:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return [(node.name, "function")]
    if isinstance(node, ast.ClassDef):
        return [(node.name, "class")]
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        return [
            (target.id, "variable")
            for target in targets
            if isinstance(target, ast.Name)
        ]
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return [
            (alias.asname or alias.name.split(".", 1)[0], "import")
            for alias in node.names
        ]
    return []
