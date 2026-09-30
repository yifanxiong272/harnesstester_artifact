#!/usr/bin/env python3
"""Match provider calls and endpoints using names and propagated facts."""

from __future__ import annotations

import ast
from collections.abc import Iterable

from ..source_rules import (
    LLM_PROVIDER_MODULES,
    certified_provider_endpoint,
    certified_provider_client_constructor,
    certified_provider_module_call,
    is_provider_client_request_suffix,
)
from .facts import FactStore
from .models import FunctionContext, ReturnRef
from .resolver import (
    expr_path,
    full_names_for_expr,
    imported_refs_for_path,
    literal_string,
    refs_for_path,
    refs_for_read_expr,
    resolve_call,
)


CALLABLE_PREFIX = "request_callable:"
MODULE_PREFIX = "provider_module:"
ATTR_PROXY_PREFIX = "provider_attr_proxy:"
HTTP_POST_CALLS = {"httpx.post", "requests.post"}
HTTP_REQUEST_CALLS = {"httpx.request", "requests.request"}
BEDROCK_RUNTIME_PROVIDER = "aws.bedrock-runtime"
EXECUTOR_CALLBACK_CALLS = {"asyncio.to_thread", "asyncio.threads.to_thread"}


def callable_kind(provider_module: str) -> str:
    """Encode provider request-callable provenance in the provider fact table."""

    return f"{CALLABLE_PREFIX}{provider_module}"


def callable_provider(kind: str) -> str | None:
    """Return provider module if `kind` marks a request callable."""

    return kind[len(CALLABLE_PREFIX) :] if kind.startswith(CALLABLE_PREFIX) else None


def provider_module_kind(provider_module: str) -> str:
    """Encode provenance for a dynamically imported provider module."""

    return f"{MODULE_PREFIX}{provider_module}"


def provider_module(kind: str) -> str | None:
    """Return provider module if `kind` marks a provider module value."""

    return kind[len(MODULE_PREFIX) :] if kind.startswith(MODULE_PREFIX) else None


def attr_proxy_kind(provider_module: str) -> str:
    """Encode provenance for values forwarding attributes to a provider module."""

    return f"{ATTR_PROXY_PREFIX}{provider_module}"


def attr_proxy_provider(kind: str) -> str | None:
    """Return provider module if `kind` marks a transparent attribute proxy."""

    return kind[len(ATTR_PROXY_PREFIX) :] if kind.startswith(ATTR_PROXY_PREFIX) else None


def provider_modules(provider_kinds: set[str]) -> set[str]:
    """Return modules represented by provider-module or attr-proxy facts."""

    out: set[str] = set()
    for kind in provider_kinds:
        module = provider_module(kind) or attr_proxy_provider(kind)
        if module:
            out.add(module)
    return out


def client_providers(provider_kinds: set[str]) -> set[str]:
    """Return raw provider-client facts, excluding encoded helper facts."""

    return {kind for kind in provider_kinds if kind in LLM_PROVIDER_MODULES}


def provider_module_value_kind(full_names: Iterable[str]) -> set[str]:
    """Return provider-module facts for resolved provider module values."""

    return {
        provider_module_kind(full_name)
        for full_name in full_names
        if full_name in LLM_PROVIDER_MODULES
    }


def provider_callable_value_kind(full_names: Iterable[str]) -> set[str]:
    """Return source-callable provider facts for resolved value names."""

    out: set[str] = set()
    for full_name in full_names:
        direct = certified_provider_module_call(full_name)
        if direct is not None:
            out.add(callable_kind(direct[0]))
    return out


def dynamic_import_module_kind(call: ast.Call, full_names: Iterable[str]) -> set[str]:
    """Return provider-module facts for importlib.import_module("provider")."""

    if "importlib.import_module" not in set(full_names) or not call.args:
        return set()
    module = literal_string(call.args[0])
    if module not in LLM_PROVIDER_MODULES:
        return set()
    return {provider_module_kind(module)}


def provider_client_constructor_kind(full_names: Iterable[str]) -> set[str]:
    """Return provider client facts for resolved constructor names."""

    out: set[str] = set()
    for full_name in full_names:
        constructor = certified_provider_client_constructor(full_name)
        if constructor is not None:
            out.add(constructor[0])
    return out


