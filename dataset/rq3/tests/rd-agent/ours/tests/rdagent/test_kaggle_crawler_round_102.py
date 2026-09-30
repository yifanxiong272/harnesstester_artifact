import types
import pytest

import rdagent.scenarios.kaggle.kaggle_crawler as kc

# Deterministic fake Path implementation to avoid any filesystem I/O.
class FakePath:
    def __init__(self, path_str, is_file=False, file_content=None, nb_cells=None, storage=None):
        self.path_str = path_str
        self.is_file = is_file
        self.file_content = file_content
        self.nb_cells = nb_cells or []
        # shared dict where write_text stores results
        self.storage = storage if storage is not None else {}

    # emulate Path.glob on the base directory by pattern matching
    def glob(self, pattern):
        # Patterns expected: "**/*.ipynb", "**/*.irnb", "**/*.py"
        if pattern.endswith("*.ipynb"):
            # find any FakePath children whose suffix is .ipynb
            return [p for p in getattr(self, "children", []) if p.path_str.endswith(".ipynb")]
        if pattern.endswith("*.irnb"):
            return [p for p in getattr(self, "children", []) if p.path_str.endswith(".irnb")]
        if pattern.endswith("*.py"):
            return [p for p in getattr(self, "children", []) if p.path_str.endswith(".py")]
        return []

    # return a context manager compatible with 'with path.open("r", encoding="utf-8") as f:'
    def open(self, mode="r", encoding=None):
        class DummyCM:
            def __init__(self, parent):
                self.parent = parent
            def __enter__(self):
                # For .read() usage (py files)
                class F:
                    def __init__(self, content):
                        self._content = content
                    def read(self):
                        return self._content
                return F(self.parent.file_content)
            def __exit__(self, exc_type, exc, tb):
                return False
        return DummyCM(self)

    def with_suffix(self, suffix):
        # return a new FakePath that will record write_text into shared storage
        new_path = FakePath(self.path_str.rsplit(".", 1)[0] + suffix, is_file=True, storage=self.storage)
        # also supply children attribute for consistency
        new_path.children = getattr(self, "children", [])
        return new_path

    def write_text(self, text, encoding=None):
        # store the content keyed by the path string
        self.storage[self.path_str] = text

    def __repr__(self):
        return f"FakePath({self.path_str})"


def setup_fake_environment(monkeypatch, nb_file_defs=None, py_file_defs=None):
    """
    Prepare a FakePath base object and patch kc.Path to return it.
    nb_file_defs: list of dicts with keys (name, cells)
    py_file_defs: list of dicts with keys (name, content)
    Returns (storage_dict, base_fake)
    """
    storage = {}

    # base path that will return children from glob
    base = FakePath("/fake/base")
    children = []

    nb_file_defs = nb_file_defs or []
    for nb_def in nb_file_defs:
        p = FakePath(f"/fake/base/{nb_def['name']}", is_file=True, nb_cells=nb_def.get("cells", []), storage=storage)
        children.append(p)

    py_file_defs = py_file_defs or []
    for py_def in py_file_defs:
        p = FakePath(f"/fake/base/{py_def['name']}", is_file=True, file_content=py_def.get("content", ""), storage=storage)
        children.append(p)

    base.children = children

    # Patch the Path symbol in the module under test so Path(...) returns our base.
    def fake_path_ctor(path_str):
        # ignore the provided path string, always return the same base container
        return base

    monkeypatch.setattr(kc, "Path", fake_path_ctor)

    return storage, base


def test_convert_notebooks_markdown_code_round_102(monkeypatch, capsys):
    # Notebook with one markdown and one code cell -> should build both wrapped sections and be converted
    nb_cells = [
        {"cell_type": "markdown", "source": "# Title"},
        {"cell_type": "code", "source": "print(1)"},
    ]

    storage, base = setup_fake_environment(monkeypatch, nb_file_defs=[{"name": "nb1.ipynb", "cells": nb_cells}], py_file_defs=[])

    # Patch nbformat.read to return an object with .cells equal to our nb_cells as objects with attributes
    def fake_nbformat_read(f, as_version):
        return types.SimpleNamespace(cells=[types.SimpleNamespace(**cell) for cell in nb_cells])

    monkeypatch.setattr(kc.nbformat, "read", fake_nbformat_read)

    # Capture calls to notebook_to_knowledge and return deterministic transformed text
    received_args = []

    def fake_notebook_to_knowledge(text):
        received_args.append(text)
        return "CONVERTED:" + text

    monkeypatch.setattr(kc, "notebook_to_knowledge", fake_notebook_to_knowledge)

    # Run function under test
    kc.convert_notebooks_to_text("competition", "local_path")

    # Assert notebook_to_knowledge received the expected joined markdown+code wrappers
    expected_input = "```markdown\n# Title```\n\n```code\nprint(1)```"
    assert received_args == [expected_input]

    # The storage should contain a .txt file for the notebook with the converted content
    expected_txt_path = "/fake/base/nb1.txt"
    assert expected_txt_path in storage
    assert storage[expected_txt_path] == "CONVERTED:" + expected_input

    # Printout should indicate 1 converted notebook
    captured = capsys.readouterr()
    assert "Converted 1 notebooks to text files." in captured.out


def test_convert_notebooks_raw_and_py_round_102(monkeypatch, capsys):
    # Notebook with a raw cell (neither markdown nor code) -> produces empty interim text
    # plus a python file to exercise the py branch
    nb_cells = [
        {"cell_type": "raw", "source": "some raw content"},
    ]
    py_content = "def foo():\n    return 'bar'\n"

    storage, base = setup_fake_environment(
        monkeypatch,
        nb_file_defs=[{"name": "nb2.ipynb", "cells": nb_cells}],
        py_file_defs=[{"name": "script.py", "content": py_content}],
    )

    # nbformat.read returns the notebook object with the raw cell as an object with attributes
    def fake_nbformat_read(f, as_version):
        return types.SimpleNamespace(cells=[types.SimpleNamespace(**cell) for cell in nb_cells])

    monkeypatch.setattr(kc.nbformat, "read", fake_nbformat_read)

    # notebook_to_knowledge should be invoked twice: once for the empty notebook text, once for the py file text
    received = []

    def fake_notebook_to_knowledge(text):
        received.append(text)
        return "K:" + text

    monkeypatch.setattr(kc, "notebook_to_knowledge", fake_notebook_to_knowledge)

    # Run
    kc.convert_notebooks_to_text("competition", "local_path")

    # For the raw cell notebook, the joined text list will be empty string
    assert received[0] == ""

    # For the py file, the input should be a code block wrapping the file content
    assert received[1] == f"```code\n{py_content}```"

    # Both outputs should have been written to storage
    assert "/fake/base/nb2.txt" in storage and storage["/fake/base/nb2.txt"] == "K:"
    assert "/fake/base/script.txt" in storage and storage["/fake/base/script.txt"] == "K:```code\n" + py_content + "```"

    # Printed count should be 2
    captured = capsys.readouterr()
    assert "Converted 2 notebooks to text files." in captured.out
