"""Compare source packets and bounded context with the formal implementation."""

from __future__ import annotations

import ast
import json
from dataclasses import asdict
from pathlib import Path
from textwrap import indent
from types import SimpleNamespace

import pytest

from test_compaction import formal_module
from probe.python.input.constraints import probe_constraints
from probe.python.input import target_packets
from probe.python.input import public_routes
from probe.python.input import module_contracts
from probe.python.input.public_routes import public_target_routes
from probe.python.prompt import context_index
from probe.python.prompt.prompts import prompt_packet


SOURCE = """from functools import wraps
from .base import Base

__all__ = ["Counter", "advance", "LIMIT"]
LIMIT: int = 3
left = right = 1
(a, b) = (1, 2)

def decorate(fn):
    @wraps(fn)
    def wrapped(value):
        return fn(value)
    return wrapped

def _increment(value):
    return value + 1

@decorate
def advance(value):
    return _increment(value)

class Counter(Base):
    total = 0

    def __init__(self):
        self.total = 0

    @staticmethod
    def start():
        return _increment(0)

    @classmethod
    def create(cls):
        return cls()

    async def step(self):
        self.total = _increment(self.total)
        return self.total

    def _hidden(self):
        return self.total

if True:
    conditional = 1
"""


@pytest.fixture
def source_project(tmp_path):
    files = {
        "src/pkg/counter.py": SOURCE,
        "src/pkg/base.py": "class Base:\n    def run(self):\n        return self._hidden()\n",
        "src/pkg/__init__.py": "from .counter import Counter\n",
        "src/pkg/broken.py": "def unfinished(\n",
        "src/pkg/empty.py": "",
        "tests/test_counter.py": "from pkg.counter import advance\n"
        + "# padding\n" * 900,
        "tests/test_alias.py": "import pkg.counter as subject\n",
        "tests/test_parent.py": "from pkg import counter as subject\n",
        "tests/test_counter_stem.py": "assert True\n",
        "tests/test_invalid.py": "invalid syntax !!\n",
        "test/test_unrelated.py": "from elsewhere import Counter\n",
        "elsewhere.py": "SECRET = 1\n",
    }
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return tmp_path


def unit_specs():
    specs = []

    def visit(body, parents=()):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                qualname = ".".join((*parents, node.name))
                specs.append(
                    {
                        "filepath": "src/pkg/counter.py",
                        "qualname": qualname,
                        "kind": "class"
                        if isinstance(node, ast.ClassDef)
                        else "function",
                        "start_line": node.lineno,
                        "end_line": node.end_lineno,
                    }
                )
                visit(node.body, (*parents, node.name))

    visit(ast.parse(SOURCE).body)
    for name in ("counter", "__init__", "broken", "empty"):
        specs.append({"filepath": f"src/pkg/{name}.py", "kind": "file"})
    return specs + specs[:1]


@pytest.mark.parametrize(
    "strategy",
    ["target_probe_ldh", "target_probe_contract_agnostic"],
)
@pytest.mark.parametrize("import_roots", [(), ("src",)])
@pytest.mark.parametrize("generated_roots", [None, [], ["test/local"], ["one", "two"]])
def test_source_packet_matches_formal(
    source_project, strategy, import_roots, generated_roots
):
    kwargs = dict(
        project="fixture",
        strategy=strategy,
        project_root=source_project,
        target_units=unit_specs(),
        python_import_roots=import_roots,
        generated_test_roots=generated_roots,
    )
    actual = target_packets.build_target_packet(**kwargs)
    formal_kwargs = {
        key: value for key, value in kwargs.items() if key != "target_units"
    }
    expected = (
        formal_module("target_packets", "input").build_target_packet(
            **formal_kwargs,
            case_id="counter",
            revision="before",
            repository_url="",
            patch_targets={"target_units": kwargs["target_units"]},
            constraints=formal_module("project", "adapters").constraints_for_strategy(
                strategy
            ),
            test_command=["python", "-m", "pytest"],
        ).to_dict()
    )
    for include_imports in (False, True):
        options = {"include_module_imports": include_imports}
        expected_prompt = formal_module("prompts", "prompt").prompt_packet(
            expected, **options
        )
        expected_prompt.pop("test_command")
        assert json.dumps(prompt_packet(actual, **options)) == json.dumps(
            expected_prompt
        )
    for key in ("packet_id", "case_id", "revision", "repository_url", "test_command"):
        assert key not in actual
        expected.pop(key)
    assert actual == expected
    assert json.dumps(actual) == json.dumps(expected)
    assert len(actual["existing_tests"]) == 2
    assert actual["public_target_routes"]["targets"]