def provider_service_client_kind(
    call: ast.Call,
    full_names: Iterable[str],
    ctx: FunctionContext | None = None,
    facts: FactStore | None = None,
    index=None,
) -> set[str]:
    """Match client calls whose service argument resolves to `bedrock-runtime`."""

    names = set(full_names)
    is_client_constructor = bool(
        names & {"boto3.client", "boto3.session.Session.client"}
    ) or (isinstance(call.func, ast.Attribute) and call.func.attr == "client")
    if not is_client_constructor:
        return set()

    service_expr = next(
        (keyword.value for keyword in call.keywords if keyword.arg == "service_name"),
        call.args[0] if call.args else None,
    )
    if service_expr is None:
        return set()
    if ctx is not None and facts is not None and index is not None:
        services = strings_for_expr(service_expr, ctx, facts, index)
    else:
        literal = literal_string(service_expr)
        services = {literal} if literal is not None else set()
    return {BEDROCK_RUNTIME_PROVIDER} if "bedrock-runtime" in services else set()


def provider_request_callable_kind(provider_kinds: set[str], suffix: str) -> set[str]:
    """Match module-specific request suffixes or the shared client allowlist."""

    out: set[str] = set()
    for module in provider_modules(provider_kinds):
        if certified_provider_module_call(f"{module}.{suffix}") is not None:
            out.add(callable_kind(module))
    if is_provider_client_request_suffix(suffix):
        for provider in client_providers(provider_kinds):
            out.add(callable_kind(provider))
    return out


def provider_client_constructor_from_kinds(
    provider_kinds: set[str],
    suffix: str,
) -> set[str]:
    """Return provider-client facts for constructor suffixes on module proxies."""

    out: set[str] = set()
    for module in provider_modules(provider_kinds):
        if certified_provider_client_constructor(f"{module}.{suffix}") is not None:
            out.add(module)
    return out


def provider_request_callable_from_path(
    path: str,
    ctx: FunctionContext,
    facts: FactStore,
    index,
) -> set[str]:
    """Return request-callable facts represented by a dotted value path."""

    parts = path.split(".")
    out: set[str] = set()
    for split in range(1, len(parts)):
        base_path = ".".join(parts[:split])
        suffix = ".".join(parts[split:])
        provider_kinds = provider_kinds_for_path(base_path, ctx, facts, index)
        out.update(provider_request_callable_kind(provider_kinds, suffix))
    return out


def provider_client_constructor_from_path(
    path: str,
    ctx: FunctionContext,
    facts: FactStore,
    index,
) -> set[str]:
    """Return provider-client facts represented by a module-proxy constructor path."""

    parts = path.split(".")
    out: set[str] = set()
    for split in range(1, len(parts)):
        base_path = ".".join(parts[:split])
        suffix = ".".join(parts[split:])
        provider_kinds = provider_kinds_for_path(base_path, ctx, facts, index)
        out.update(provider_client_constructor_from_kinds(provider_kinds, suffix))
    return out


def provider_kinds_for_path(
    path: str,
    ctx: FunctionContext,
    facts: FactStore,
    index,
) -> set[str]:
    """Return provider facts for a path, including project-local imports."""

    out: set[str] = set()
    refs = refs_for_path(path, ctx, facts, index, include_prefixes=False)
    refs.extend(imported_refs_for_path(path, ctx.info.scope, index))
    for ref in refs:
        out.update(facts.provider_of(ref))
    return out


def provider_request_call(
    call: ast.Call,
    ctx: FunctionContext,
    facts: FactStore,
    index,
) -> set[str]:
    """Match request calls using resolved names, provider facts, and endpoints."""

    direct_providers = {
        direct[0]
        for full_name in full_names_for_expr(call.func, ctx, index)
        if (direct := certified_provider_module_call(full_name)) is not None
    }
    if direct_providers:
        return direct_providers

    callable_providers: set[str] = set()
    for ref in refs_for_read_expr(call.func, ctx, facts, index, include_prefixes=False):
        for kind in facts.provider_of(ref):
            provider = callable_provider(kind)
            if provider:
                callable_providers.add(provider)
    if callable_providers:
        return callable_providers

    for target in resolve_call(call, ctx, facts, index):
        for kind in facts.provider_of(ReturnRef(target.key)):
            provider = callable_provider(kind)
            if provider:
                callable_providers.add(provider)
    if callable_providers:
        return callable_providers

    providers = provider_request_from_path(call, ctx, facts, index)
    providers.update(provider_request_from_constructor_chain(call, ctx, facts, index))
    providers.update(provider_request_from_http_endpoint(call, ctx, facts, index))
    providers.update(provider_request_from_executor_callback(call, ctx, facts, index))
    return providers


