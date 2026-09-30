#!/usr/bin/env python3
"""Parse model plans and independent test assets.

Validate exact context requests, generated-test paths, syntax, and canonical
boundary metadata before execution. Test collection is determined by pytest.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

from probe.python.models import ProbeAsset, ProbeBoundary, ProbeProposal

SUPPORTED_CONTEXT_REQUEST_KINDS = {
    "module_context",
    "class_definition",
    "function_definition",
    "symbol_definition",
}


ASSET_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}$")
ORACLE_MODES = {"assertion", "exception", "crash"}


def extract_json(text: str) -> dict[str, Any]:
    """Extract one JSON object, allowing a Markdown JSON fence only."""

    stripped = text.strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL)
    if fence:
        stripped = fence.group(1).strip()
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"proposal must be valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("proposal must be a JSON object")
    return data


def parse_proposal_partial(
    text: str | dict[str, Any],
    *,
    max_assets: int = 5,
    allowed_test_roots: list[str] | None = None,
    canonical_plan: dict[str, Any] | None = None,
    public_entrypoints: list[dict[str, Any]] | None = None,
    allow_empty_assets: bool = False,
) -> tuple[ProbeProposal, list[dict[str, Any]]]:
    """Parse a proposal while retaining valid independent assets."""

    data = text if isinstance(text, dict) else extract_json(text)
    raw_assets = data.get("assets")
    if raw_assets is None:
        raw_assets = [data | {"asset_id": data.get("asset_id") or "asset-001"}]
    if not isinstance(raw_assets, list) or (not allow_empty_assets and not raw_assets):
        raise SystemExit("proposal assets must be a non-empty list")
    errors: list[dict[str, Any]] = []

    def record_error(index: int, asset_id: str, message: str) -> None:
        errors.append({"index": index, "asset_id": asset_id, "message": message})

    if len(raw_assets) > max_assets:
        record_error(
            max_assets + 1,
            "",
            f"ignored {len(raw_assets) - max_assets} assets beyond maximum {max_assets}",
        )
        raw_assets = raw_assets[:max_assets]

    boundary_plan = parse_boundary_plan(data)
    plan = canonical_plan or {"boundary_plan": boundary_plan}
    assets: list[ProbeAsset] = []
    seen_asset_ids: set[str] = set()
    for index, raw_asset in enumerate(raw_assets, 1):
        # Preserve valid assets independently of malformed siblings.
        raw_asset_id = raw_asset.get("asset_id") if isinstance(raw_asset, dict) else ""
        try:
            asset = parse_asset(
                raw_asset,
                index=index,
                allowed_test_roots=allowed_test_roots,
                canonical_plan=plan,
                public_entrypoints=public_entrypoints,
            )
        except SystemExit as exc:
            record_error(index, str(raw_asset_id or ""), str(exc))
            continue
        if asset.asset_id in seen_asset_ids:
            record_error(
                index,
                asset.asset_id,
                f"duplicate asset_id ignored: {asset.asset_id}",
            )
            continue
        seen_asset_ids.add(asset.asset_id)
        assets.append(asset)

    if not assets and not allow_empty_assets:
        detail = "; ".join(error["message"] for error in errors) or "no valid assets"
        raise SystemExit(f"proposal has no valid assets: {detail}")
    return (
        ProbeProposal(
            assets=assets,
            boundary_plan=boundary_plan,
            plan_notes=string_list(data, "plan_notes", required=False),
        ),
        errors,
    )


def parse_probe_plan(
    text: str | dict[str, Any],
    *,
    max_context_requests: int = 1,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Parse the boundary plan and bounded exact context requests."""

    data = text if isinstance(text, dict) else extract_json(text)
    boundary_plan = parse_boundary_plan(data)
    context_requests, errors = parse_request_list(
        data.get("context_requests", []),
        max_requests=max_context_requests,
        planning=True,
    )
    exhausted_reason = str(data.get("exhausted_reason") or "").strip()
    if not boundary_plan and not exhausted_reason:
        raise SystemExit("an empty boundary_plan requires exhausted_reason")
    if not boundary_plan and data.get("context_requests"):
        raise SystemExit("an exhausted plan cannot request context")
    plan = {"boundary_plan": boundary_plan, "context_requests": context_requests}
    notes = string_list(data, "plan_notes", required=False)
    if notes:
        plan["plan_notes"] = notes
    if not boundary_plan:
        plan["exhausted_reason"] = exhausted_reason
    return plan, errors


