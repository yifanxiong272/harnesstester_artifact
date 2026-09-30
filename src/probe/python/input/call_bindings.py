"""Resolve unambiguous lexical bindings used by public call-route discovery."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field


@dataclass
class Scope:
    node: ast.AST
    parent: Scope | None
    bindings: dict[str, list[ast.AST]] = field(default_factory=dict)

    def bind(self, name: str, node: ast.AST) -> None:
        self.bindings.setdefault(name, []).append(node)

    def lookup(
        self, name: str, seen: frozenset[ast.AST] = frozenset()
    ) -> ast.AST | None:
        if name in self.bindings:
            values = self.bindings[name]
            if len(values) != 1:
                return None
            value = values[0]
            if isinstance(value, ast.Name) and isinstance(value.ctx, ast.Load):
                return None if value in seen else self.lookup(value.id, seen | {value})
            if isinstance(value, ast.Global) and self.parent:
                scope = self.parent
                while scope.parent:
                    scope = scope.parent
                return scope.lookup(name, seen)
            if isinstance(value, ast.Nonlocal):
                return self.parent.lookup(name, seen) if self.parent else None
            return value
        return self.parent.lookup(name, seen) if self.parent else None


class CallBindings(ast.NodeVisitor):
    """Index bindings and call scopes without inferring unknown runtime values."""

    def __init__(self, tree: ast.Module):
        self.scope = Scope(tree, None)
        self.scopes = {tree: self.scope}
        self.calls: dict[ast.Call, Scope] = {}
        self.receivers: dict[ast.arg, ast.ClassDef] = {}
        self.visit(tree)

    def resolve(self, call: ast.Call, name: str) -> ast.AST | None:
        scope = self.calls.get(call)
        return scope.lookup(name) if scope else None

    def member(self, call: ast.Call) -> ast.AST | None:
        expression = call.func
        if not isinstance(expression, ast.Attribute) or not isinstance(
            expression.value, ast.Name
        ):
            return None
        binding = self.resolve(call, expression.value.id)
        owner = (
            binding
            if isinstance(binding, ast.ClassDef)
            else self.receivers.get(binding)
        )
        if owner is None:
            return None
        values = self.scopes[owner].bindings.get(expression.attr, [])
        return values[0] if len(values) == 1 else None

    def visit_Call(self, node: ast.Call) -> None:
        self.calls[node] = self.scope
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.scope.bind(node.id, node)

    def bind_target(self, target: ast.expr, value: ast.expr) -> None:
        if isinstance(target, ast.Name):
            self.scope.bind(target.id, value)
        else:
            self.visit(target)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        for target in node.targets:
            self.bind_target(target, node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        # A value-free annotation binds a local name only in a function scope.
        if node.value is not None:
            self.visit(node.value)
            self.bind_target(node.target, node.value)
        elif isinstance(self.scope.node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.visit(node.target)
        self.visit(node.annotation)

    def visit_FunctionDef(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda
    ) -> None:
        outer = self.scope
        is_lambda = isinstance(node, ast.Lambda)
        if not is_lambda:
            outer.bind(node.name, node)
        decorators = [] if is_lambda else node.decorator_list
        for value in [
            *decorators,
            *node.args.defaults,
            *node.args.kw_defaults,
        ]:
            if value is not None:
                self.visit(value)
        parent = outer.parent if isinstance(outer.node, ast.ClassDef) else outer
        self.scope = self.scopes[node] = Scope(node, parent)
        arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        for argument in [*arguments, node.args.vararg, node.args.kwarg]:
            if argument is not None:
                self.scope.bind(argument.arg, argument)
        positional = [*node.args.posonlyargs, *node.args.args]
        is_static = any(
            isinstance(decorator, ast.Name)
            and decorator.id == "staticmethod"
            or isinstance(decorator, ast.Attribute)
            and decorator.attr == "staticmethod"
            for decorator in decorators
        )
        if (
            not is_lambda
            and isinstance(outer.node, ast.ClassDef)
            and positional
            and not is_static
        ):
            self.receivers[positional[0]] = outer.node
        for statement in [node.body] if is_lambda else node.body:
            self.visit(statement)
        self.scope = outer

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_Lambda = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        outer = self.scope
        outer.bind(node.name, node)
        for value in [*node.decorator_list, *node.bases, *node.keywords]:
            self.visit(value)
        parent = outer.parent if isinstance(outer.node, ast.ClassDef) else outer
        self.scope = self.scopes[node] = Scope(node, parent)
        for statement in node.body:
            self.visit(statement)
        self.scope = outer

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.scope.bind(alias.asname or alias.name.split(".")[0], alias)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            self.scope.bind(alias.asname or alias.name, alias)

    def visit_Global(self, node: ast.Global | ast.Nonlocal) -> None:
        for name in node.names:
            self.scope.bind(name, node)

    visit_Nonlocal = visit_Global

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name:
            self.scope.bind(node.name, node)
        self.generic_visit(node)

    def visit_MatchAs(self, node: ast.MatchAs | ast.MatchStar) -> None:
        if node.name:
            self.scope.bind(node.name, node)
        self.generic_visit(node)

    visit_MatchStar = visit_MatchAs

    def visit_MatchMapping(self, node: ast.MatchMapping) -> None:
        if node.rest:
            self.scope.bind(node.rest, node)
        self.generic_visit(node)

    def visit_ListComp(
        self, node: ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp
    ) -> None:
        outer = self.scope
        self.visit(node.generators[0].iter)
        parent = outer.parent if isinstance(outer.node, ast.ClassDef) else outer
        self.scope = self.scopes[node] = Scope(node, parent)
        for index, generator in enumerate(node.generators):
            if index:
                self.visit(generator.iter)
            self.visit(generator.target)
            for condition in generator.ifs:
                self.visit(condition)
        if isinstance(node, ast.DictComp):
            self.visit(node.key)
            self.visit(node.value)
        else:
            self.visit(node.elt)
        self.scope = outer

    visit_SetComp = visit_ListComp
    visit_DictComp = visit_ListComp
    visit_GeneratorExp = visit_ListComp

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        scope = self.scope
        while isinstance(
            scope.node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
        ):
            scope = scope.parent
        # Comprehension values can refer to names outside the destination scope.
        scope.bind(node.target.id, node.value if scope is self.scope else node.target)
        self.visit(node.value)