def provider_request_from_http_endpoint(
    call: ast.Call,
    ctx: FunctionContext,
    facts: FactStore,
    index,
) -> set[str]:
    """Match HTTP POST calls to allowlisted provider REST endpoints."""

    call_names = set(full_names_for_expr(call.func, ctx, index))
    is_post_method = isinstance(call.func, ast.Attribute) and call.func.attr == "post"
    is_request_method = isinstance(call.func, ast.Attribute) and call.func.attr == "request"
    if call_names & HTTP_POST_CALLS or is_post_method:
        return provider_endpoint_from_url_expr(http_url_arg(call, 0), ctx, facts, index)
    if (call_names & HTTP_REQUEST_CALLS or is_request_method) and http_method_is_post(
        call,
        ctx,
        facts,
        index,
    ):
        return provider_endpoint_from_url_expr(http_url_arg(call, 1), ctx, facts, index)
    return set()


def provider_request_from_executor_callback(
    call: ast.Call,
    ctx: FunctionContext,
    facts: FactStore,
    index,
) -> set[str]:
    """Recognize provider callables invoked through standard executors."""

    call_names = set(full_names_for_expr(call.func, ctx, index))
    callback = None
    if call_names & EXECUTOR_CALLBACK_CALLS and call.args:
        callback = call.args[0]
    elif (
        isinstance(call.func, ast.Attribute)
        and call.func.attr == "run_in_executor"
        and len(call.args) >= 2
    ):
        callback = call.args[1]
    if callback is None:
        return set()

    if isinstance(callback, ast.Lambda):
        out: set[str] = set()
        for nested in ast.walk(callback.body):
            if isinstance(nested, ast.Call):
                out.update(provider_request_call(nested, ctx, facts, index))
        return out

    out: set[str] = set()
    for full_name in full_names_for_expr(callback, ctx, index):
        direct = certified_provider_module_call(full_name)
        if direct is not None:
            out.add(direct[0])
    path = expr_path(callback)
    if path:
        for kind in provider_request_callable_from_path(path, ctx, facts, index):
            provider = callable_provider(kind)
            if provider:
                out.add(provider)
    for ref in refs_for_read_expr(callback, ctx, facts, index, include_prefixes=False):
        for kind in facts.provider_of(ref):
            provider = callable_provider(kind)
            if provider:
                out.add(provider)
    return out


def http_url_arg(call: ast.Call, position: int) -> ast.AST | None:
    """Return the URL expression from requests/httpx call shapes."""

    for keyword in call.keywords:
        if keyword.arg == "url":
            return keyword.value
    if len(call.args) > position:
        return call.args[position]
    return None


def http_method_is_post(
    call: ast.Call,
    ctx: FunctionContext,
    facts: FactStore,
    index,
) -> bool:
    """Return true when requests.request/httpx.request is known to be POST."""

    method_expr = None
    for keyword in call.keywords:
        if keyword.arg == "method":
            method_expr = keyword.value
            break
    if method_expr is None and call.args:
        method_expr = call.args[0]
    return any(value.upper() == "POST" for value in strings_for_expr(method_expr, ctx, facts, index))


def provider_endpoint_from_url_expr(
    expr: ast.AST | None,
    ctx: FunctionContext,
    facts: FactStore,
    index,
) -> set[str]:
    """Match provider endpoints carried by literal/string facts."""

    out: set[str] = set()
    for value in endpoint_strings_for_expr(expr, ctx, facts, index):
        match = certified_provider_endpoint(value)
        if match is not None:
            out.add(match[0])
    return out


