"""Compare model-visible context and traceback excerpts with the formal broker."""

import importlib
import os
from dataclasses import asdict
from pathlib import Path

import pytest

from augment.python.models import ContextRequest
from augment.python.prompt import context


SOURCE = """VALUE = 3
def decorate(value): return value

@decorate
class Counter:
    @staticmethod
    def start(value): return value + 1

    async def step(self, value):
        if value:
            def nested(): return value
            return nested()
        return 0

def outer():
    class Inner:
        def run(self): return 1
    return Inner()

def repeated(): return 1
def repeated(): return 2
"""


@pytest.fixture(scope="module")
def formal_context():
    root = os.environ.get("AUGMENT_FORMAL_ROOT") or os.environ.get("PROBE_FORMAL_ROOT")
    if not root:
        pytest.skip("set AUGMENT_FORMAL_ROOT for reference checks")
    import common

    directory = str(Path(root) / "src/common")
    if directory not in common.__path__:
        common.__path__.append(directory)
    return importlib.import_module("common.test_augmentF.python.prompt.context")


@pytest.fixture
def project(tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    for name, text in {
        "counter.py": SOURCE,
        "empty.py": "",
        "invalid.py": "def broken(\n",
        "long.py": "def long():\n" + "    value = 1\n" * 140,
        "notes.txt": "ordinary text\n",
    }.items():
        (source / name).write_text(text)
    (tmp_path / "outside.py").write_text("def outside(): return 1\n")
    (source / "alias.py").symlink_to("counter.py")
    (source / "outside.py").symlink_to("../outside.py")
    return tmp_path


@pytest.mark.parametrize("source", [SOURCE, "", "def broken(\n", "\0"])
def test_definition_index_matches_formal(formal_context, source):
    def records(module):
        return {
            name: [asdict(record) for record in values]
            for name, values in module.definitions_for_file(
                "src/counter.py", source
            ).items()
        }

    assert records(context) == records(formal_context)


@pytest.mark.parametrize("budget", [-2, 0, 1, 3, 90, 500])
def test_broker_resolution_matches_formal(project, formal_context, budget):
    requests = [
        ContextRequest(kind=kind, filepath="src/counter.py", qualname=qualname)
        for kind in (
            "module_context",
            "class_definition",
            "function_definition",
            "symbol_definition",
            "unknown",
        )
        for qualname in (
            "",
            "Counter",
            "Counter.step",
            "Counter.step.nested",
            "outer.Inner.run",
            "repeated",
            "VALUE",
            "missing",
        )
    ]
    requests += [
        ContextRequest(
            kind="module_context", filepath=filepath, start_line=start, end_line=end
        )
        for filepath in (
            "src/counter.py",
            "src/empty.py",
            "src/invalid.py",
            "src/alias.py",
            "src/outside.py",
            "src/notes.txt",
            "src/missing.py",
            "src",
            "outside.py",
            "../outside.py",
            "/absolute.py",
            "",
            "src//counter.py",
        )
        for start, end in ((None, None), (2, 1), (1, 5), (100, 120))
    ]
    requests += [
        ContextRequest(
            kind="function_definition",
            filepath="src/counter.py",
            qualname="repeated",
            start_line=start,
            end_line=end,
        )
        for start, end in ((20, 20), (21, 21), (20, 21), (21, None), (None, 20))
    ]
    actual = context.ContextBroker(project, ["src"])
    expected = formal_context.ContextBroker(project, ["src"])
    for request in requests:
        assert (
            actual.resolve(request, line_budget=budget).to_dict()
            == expected.resolve(request, line_budget=budget).to_dict()
        )
    batch = requests + requests[:3]
    assert actual.resolve_batch(batch) == expected.resolve_batch(batch)


@pytest.mark.parametrize("budget", [-1, 0, 1, 4, 90, 200])
def test_traceback_frame_windows_match_formal(project, formal_context, budget):
    actual = context.ContextBroker(project, ["src"])
    expected = formal_context.ContextBroker(project, ["src"])
    for filepath in (
        "src/counter.py",
        "src/long.py",
        "src/invalid.py",
        "src/empty.py",
        "src/missing.py",
    ):
        for line in (1, 4, 6, 10, 14, 19, 21, 70, 141, 200):
            for function in ("", "step", "<module>"):
                assert (
                    actual.resolve_frame(
                        filepath, line, function, line_budget=budget
                    ).to_dict()
                    == expected.resolve_frame(
                        filepath, line, function, line_budget=budget
                    ).to_dict()
                )
    failure = f'''Traceback (most recent call last):
  File "{project}/src/counter.py", line 10, in step
  File "{project}/src/long.py", line 70, in long
  File "{project}/src/counter.py", line 21, in repeated
AssertionError: fixture
'''
    assert context.project_traceback_context(
        failure, actual
    ) == formal_context.project_traceback_context(failure, expected)


def test_read_failures_match_formal(project, formal_context, monkeypatch):
    read = Path.read_text

    def denied(path, *args, **kwargs):
        if path.name == "counter.py":
            raise PermissionError("fixture")
        return read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", denied)
    request = ContextRequest(
        kind="function_definition", filepath="src/counter.py", qualname="Counter.step"
    )
    assert (
        context.ContextBroker(project, ["src"]).resolve(request).to_dict()
        == formal_context.ContextBroker(project, ["src"]).resolve(request).to_dict()
    )