def test_packet_owns_mutable_inputs(source_project):
    shared = ["tests/generated"]
    specs = unit_specs()
    packet = target_packets.build_target_packet(
        project="fixture",
        strategy="target_probe_ldh",
        project_root=source_project,
        target_units=specs,
        generated_test_roots=shared,
    )
    original_specs = json.dumps(specs)
    packet["target_units"][0]["code"] = "changed packet source"
    assert packet["generated_test_roots"] == shared
    packet["generated_test_roots"].append("packet-only")
    assert shared == ["tests/generated"]
    original_constraints = probe_constraints()
    assert packet["constraints"] == original_constraints
    packet["constraints"].append("packet-only")
    assert probe_constraints() == original_constraints
    assert json.dumps(specs) == original_specs


def test_packet_requires_target_units(source_project):
    with pytest.raises(SystemExit, match="case has no target units"):
        target_packets.build_target_packet(
            project="fixture",
            strategy="target_probe_ldh",
            project_root=source_project,
            target_units=[],
        )


def test_prompt_omits_run_metadata_and_execution_command():
    packet = {
        "project": "fixture",
        "case_id": "private-case",
        "revision": "private-revision",
        "repository_url": "https://example.test/private-repo",
        "test_command": ["private-command"],
    }
    payload = prompt_packet(packet)
    assert payload["project"] == "fixture"
    assert not {"case_id", "revision", "repository_url", "test_command"} & payload.keys()


@pytest.mark.parametrize("max_lines", [-1, 0, 1, 2, 80])
def test_packet_excerpts_match_formal(source_project, max_lines):
    files = [
        "src/pkg/counter.py",
        "src/pkg/__init__.py",
        "src/pkg/broken.py",
        "src/pkg/empty.py",
        "missing.py",
        "src/pkg/counter.py",
    ]
    actual = target_packets.module_import_contexts(
        source_project, files, max_lines=max_lines
    )
    expected = formal_module("target_packets", "input").module_import_contexts(
        source_project, files, max_lines=max_lines
    )
    assert json.dumps(actual) == json.dumps([asdict(item) for item in expected])
    actual_index = target_packets.source_file_index(source_project, files)
    expected_index = formal_module("target_units", "input").source_file_index(
        source_project, files
    )
    assert actual_index == [asdict(item) for item in expected_index]