def endpoint_strings_for_expr(
    expr: ast.AST | None,
    ctx: FunctionContext,
    facts: FactStore,
    index,
    seen: set[tuple[object, int, int]] | None = None,
) -> set[str]:
    """Resolve bounded local string composition used only for endpoint checks.

    Follow local assignments, class fields, and selected string wrappers without
    adding general string/data-flow facts.
    """

    if expr is None:
        return set()
    seen = seen if seen is not None else set()
    key = (
        ctx.info.key,
        id(expr),
        0,
    )
    if key in seen:
        return set()
    seen.add(key)

    out = strings_for_expr(expr, ctx, facts, index)
    if isinstance(expr, ast.JoinedStr):
        parts: list[set[str]] = []
        for value in expr.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append({value.value})
            elif isinstance(value, ast.FormattedValue):
                parts.append(
                    endpoint_strings_for_expr(value.value, ctx, facts, index, seen)
                )
            else:
                return out
        out.update(combine_string_parts(parts))
    elif isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add):
        out.update(
            combine_string_parts(
                [
                    endpoint_strings_for_expr(expr.left, ctx, facts, index, seen),
                    endpoint_strings_for_expr(expr.right, ctx, facts, index, seen),
                ]
            )
        )
    elif isinstance(expr, ast.BoolOp):
        for value in expr.values:
            out.update(endpoint_strings_for_expr(value, ctx, facts, index, seen))
    elif isinstance(expr, ast.Name):
        for value in assignment_values(ctx.info.node, expr.id, getattr(expr, "lineno", None)):
            out.update(endpoint_strings_for_expr(value, ctx, facts, index, seen))
    elif isinstance(expr, ast.Attribute) and expr_path(expr):
        path = expr_path(expr)
        if path and path.startswith(("self.", "cls.")) and ctx.info.class_key is not None:
            for info in index.functions.values():
                if info.class_key != ctx.info.class_key:
                    continue
                method_ctx = FunctionContext(info=info)
                for value in assignment_values(info.node, path, None):
                    out.update(
                        endpoint_strings_for_expr(value, method_ctx, facts, index, seen)
                    )
    elif isinstance(expr, ast.Call):
        call_names = set(full_names_for_expr(expr.func, ctx, index))
        if (
            isinstance(expr.func, ast.Name)
            and expr.func.id == "str"
            and expr.args
        ):
            out.update(endpoint_strings_for_expr(expr.args[0], ctx, facts, index, seen))
        elif isinstance(expr.func, ast.Attribute) and expr.func.attr in {
            "lstrip",
            "rstrip",
            "strip",
        }:
            out.update(
                endpoint_strings_for_expr(expr.func.value, ctx, facts, index, seen)
            )
        elif call_names & {"os.getenv", "os.environ.get"}:
            default_expr = next(
                (keyword.value for keyword in expr.keywords if keyword.arg == "default"),
                expr.args[1] if len(expr.args) >= 2 else None,
            )
            out.update(endpoint_strings_for_expr(default_expr, ctx, facts, index, seen))

        for target in resolve_call(expr, ctx, facts, index):
            target_info = index.functions.get(target.key)
            if target_info is None:
                continue
            target_ctx = FunctionContext(info=target_info)
            for value in return_values(target_info.node):
                out.update(
                    endpoint_strings_for_expr(value, target_ctx, facts, index, seen)
                )
    return out


