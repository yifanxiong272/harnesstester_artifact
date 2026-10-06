"""Optional checks against a supplied formal source tree."""

from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys

import pytest

ARTIFACT = Path(__file__).resolve().parents[2]
FORMAL = os.environ.get("LDH_FORMAL_ROOT")
REFERENCE = Path(FORMAL or ".") / "src/common/llm_dependent/python"
CASES = sorted((REFERENCE / "flow/tests").glob("*_regression.py")) if FORMAL else []


def executable_ast(source: str) -> str:
    """Compare Python structure while allowing comments and docstrings to differ."""

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if ast.get_docstring(node, clean=False) is not None:
                del node.body[0]
    return ast.dump(tree)


def test_executable_ast_ignores_only_documentation():
    plain = 'class C:\n    async def f(self):\n        return "result"\n'
    documented = (
        '"""Module documentation."""\n'
        '# A comment.\n'
        'class C:\n'
        '    """Class documentation."""\n'
        '    async def f(self):\n'
        '        """Function documentation."""\n'
        '        return "result"\n'
    )
    assert executable_ast(plain) == executable_ast(documented)
    assert executable_ast('def f():\n    "doc"\n    return 1') == executable_ast(
        'def f():\n    return 1'
    )
    for left, right in (
        (plain, plain.replace('"result"', '"changed"')),
        ('value = "a"', 'value = "b"'),
        ('if True:\n    "a"', 'if True:\n    "b"'),
    ):
        assert executable_ast(left) != executable_ast(right)


@pytest.mark.skipif(not FORMAL, reason="set LDH_FORMAL_ROOT for reference checks")
def test_python_transfer_rules_match_formal():
    for source in REFERENCE.rglob("*.py"):
        relative = source.relative_to(REFERENCE)
        # Refactored files have separate structural or behavioral comparisons.
        if (
            "tests" in relative.parts
            or relative.name == "project_cli.py"
            or relative
            in {
                Path("flow/payload.py"),
                Path("flow/analysis.py"),
                Path("flow/resolver.py"),
                Path("common.py"),
            }
        ):
            continue
        actual = (ARTIFACT / "llm_dependent/python" / relative).read_text(encoding="utf-8")
        if relative == Path("flow/indexing.py"):
            # Parameter shadowing must not change definition-scope annotations.
            for expression in ("arg.annotation", "info.node.returns"):
                corrected = f"annotation_class_keys({expression}, info.parent_scope, index)"
                assert actual.count(corrected) == 1
                actual = actual.replace(corrected, corrected.replace("parent_scope", "scope"))
        assert executable_ast(actual) == executable_ast(source.read_text(encoding="utf-8")), relative


@pytest.mark.skipif(not FORMAL, reason="set LDH_FORMAL_ROOT for reference checks")
def test_span_helpers_match_formal():
    def definitions(path):
        return [
            ast.dump(node)
            for node in ast.parse(path.read_text()).body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef))
            and node.name != "scan_source_files"
        ]

    assert definitions(ARTIFACT / "llm_dependent/python/common.py") == definitions(
        REFERENCE / "common.py"
    )


@pytest.mark.skipif(not FORMAL, reason="set LDH_FORMAL_ROOT for reference checks")
def test_unchanged_python_transfer_rules_match_formal():
    refactored = {
        "static_refs",
        "seed_module_body_facts",
        "seed_class_body_facts",
        "seed_static_assignment_facts",
        "eval_static_expr",
        "eval_expr",
        "module_read_refs_for_expr",
        "module_target_refs",
        "module_span",
        "class_span",
        "static_span",
        "class_read_refs_for_expr",
        "class_target_refs",
        "definition_scope_read_refs",
        "info_for_path",
        "read_ref_facts",
        "resolve_name",
        "resolve_imported_symbol",
        "scope_bindings",
    }

    class InlineForwarders(ast.NodeTransformer):
        def visit_FunctionDef(self, node):
            if node.name in refactored | {
                "analyze_project",
                "eval_value_expr",
                "should_drop_constructor_target",
                # Unpacked argument binding has independent flow regressions.
                "callee_actual_infos",
            }:
                return None
            return self.generic_visit(node)

        def visit_ImportFrom(self, node):
            if node.module == "functools":
                return None
            if node.module == "models":
                node.names = [alias for alias in node.names if alias.name != "NameEnv"]
            if node.module == "common":
                node.names = [
                    alias for alias in node.names if alias.name != "scan_source_files"
                ]
            return node

        def visit_Name(self, node):
            if node.id == "src_roots":
                node.id = "source_files"
            return node

        def visit_arg(self, node):
            if node.arg == "src_roots":
                node.arg = "source_files"
            return self.generic_visit(node)

        def visit_keyword(self, node):
            if node.arg == "src_roots":
                node.arg = "source_files"
            return self.generic_visit(node)

        def visit_Assign(self, node):
            if any(
                isinstance(target, ast.Attribute) and target.attr == "src_roots"
                for target in node.targets
            ):
                return None
            return self.generic_visit(node)

        def visit_Attribute(self, node):
            self.generic_visit(node)
            if node.attr == "eval_value_expr":
                node.attr = "value_result_info"
            return node

        def visit_Call(self, node):
            self.generic_visit(node)
            if isinstance(node.func, ast.Name) and node.func.id == "scan_source_files":
                node.func.id = "sorted"
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "should_drop_constructor_target"
            ):
                return ast.Call(
                    func=ast.Name(id="isinstance", ctx=ast.Load()),
                    args=[
                        node.args[0],
                        ast.Attribute(
                            value=ast.Name(id="ast", ctx=ast.Load()),
                            attr="Subscript",
                            ctx=ast.Load(),
                        ),
                    ],
                    keywords=[],
                )
            return node

    for name in ("analysis.py", "resolver.py"):
        original = ast.parse((REFERENCE / "flow" / name).read_text())
        source = (ARTIFACT / "llm_dependent/python/flow" / name).read_text()
        if name == "resolver.py":
            # These exact lexical-scope corrections have behavioral regression cases.
            corrections = {
                "                enclosing_has_binding = True\n                break\n":
                    "                enclosing_has_binding = True\n",
                "        if scope_bindings(root, env, index) is not None:\n            return []\n": "",
            }
            for corrected, previous in corrections.items():
                assert source.count(corrected) == 1
                source = source.replace(corrected, previous)
        actual = ast.parse(source)
        assert ast.dump(InlineForwarders().visit(actual)) == ast.dump(
            InlineForwarders().visit(original)
        )


@pytest.mark.parametrize("case", CASES, ids=lambda path: path.stem)
def test_formal_python_regression_on_artifact(case):
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("python_reference.py")),
            str(case.resolve()),
        ],
        env={**os.environ, "PYTHONPATH": str(ARTIFACT), "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