@pytest.mark.parametrize(
    "consumer",
    ["contracts", "imports", "test_match", "routes", "base_class", "context"],
)
@pytest.mark.parametrize("failure", ["syntax", "null_byte", "read_error"])
def test_module_read_failures_match_formal(
    source_project, monkeypatch, consumer, failure
):
    units = target_packets.load_target_units(source_project, unit_specs())
    filepath = "src/pkg/base.py" if consumer == "base_class" else "src/pkg/counter.py"
    target = source_project / filepath
    if failure != "read_error":
        target.write_text("def unfinished(\n" if failure == "syntax" else "\0")
    reads = []
    original = Path.read_text

    def read(path, *args, **kwargs):
        if path == target:
            reads.append((path, args, kwargs))
            if failure == "read_error":
                raise PermissionError("fixture read failed")
        return original(path, *args, **kwargs)

    tree = ast.parse(SOURCE)
    base = next(node for node in tree.body if isinstance(node, ast.ClassDef)).bases[0]

    def run(formal):
        modules = {
            "module_contracts": module_contracts,
            "target_packets": target_packets,
            "public_routes": public_routes,
            "context_index": context_index,
        }
        if formal:
            modules = {
                name: formal_module(
                    name, "prompt" if name == "context_index" else "input"
                )
                for name in modules
            }
        calls = {
            "contracts": lambda: modules["module_contracts"].module_contracts(
                source_project, [filepath]
            ),
            "imports": lambda: modules["target_packets"].module_import_contexts(
                source_project, [filepath]
            ),
            "test_match": lambda: modules["target_packets"].import_match(
                target, units=units
            ),
            "routes": lambda: modules["public_routes"].public_target_routes(
                source_project, units
            ),
            "base_class": lambda: modules["public_routes"].resolve_base_class(
                source_project, "src/pkg/counter.py", "pkg.counter", tree, base
            ),
            "context": lambda: modules["context_index"].build_context_index(
                source_project, ["src"], filepaths=[filepath]
            ),
        }
        reads.clear()
        try:
            return calls[consumer](), list(reads)
        except PermissionError as exc:
            return (type(exc), str(exc)), list(reads)

    monkeypatch.setattr(Path, "read_text", read)
    expected = run(True)
    assert len(expected[1]) == 1
    assert run(False) == expected


@pytest.mark.parametrize("reverse_targets", [False, True])
def test_module_name_matching_matches_formal(tmp_path, reverse_targets):
    paths = [
        "counter.py",
        "pkg/counter.py",
        "pkg/__init__.py",
        "__init__.py",
        "src/pkg/counter.py",
        "lib/pkg/counter.py",
        "src/__init__.py",
        "lib/__init__.py",
        "src/lib/pkg/__init__.py",
        "src/counter.PY",
        "src/counter.pyi",
        "pkg/counter.py",
    ]
    units = [
        SimpleNamespace(filepath=value, unit_id=f"u{index}")
        for index, value in enumerate(paths)
    ]
    if reverse_targets:
        units.reverse()
    formal = formal_module("target_packets", "input")
    actual = target_packets.target_modules(units)
    assert list(actual.items()) == list(formal.target_modules(units).items())
    source = tmp_path / "context.py"
    for text in (
        "import pkg.counter",
        "import src.pkg.counter as subject",
        "import pkg.counter.child",
        "from pkg import counter",
        "from lib.pkg import counter",
        "from src import pkg",
        "from .pkg import counter",
        "import other\nfrom pkg import counter",
    ):
        source.write_text(text)
        assert target_packets.import_match(source, units=units) == formal.import_match(
            source, units=units
        )
    for name in (
        "test_counter.py",
        "counter_test.py",
        "counter_tests.py",
        "test_counter_more.py",
        "test_other.py",
    ):
        assert target_packets.same_stem_units(name, units) == formal.same_stem_units(
            name, units
        )