class _FunctionValueCollector(ast.NodeVisitor):
    """Collect assignments/returns without descending into nested functions."""

    def __init__(self, root: ast.AST, target_path: str | None, before_line: int | None) -> None:
        self.root = root
        self.target_path = target_path
        self.before_line = before_line
        self.assignments: list[ast.AST] = []
        self.returns: list[ast.AST] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node is self.root:
            self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if node is self.root:
            self.generic_visit(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return

    def visit_Assign(self, node: ast.Assign) -> None:
        if self.matches_line(node) and any(
            expr_path(target) == self.target_path for target in node.targets
        ):
            self.assignments.append(node.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if (
            node.value is not None
            and self.matches_line(node)
            and expr_path(node.target) == self.target_path
        ):
            self.assignments.append(node.value)
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        if node.value is not None:
            self.returns.append(node.value)

    def matches_line(self, node: ast.AST) -> bool:
        return self.before_line is None or int(getattr(node, "lineno", 0)) < self.before_line


def assignment_values(
    root: ast.AST,
    target_path: str,
    before_line: int | None,
) -> list[ast.AST]:
    collector = _FunctionValueCollector(root, target_path, before_line)
    collector.visit(root)
    return collector.assignments


def return_values(root: ast.AST) -> list[ast.AST]:
    collector = _FunctionValueCollector(root, None, None)
    collector.visit(root)
    return collector.returns


def strings_for_expr(
    expr: ast.AST | None,
    ctx: FunctionContext,
    facts: FactStore,
    index,
) -> set[str]:
    """Return literal strings known for an expression without adding taint."""

    if expr is None:
        return set()
    out: set[str] = set()
    literal = literal_string(expr)
    if literal is not None:
        out.add(literal)
    for ref in refs_for_read_expr(expr, ctx, facts, index, include_prefixes=True):
        out.update(facts.string_of(ref))
    if isinstance(expr, ast.Call):
        for target in resolve_call(expr, ctx, facts, index):
            out.update(facts.string_of(ReturnRef(target.key)))
    out.update(composed_strings_for_expr(expr, ctx, facts, index))
    return out


def composed_strings_for_expr(
    expr: ast.AST,
    ctx: FunctionContext,
    facts: FactStore,
    index,
) -> set[str]:
    """Evaluate bounded literal/fact string composition used by endpoint URLs."""

    if isinstance(expr, ast.JoinedStr):
        parts: list[set[str]] = []
        for value in expr.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append({value.value})
            elif isinstance(value, ast.FormattedValue):
                parts.append(strings_for_expr(value.value, ctx, facts, index))
            else:
                return set()
        return combine_string_parts(parts)
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add):
        return combine_string_parts(
            [
                strings_for_expr(expr.left, ctx, facts, index),
                strings_for_expr(expr.right, ctx, facts, index),
            ]
        )
    return set()


def combine_string_parts(parts: list[set[str]], limit: int = 128) -> set[str]:
    """Return a bounded Cartesian concatenation of statically known strings."""

    combined = {""}
    for part in parts:
        if not part:
            return set()
        combined = {prefix + suffix for prefix in combined for suffix in part}
        if len(combined) > limit:
            return set(sorted(combined)[:limit])
    return combined


def provider_request_from_path(
    call: ast.Call,
    ctx: FunctionContext,
    facts: FactStore,
    index,
) -> set[str]:
    """Match `client.chat.completions.create()` style calls."""

    path = expr_path(call.func)
    if not path:
        return set()
    parts = path.split(".")
    out: set[str] = set()
    for split in range(1, len(parts)):
        base_path = ".".join(parts[:split])
        suffix = ".".join(parts[split:])
        provider_kinds = provider_kinds_for_path(base_path, ctx, facts, index)
        for kind in provider_request_callable_kind(provider_kinds, suffix):
            provider = callable_provider(kind)
            if provider:
                out.add(provider)
    return out


def provider_request_from_constructor_chain(
    call: ast.Call,
    ctx: FunctionContext,
    facts: FactStore,
    index,
) -> set[str]:
    """Match `OpenAI().chat.completions.create()` style calls."""

    base, suffix = attribute_base_and_suffix(call.func)
    if not suffix or not is_provider_client_request_suffix(".".join(suffix)):
        return set()
    return client_providers(provider_value_kind(base, ctx, facts, index))


def attribute_base_and_suffix(expr: ast.AST) -> tuple[ast.AST, list[str]]:
    """Split an attribute chain into base expression and suffix parts."""

    suffix: list[str] = []
    current = expr
    while isinstance(current, ast.Attribute):
        suffix.append(current.attr)
        current = current.value
    suffix.reverse()
    return current, suffix


def provider_value_kind(
    expr: ast.AST,
    ctx: FunctionContext,
    facts: FactStore,
    index,
) -> set[str]:
    """Return provider kinds produced by reading `expr`.

    This handles provider client constructors, provider-returning local calls,
    and provider-backed local/class-field refs.
    """

    out: set[str] = set()
    full_names = full_names_for_expr(expr, ctx, index)
    out.update(provider_module_value_kind(full_names))
    out.update(provider_callable_value_kind(full_names))

    if isinstance(expr, ast.Call):
        call_full_names = full_names_for_expr(expr.func, ctx, index)
        out.update(dynamic_import_module_kind(expr, call_full_names))
        if "functools.partial" in call_full_names and expr.args:
            out.update(provider_value_kind(expr.args[0], ctx, facts, index))
        out.update(provider_client_constructor_kind(call_full_names))
        out.update(
            provider_service_client_kind(
                expr,
                call_full_names,
                ctx,
                facts,
                index,
            )
        )
        path = expr_path(expr.func)
        if path:
            out.update(provider_client_constructor_from_path(path, ctx, facts, index))
        for target in resolve_call(expr, ctx, facts, index):
            out.update(facts.provider_of(ReturnRef(target.key)))

    for ref in refs_for_read_expr(expr, ctx, facts, index, include_prefixes=True):
        out.update(facts.provider_of(ref))
    path = expr_path(expr)
    if path:
        for ref in imported_refs_for_path(path, ctx.info.scope, index):
            out.update(facts.provider_of(ref))
    return out