def parse_request_list(
    value: Any,
    *,
    max_requests: int,
    planning: bool = False,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    """Parse bounded requests; planning validates paths before context resolution."""
    if value is None:
        value = []
    if not isinstance(value, list):
        raise SystemExit(
            "context_requests must be a list"
            if planning
            else "context request payload must contain a requests list"
        )
    prefix = "context " if planning else ""
    errors: list[dict[str, Any]] = []

    def record_error(index: int, message: str, **details: Any) -> None:
        errors.append({"index": index, **details, "message": message})

    if len(value) > max_requests:
        record_error(
            max_requests + 1,
            f"ignored {len(value) - max_requests} {prefix}requests "
            f"beyond maximum {max_requests}",
        )
        value = value[:max_requests]
    requests: list[dict[str, str]] = []
    for index, raw in enumerate(value, 1):
        # Record invalid requests as parse errors for the exact context resolver.
        if not isinstance(raw, dict):
            record_error(index, f"{prefix}request must be a JSON object")
            continue
        kind = str(raw.get("kind") or "").strip()
        filepath = str(raw.get("filepath") or "").strip()
        qualname = str(raw.get("qualname") or "").strip()
        reason = str(raw.get("reason") or "").strip()
        if kind not in SUPPORTED_CONTEXT_REQUEST_KINDS:
            record_error(index, f"unsupported {prefix}request kind", kind=kind)
            continue
        if planning:
            try:
                validate_project_path(filepath, field="filepath")
            except SystemExit:
                record_error(index, "unsafe filepath", kind=kind, filepath=filepath)
                continue
        elif not filepath:
            record_error(index, "missing filepath", kind=kind)
            continue
        if kind != "module_context" and not qualname:
            record_error(index, "missing qualname", kind=kind, filepath=filepath)
            continue
        requests.append(
            {"kind": kind, "filepath": filepath, "qualname": qualname, "reason": reason}
        )
    return requests, errors


def parse_boundary_plan(data: dict[str, Any]) -> list[dict[str, Any]]:
    raw_items = data.get("boundary_plan", [])
    if raw_items is None:
        return []
    if not isinstance(raw_items, list):
        raise SystemExit("boundary_plan must be a list")
    items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_item in enumerate(raw_items, 1):
        if not isinstance(raw_item, dict):
            raise SystemExit(f"boundary_plan item {index} must be a JSON object")
        boundary_id = validate_id(
            str(raw_item.get("boundary_id") or f"boundary-{index:03d}"), "boundary_id"
        )
        if boundary_id in seen_ids:
            raise SystemExit(f"duplicate boundary_id: {boundary_id}")
        seen_ids.add(boundary_id)
        target_unit_ids = string_list(raw_item, "target_unit_ids", required=True)
        if not target_unit_ids or len(set(target_unit_ids)) != len(target_unit_ids):
            raise SystemExit(
                f"boundary {boundary_id} target_unit_ids must be non-empty and unique"
            )
        route = object_field(raw_item, "route")
        probe = object_field(raw_item, "probe")
        invariant = object_field(raw_item, "invariant")
        activation_conditions = string_list(
            probe,
            "activation_conditions",
            required=True,
            coerce=True,
        )
        if not activation_conditions:
            raise SystemExit(
                f"boundary {boundary_id} activation_conditions must not be empty"
            )
        independent_oracle = string_field(invariant, "independent_oracle")
        oracle_mode = string_field(invariant, "oracle_mode")
        if oracle_mode not in ORACLE_MODES:
            raise SystemExit(
                f"boundary {boundary_id} oracle_mode must be one of: "
                f"{', '.join(sorted(ORACLE_MODES))}"
            )
        item = {
            "boundary_id": boundary_id,
            "target_unit_ids": target_unit_ids,
            "route": {
                "entrypoint_id": validate_id(string_field(route, "entrypoint_id"))
            },
            "probe": {
                "test_intent": string_field(probe, "test_intent"),
                "activation_conditions": activation_conditions,
            },
            "invariant": {
                "independent_oracle": independent_oracle,
                "supporting_evidence": string_field(invariant, "supporting_evidence"),
                "expected_observation": string_field(invariant, "expected_observation"),
                "oracle_mode": oracle_mode,
            },
        }
        bug_hypothesis = string_field(raw_item, "bug_hypothesis")
        item.update(
            oracle_family=(
                str(raw_item.get("oracle_family", "")).strip() or independent_oracle
            ),
            novelty_from_prior=(
                str(raw_item.get("novelty_from_prior", "")).strip() or "not_provided"
            ),
            bug_hypothesis=bug_hypothesis,
        )
        items.append(item)
    return items


def parse_asset(
    data: Any,
    *,
    index: int,
    allowed_test_roots: list[str] | None,
    canonical_plan: dict[str, Any],
    public_entrypoints: list[dict[str, Any]] | None,
) -> ProbeAsset:
    """Validate one generated pytest asset before materialization."""

    if not isinstance(data, dict):
        raise SystemExit(f"asset {index} must be a JSON object")
    required = (
        "test_file",
        "append_code",
        "input_construction",
        "observable_oracle",
        "primary_oracle",
    )
    missing = [
        key
        for key in required
        if not isinstance(data.get(key), str) or not data.get(key).strip()
    ]
    if missing:
        raise SystemExit(
            f"asset {index} missing required string fields: {', '.join(missing)}"
        )
    asset_id = validate_id(str(data.get("asset_id") or f"asset-{index:03d}"))
    boundary_id = validate_id(string_field(data, "boundary_id"), "boundary_id")
    boundary = next(
        (
            item
            for item in canonical_plan.get("boundary_plan", [])
            if item.get("boundary_id") == boundary_id
        ),
        None,
    )
    if boundary is None:
        raise SystemExit(
            f"asset {asset_id} references unknown boundary_id: {boundary_id}"
        )
    entrypoint_id = string_field(object_field(boundary, "route"), "entrypoint_id")
    entrypoints = public_entrypoints or []
    if not any(item.get("entrypoint_id") == entrypoint_id for item in entrypoints):
        raise SystemExit(
            f"asset {asset_id} references unavailable public entrypoint: {entrypoint_id}"
        )
    probe = object_field(boundary, "probe")
    invariant = object_field(boundary, "invariant")
    test_file = validate_test_file(
        data["test_file"],
        allowed_roots=allowed_test_roots,
    )
    append_code = normalize_append_code(data["append_code"])
    validate_append_code(asset_id, append_code)
    return ProbeAsset(
        asset_id=asset_id,
        boundary=ProbeBoundary(
            boundary_id=boundary_id,
            target_unit_ids=[str(item) for item in boundary.get("target_unit_ids", [])],
            public_entrypoint_id=entrypoint_id,
            test_intent=string_field(probe, "test_intent"),
            activation_conditions=string_list(
                probe, "activation_conditions", required=True, coerce=True
            ),
            independent_oracle=string_field(invariant, "independent_oracle"),
            supporting_evidence=string_field(invariant, "supporting_evidence"),
            expected_observation=string_field(invariant, "expected_observation"),
            oracle_family=string_field(boundary, "oracle_family"),
            novelty_from_prior=string_field(boundary, "novelty_from_prior"),
            bug_hypothesis=string_field(boundary, "bug_hypothesis"),
            oracle_mode=string_field(invariant, "oracle_mode"),
        ),
        input_construction=data["input_construction"].strip(),
        observable_oracle=data["observable_oracle"].strip(),
        primary_oracle=data["primary_oracle"].strip(),
        test_file=test_file,
        append_code=append_code,
        mocking_plan=str(data.get("mocking_plan", "")).strip(),
    )


def validate_id(value: str, label: str = "asset_id") -> str:
    if not ASSET_ID_RE.fullmatch(value):
        raise SystemExit(f"unsafe proposal {label}: {value}")
    return value


def validate_test_file(
    path: str,
    *,
    allowed_roots: list[str] | None = None,
) -> str:
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise SystemExit(f"unsafe proposal test path: {path}")
    normalized = candidate.as_posix()
    roots = allowed_roots or ["tests/generated/benchmarkbr"]
    normalized_roots = [Path(root).as_posix().rstrip("/") + "/" for root in roots]
    if not any(
        normalized.startswith(root) for root in normalized_roots
    ) or not normalized.endswith(".py"):
        raise SystemExit(
            "proposal test_file must be a .py file under one generated test root "
            f"({', '.join(normalized_roots)}): {path}"
        )
    return normalized


def string_field(data: dict[str, Any], key: str, *, required: bool = True) -> str:
    value = data.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    if required:
        raise SystemExit(f"missing required string field: {key}")
    return ""


def object_field(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise SystemExit(f"missing required object field: {key}")
    return value


def validate_project_path(path: str, *, field: str) -> str:
    candidate = Path(path)
    if not path or candidate.is_absolute() or ".." in candidate.parts:
        raise SystemExit(f"unsafe {field}: {path}")
    return candidate.as_posix()


def normalize_append_code(code: str) -> str:
    return code.rstrip() + "\n"


def validate_append_code(asset_id: str, code: str) -> None:
    """Reject invalid syntax and hard runtime-safety violations only."""

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise SystemExit(
            f"asset {asset_id} append_code must be valid Python: {exc}"
        ) from exc
    validate_runtime_safety(asset_id, tree)


def validate_minimized_code_is_subset(
    original: ProbeAsset, minimized: ProbeAsset
) -> None:
    """Require minimization to preserve structure and only delete statements."""

    before = asset_intent_structure(original)
    after = asset_intent_structure(minimized)
    if before["test_signature"] != after["test_signature"]:
        raise SystemExit(
            "minimization changed the test function signature or decorators"
        )
    for key, label in (
        ("imports", "imports"),
        ("protected_top_level", "protected top-level behavior"),
        ("body", "test-body behavior"),
    ):
        if not is_ordered_subset(before[key], after[key]):
            raise SystemExit(f"minimization added or changed {label}")
    if not before["oracles"]:
        raise SystemExit("minimization requires an explicit assertion or pytest oracle")
    if before["oracles"] != after["oracles"]:
        raise SystemExit("minimization changed the primary oracle assertion")


def asset_intent_structure(asset: ProbeAsset) -> dict[str, Any]:
    tree = ast.parse(asset.append_code)
    tests = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]
    if len(tests) != 1:
        raise SystemExit(
            "generated asset must contain exactly one top-level test function"
        )
    test = tests[0]
    imports, protected, body, oracles = [], [], [], []
    for node in tree.body:
        if node is not test:
            target = (
                imports if isinstance(node, (ast.Import, ast.ImportFrom)) else protected
            )
            target.append(canonical_node(node))
    for node in test.body:
        text = canonical_node(node)
        body.append(text)
        if contains_pytest_oracle(node):
            oracles.append(text)
    signature = (
        type(test).__name__,
        canonical_node(test.args),
        tuple(canonical_node(item) for item in test.decorator_list),
        canonical_node(test.returns) if test.returns else "",
        str(getattr(test, "type_comment", "") or ""),
    )
    return {
        "imports": imports,
        "protected_top_level": protected,
        "body": body,
        "oracles": oracles,
        "test_signature": signature,
    }


def canonical_node(node: ast.AST) -> str:
    return ast.dump(node, annotate_fields=True, include_attributes=False)


def contains_pytest_oracle(node: ast.AST) -> bool:
    for current in ast.walk(node):
        if isinstance(current, ast.Assert):
            return True
        if not isinstance(current, ast.Call):
            continue
        if isinstance(current.func, ast.Name) and current.func.id in {"fail", "raises"}:
            return True
        if isinstance(current.func, ast.Attribute) and (
            current.func.attr in {"fail", "raises"}
            or current.func.attr.startswith("assert")
        ):
            return True
    return False


def is_ordered_subset(original: list[str], candidate: list[str]) -> bool:
    # Membership consumes the remaining original statements in order.
    remaining = iter(original)
    return all(statement in remaining for statement in candidate)


def imported_names(aliases: list[ast.alias], members: set[str]) -> set[str]:
    return {alias.asname or alias.name for alias in aliases if alias.name in members}


def validate_runtime_safety(asset_id: str, tree: ast.AST) -> None:
    """Reject explicit host/process/network access and unbounded live sleeps."""

    process_modules: dict[str, str] = {}
    direct_process_names: set[str] = set()
    sleep_names: set[str] = set()
    module_aliases: dict[str, str] = {}
    forbidden_direct_calls = {"__import__", "compile", "eval", "exec"}
    forbidden_call_names: set[str] = set()
    http_methods = {
        "delete",
        "get",
        "head",
        "options",
        "patch",
        "post",
        "put",
        "request",
    }
    forbidden_module_calls = {
        "aiohttp": {"ClientSession", "request"},
        "http.client": {"HTTPConnection", "HTTPSConnection"},
        "httpx": http_methods | {"Client", "AsyncClient", "stream"},
        "requests": http_methods,
        "socket": {"create_connection", "socket"},
        "urllib.request": {"urlopen"},
    }
    forbidden_os_members = {
        "argv",
        "chdir",
        "environ",
        "execv",
        "execve",
        "fork",
        "getcwd",
        "getenv",
        "getpid",
        "getppid",
        "kill",
        "popen",
        "putenv",
        "system",
    }
    forbidden_sys_members = {"argv", "modules", "path"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "subprocess":
                    raise SystemExit(f"asset {asset_id} must not launch subprocesses")
                if alias.name in {"os", "sys", "time", "asyncio"}:
                    process_modules[alias.asname or alias.name] = alias.name
                bound_name = alias.asname or alias.name.split(".")[0]
                module_aliases[bound_name] = alias.name if alias.asname else bound_name
        elif isinstance(node, ast.ImportFrom):
            if node.module == "subprocess":
                raise SystemExit(f"asset {asset_id} must not launch subprocesses")
            if node.module in {"os", "sys"}:
                forbidden = (
                    forbidden_os_members
                    if node.module == "os"
                    else forbidden_sys_members
                )
                direct_process_names.update(imported_names(node.names, forbidden))
            if node.module in {"time", "asyncio"}:
                sleep_names.update(imported_names(node.names, {"sleep"}))
            if node.module == "importlib":
                forbidden_call_names.update(
                    imported_names(node.names, {"import_module"})
                )
            forbidden_members = forbidden_module_calls.get(
                str(node.module or ""), set()
            )
            forbidden_call_names.update(imported_names(node.names, forbidden_members))

    violations = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
            and node.id in direct_process_names
        ):
            violations.append(node.id)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            module = process_modules.get(node.value.id)
            forbidden = (
                forbidden_os_members if module == "os" else forbidden_sys_members
            )
            if module in {"os", "sys"} and node.attr in forbidden:
                violations.append(f"{module}.{node.attr}")
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and (
            node.func.id in forbidden_direct_calls
            or node.func.id in forbidden_call_names
        ):
            violations.append(node.func.id)
        qualified = qualified_call_name(node.func, module_aliases)
        if qualified:
            module, _, member = qualified.rpartition(".")
            if member in forbidden_module_calls.get(module, set()):
                violations.append(qualified)
        is_sleep = isinstance(node.func, ast.Name) and node.func.id in sleep_names
        if isinstance(node.func, ast.Attribute) and isinstance(
            node.func.value, ast.Name
        ):
            module = process_modules.get(node.func.value.id)
            is_sleep = is_sleep or (
                module in {"time", "asyncio"} and node.func.attr == "sleep"
            )
        if is_sleep and not bounded_sleep_call(node):
            violations.append("unbounded sleep")
    if violations:
        raise SystemExit(
            f"asset {asset_id} uses forbidden host, process, network, dynamic-execution, "
            f"or timing behavior: {', '.join(sorted(set(violations)))}"
        )


def qualified_call_name(node: ast.expr, module_aliases: dict[str, str]) -> str:
    """Resolve a statically imported module call without evaluating code."""

    parts = []
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name) or current.id not in module_aliases:
        return ""
    module = module_aliases[current.id]
    return ".".join([module, *reversed(parts)])


def bounded_sleep_call(node: ast.Call) -> bool:
    if not node.args:
        return False
    value = node.args[0]
    return (
        isinstance(value, ast.Constant)
        and isinstance(value.value, (int, float))
        and not isinstance(value.value, bool)
        and 0 <= value.value <= 1
    )


def string_list(
    data: dict[str, Any], key: str, *, required: bool = True, coerce: bool = False
) -> list[str]:
    value = data.get(key, [])
    if value is None and not required:
        return []
    if coerce and isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, list):
        raise SystemExit(f"{key} must be a list of strings")
    if coerce:
        return [coerced for item in value if (coerced := coerce_string_list_item(item))]
    if not all(isinstance(item, str) for item in value):
        raise SystemExit(f"{key} must be a list of strings")
    return [item.strip() for item in value if item.strip()]


def coerce_string_list_item(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, (dict, list)):
        return json.dumps(item, sort_keys=True, separators=(",", ":"))
    if item is None:
        return ""
    return str(item).strip()