@pytest.mark.parametrize("reverse_targets", [False, True])
def test_shared_call_graph_matches_formal(source_project, reverse_targets):
    source = """def _leaf(value): return value
def _left(value): return _leaf(value) + _right(value)
def _right(value): return _leaf(value) + _left(value)
def first(value): return _left(value)
def second(value): return _right(value)
def third(value): return _leaf(value)
def fourth(value): return _leaf(value)
def fifth(value): return _leaf(value)
def sixth(value): return _leaf(value)
def outer(value):
    def inner(): return _leaf(value)
    return inner()
class Public:
    def __init__(self): self._hidden(0)
    def run(self, value): return self._hidden(value)
    @staticmethod
    def start(value): return _leaf(value)
    @classmethod
    def create(cls): return cls()
    async def step(self, value): return self._hidden(value)
    def _hidden(self, value): return _leaf(value)
"""
    filepath = "src/pkg/routes.py"
    (source_project / filepath).write_text(source)
    specs = [
        {
            "filepath": filepath,
            "kind": "function",
            "qualname": node.name,
            "start_line": node.lineno,
            "end_line": node.end_lineno,
        }
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    units = target_packets.load_target_units(source_project, specs)
    if reverse_targets:
        units.reverse()
    formal = formal_module("public_routes", "input")
    actual = public_target_routes(source_project, units)
    assert actual == formal.public_target_routes(source_project, units)
    assert any(len(item["entrypoints"]) == 4 for item in actual["targets"])
    for unit, target in zip(units, actual["targets"], strict=True):
        assert public_target_routes(source_project, [unit])["targets"] == [target]


@pytest.mark.parametrize("async_method", [False, True])
@pytest.mark.parametrize(
    "body, calls_hidden, formal_calls_hidden",
    [
        ("return self._hidden(value)", True, True),
        ("return cls._hidden(value)", True, True),
        ("return wrap(self._hidden(wrap(value)))", True, True),
        ("return lambda: self._hidden(value)", True, True),
        ("return [self._hidden(item) for item in values if wrap(item)]", True, True),
        ("def inner(): return self._hidden(value)\nreturn inner()", False, False),
        ("async def inner(): return self._hidden(value)\nreturn inner()", False, False),
        (
            "class Inner:\n    result = self._hidden(value)\nreturn Inner()",
            False,
            False,
        ),
        (
            "if value:\n    def inner(): return self._hidden(value)\nreturn value",
            False,
            False,
        ),
        ("try:\n    return wrap(value)\nfinally:\n    self._hidden(value)", True, True),
    ],
)
def test_scope_traversal_binding_corrections(
    body, calls_hidden, formal_calls_hidden, async_method
):
    prefix = "async def" if async_method else "def"
    tree = ast.parse(
        "def wrap(value): return value\n"
        "class Public:\n"
        f"    {prefix} run(self, value):\n{indent(body, '        ')}\n"
        "    def _hidden(self, value): return wrap(value)\n"
        "    def _unused(self): return self._hidden(0)\n"
    )
    method = tree.body[1].body[0]
    formal = formal_module("public_routes", "input")
    assert (
        public_routes.directly_calls_instance_member(method, "_hidden") == calls_hidden
    )
    assert (
        formal.directly_calls_instance_member(method, "_hidden") == formal_calls_hidden
    )
    actual = public_routes.collect_records(tree, "fixture")
    expected = formal.collect_records(tree, "fixture")
    public_routes.collect_call_edges(actual, tree)
    formal.collect_call_edges(expected)
    if calls_hidden != formal_calls_hidden:
        run = next(record for record in expected if record.qualname == "Public.run")
        hidden = next(
            record for record in expected if record.qualname == "Public._hidden"
        )
        run.calls.remove(hidden.record_id)
    # A nested function captures the enclosing method's actual receiver.
    for record in expected:
        if record.qualname == "Public.run.inner":
            hidden = next(
                item for item in expected if item.qualname == "Public._hidden"
            )
            record.calls.add(hidden.record_id)
    assert [(record.record_id, record.calls) for record in actual] == [
        (record.record_id, record.calls) for record in expected
    ]


@pytest.mark.parametrize("linked", [False, True])
def test_test_context_ranking_matches_formal(source_project, linked):
    if linked:
        (source_project / "test/alias.py").symlink_to("../tests/test_alias.py")
        (source_project / "tests/nested").symlink_to(
            "../test", target_is_directory=True
        )
    units = target_packets.load_target_units(source_project, unit_specs())
    formal = formal_module("target_packets", "input")
    for max_files in [-1, 0, 1, 2, 20]:
        for max_chars in [0, 1, 20, 7000]:
            kwargs = dict(max_files=max_files, max_chars=max_chars)
            actual = target_packets.existing_test_contexts(
                source_project, units, **kwargs
            )
            expected = formal.existing_test_contexts(source_project, units, **kwargs)
            assert actual == [asdict(item) for item in expected]


REQUESTS = [
    ("module_context", "counter.py", ""),
    ("function_definition", "counter.py", "advance"),
    ("class_definition", "counter.py", "Counter"),
    ("function_definition", "counter.py", "Counter.step"),
    ("function_definition", "counter.py", "decorate.wrapped"),
    ("symbol_definition", "counter.py", "Counter.total"),
    ("symbol_definition", "counter.py", "LIMIT"),
    ("symbol_definition", "counter.py", "right"),
    ("symbol_definition", "counter.py", "a"),
    ("symbol_definition", "counter.py", "conditional"),
    ("function_definition", "broken.py", "unfinished"),
    ("module_context", "empty.py", ""),
    ("module_context", "missing.py", ""),
    ("unsupported", "counter.py", "advance"),
    ("function_definition", "counter.py", ""),
]


@pytest.mark.parametrize("limit", [None, 0, 1, 2])
def test_context_request_default_and_explicit_limits(source_project, limit):
    from probe.python.prompt.context_requests import parse_context_requests

    requests = [
        {"kind": kind, "filepath": f"src/pkg/{filename}", "qualname": qualname}
        for kind, filename, qualname in REQUESTS[:2]
    ]
    kwargs = {} if limit is None else {"max_requests": limit}
    expected_count = 1 if limit is None else limit
    parsed, errors = parse_context_requests({"requests": requests}, **kwargs)
    assert len(parsed) == expected_count
    assert bool(errors) is (expected_count < len(requests))

    resolved = context_index.resolve_context_requests(
        project_root=source_project,
        source_roots=["src"],
        requests=requests,
        **kwargs,
    )
    assert resolved["max_requests"] == expected_count
    assert len(resolved["requests"]) == expected_count
    assert [item["kind"] for item in resolved["requests"]] == [
        item["kind"] for item in requests[:expected_count]
    ]
    assert all(item["status"] == "found" for item in resolved["requests"])
    assert len(requests) == 2


@pytest.mark.parametrize("max_lines", [0, 1, 5, 90])
def test_context_resolution_matches_formal(source_project, max_lines):
    requests = [
        {
            "kind": kind,
            "filepath": f"src/pkg/{name}",
            "qualname": qualname,
            "reason": "inspect",
        }
        for kind, name, qualname in REQUESTS
    ]
    requests += [
        {"kind": "module_context", "filepath": name}
        for name in ("elsewhere.py", "../outside.py", "/absolute.py", "", "src/pkg")
    ]
    formal = formal_module("context_index", "prompt")
    for batch in ([request] for request in requests):
        kwargs = dict(
            project_root=source_project,
            source_roots=["src"],
            requests=batch,
            max_requests=1,
            max_module_lines=max_lines,
        )
        assert context_index.resolve_context_requests(
            **kwargs
        ) == formal.resolve_context_requests(**kwargs)
    kwargs = dict(
        project_root=source_project,
        source_roots=["src"],
        requests=requests,
        max_requests=len(requests),
        max_total_lines=max_lines,
        max_module_lines=90,
    )
    assert context_index.resolve_context_requests(
        **kwargs
    ) == formal.resolve_context_requests(**kwargs)


@pytest.mark.parametrize("max_requests", [-1, 0, 1, 20])
@pytest.mark.parametrize("max_lines", [0, 3, 90])
def test_request_index_normalizes_once(
    source_project, tmp_path_factory, monkeypatch, max_requests, max_lines
):
    outside = tmp_path_factory.mktemp("outside-context") / "outside.py"
    outside.write_text("def advance(value): return value + 100\n")
    (source_project / "src/escape.py").symlink_to(outside)
    (source_project / "src/alias.py").symlink_to("pkg/counter.py")
    (source_project / "src/notes.txt").write_text("plain module context\n")
    requests = [
        {"kind": "function_definition", "filepath": filepath, "qualname": "advance"}
        for filepath in (
            " src/./pkg//counter.py ",
            "src/pkg/base.py",
            "src/pkg/counter.py",
            "src/alias.py",
            "src/escape.py",
            "src/pkg/broken.py",
            "elsewhere.py",
            "../outside.py",
            "/absolute.py",
            None,
            123,
        )
    ] + [{"kind": "module_context", "filepath": "src/notes.txt"}]
    original_requests = json.dumps(requests)
    formal = formal_module("context_index", "prompt")
    kwargs = dict(
        project_root=source_project,
        source_roots=["src"],
        requests=requests,
        max_requests=max_requests,
        max_total_lines=max_lines,
    )
    expected = formal.resolve_context_requests(**kwargs)
    expected_index = formal.build_context_index(
        source_project,
        ["src"],
        filepaths=formal.request_filepaths(requests[:max_requests], ["src"]),
    )
    indexed_files = []
    add_symbols = context_index.add_module_symbols

    def observe(index, filepath, body, *, parents):
        if not parents:
            indexed_files.append(filepath)
        add_symbols(index, filepath, body, parents=parents)

    monkeypatch.setattr(context_index, "add_module_symbols", observe)
    assert context_index.resolve_context_requests(**kwargs) == expected
    assert indexed_files == sorted({key[0] for key in expected_index})
    assert json.dumps(requests) == original_requests


def assert_traceback_excerpt(actual, previous, *, path, line, max_lines):
    """Preserve the reference result except when its window omits a valid frame."""
    lines = path.read_text().splitlines()
    if (
        max_lines <= 0
        or previous["start_line"] <= line <= previous["end_line"]
        or not 1 <= line <= len(lines)
    ):
        assert actual == previous
        return
    excerpt_fields = {"code", "start_line", "end_line", "line_count"}
    assert {k: v for k, v in actual.items() if k not in excerpt_fields} == {
        k: v for k, v in previous.items() if k not in excerpt_fields
    }
    start, end = actual["start_line"], actual["end_line"]
    assert start <= line <= end
    assert end - start + 1 == actual["line_count"] <= max_lines
    assert [row.split(": ", 1)[1] for row in actual["code"].splitlines()] == lines[start - 1:end]


@pytest.mark.parametrize("function", ["def run():", "async def run():"])
@pytest.mark.parametrize("max_lines", [1, 5, 90])
@pytest.mark.parametrize("line", [522, 530, 610, 630, 671])
def test_traceback_long_function_includes_failing_line(tmp_path, function, max_lines, line):
    path = tmp_path / "subject.py"
    path.write_text("# padding\n" * 520 + function + "\n" + "    value = 1\n" * 149 + "    raise ValueError(value)\n")
    contexts = context_index.project_traceback_context(
        project_root=tmp_path,
        source_roots=["."],
        failure_text=f'  File "{path}", line {line}, in run\n',
        max_lines=max_lines,
    )
    assert len(contexts) == 1
    context = contexts[0]
    assert 521 <= context["start_line"] <= line <= context["end_line"] <= 671
    assert context["line_count"] == max_lines
    assert any(row.lstrip().startswith(f"{line}: ") for row in context["code"].splitlines())
    if line < 521 + max_lines:
        assert context["start_line"] == 521


@pytest.mark.parametrize("max_lines", [1, 3, 90])
def test_traceback_module_window_includes_failing_line(tmp_path, max_lines):
    path = tmp_path / "subject.py"
    path.write_text("value = 1\n" * 100)
    context = context_index.traceback_frame_context(
        tmp_path, {}, path.name, 50, "<module>", max_lines=max_lines
    )
    assert context["start_line"] <= 50 <= context["end_line"]
    assert 0 < context["line_count"] <= max_lines
    assert any(row.lstrip().startswith("50: ") for row in context["code"].splitlines())


@pytest.mark.parametrize("max_frames", [0, 1, 3])
@pytest.mark.parametrize("max_lines", [0, 3, 90])
def test_traceback_context_preserves_unique_frame_selection(
    source_project, max_frames, max_lines
):
    text = f'''Traceback (most recent call last):
  File "{source_project}/src/pkg/base.py", line 3, in run
  File "src/pkg/counter.py", line 18, in advance
  File "src/pkg/counter.py", line 34, in step
src/pkg/counter.py:34: in step
src/pkg/counter.py:34: AssertionError: arithmetic fixture
ImportError: cannot import name missing ({source_project}/src/pkg/counter.py)
'''
    kwargs = dict(
        project_root=source_project,
        source_roots=["src"],
        failure_text=text,
        max_frames=max_frames,
        max_lines=max_lines,
    )
    formal = formal_module("context_index", "prompt")
    actual = context_index.project_traceback_context(**kwargs)
    previous = formal.project_traceback_context(**kwargs)
    frames = context_index.project_frames(
        text, project_root=source_project, source_roots=["src"], max_frames=max_frames
    )
    assert len(frames) == len({(frame.filepath, frame.line) for frame in frames})
    assert len(actual) == len(previous) == len(frames)
    for current, old, frame in zip(actual, previous, frames):
        assert_traceback_excerpt(
            current, old, path=source_project / frame.filepath,
            line=frame.line, max_lines=max_lines,
        )


@pytest.mark.parametrize("max_lines", [0, 1, 5, 90])
def test_traceback_index_and_excerpts_match_formal(source_project, max_lines):
    formal = formal_module("context_index", "prompt")
    filepath = "src/pkg/counter.py"
    kwargs = dict(filepaths=[filepath, filepath, "src/pkg/broken.py", "../outside.py"])
    actual = context_index.build_context_index(source_project, ["src"], **kwargs)
    expected = formal.build_context_index(source_project, ["src"], **kwargs)
    assert len(actual) * 2 == len(expected)
    assert {k: asdict(v) for k, v in actual.items()} == {
        k: {"qualname": v.qualname, "start_line": v.start_line, "end_line": v.end_line}
        for k, v in expected.items()
        if k[2].endswith("_definition")
    }
    for line in (1, 10, 12, 18, 21, 24, 34, 40, 99):
        for function in ("<module>", "step", "Counter.step", "unknown"):
            current = context_index.traceback_frame_context(
                source_project, actual, filepath, line, function, max_lines=max_lines
            )
            previous = formal.traceback_frame_context(
                source_project, expected, filepath, line, function, max_lines=max_lines
            )
            assert_traceback_excerpt(
                current, previous, path=source_project / filepath, line=line, max_lines=max_lines
            )


@pytest.mark.parametrize("max_lines", [0, 1, 90])
def test_context_index_redefinitions_match_formal(tmp_path, max_lines):
    filepath = "subject.py"
    text = """left = right = 1
left: int = 2
class Subject:
    value = 3
    def run(self):
        def nested(): return 1
        return nested()
    async def run(self): return 2
def Subject():
    class Nested:
        def run(self): return 3
    return Nested()
"""
    (tmp_path / filepath).write_text(text)
    formal = formal_module("context_index", "prompt")
    actual = context_index.build_context_index(tmp_path, ["."], filepaths=[filepath])
    expected = formal.build_context_index(tmp_path, ["."], filepaths=[filepath])
    assert len(actual) * 2 == len(expected)
    for path, qualname, kind in expected:
        kwargs = dict(
            project_root=tmp_path,
            source_roots=["."],
            request={"filepath": path, "qualname": qualname, "kind": kind},
            max_lines=max_lines,
        )
        assert context_index.resolve_context_request(
            **kwargs, index=actual
        ) == formal.resolve_context_request(**kwargs, index=expected)
    for line in range(1, len(text.splitlines()) + 2):
        for function in ("<module>", "run", "Subject", "Subject.run", "nested"):
            current = context_index.traceback_frame_context(
                tmp_path, actual, filepath, line, function, max_lines=max_lines
            )
            previous = formal.traceback_frame_context(
                tmp_path, expected, filepath, line, function, max_lines=max_lines
            )
            assert_traceback_excerpt(
                current, previous, path=tmp_path / filepath, line=line, max_lines=max_lines
            )
