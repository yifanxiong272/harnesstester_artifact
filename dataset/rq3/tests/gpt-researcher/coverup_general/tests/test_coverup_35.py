# file: cli.py:209-245
# asked: {"lines": [209, 210, 211, 212, 213, 214, 220, 222, 224, 225, 226, 228, 229, 230, 231, 232, 233, 234, 235, 237, 238, 239, 240, 241, 242, 243, 244, 245], "branches": [[237, 238], [237, 240]]}
# gained: {"lines": [209, 213, 220, 222, 224, 225, 226, 228, 229, 230, 231, 232, 233, 234, 235, 237, 238, 239, 240, 241, 242, 243, 244, 245], "branches": [[237, 238], [237, 240]]}

import argparse
import importlib.util
import re
from pathlib import Path

import pytest


def _load_cli_module():
    """Locate and load the cli.py module from the repository.

    Checks common locations for the module file.
    """
    candidates = [
        Path("gpt_researcher") / "cli.py",
        Path("gpt-researcher") / "cli.py",
        Path("gpt_researcher.py"),
    ]
    for p in candidates:
        if p.exists():
            spec = importlib.util.spec_from_file_location("test_gpt_researcher_cli_module", p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore
            return mod
    for p in Path(".").rglob("cli.py"):
        if "site-packages" in str(p) or ".venv" in str(p):
            continue
        spec = importlib.util.spec_from_file_location("test_gpt_researcher_cli_module", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
        return mod
    raise FileNotFoundError("Could not locate cli.py for gpt_researcher/gpt-researcher")


class DummyResearcher:
    def __init__(self, visited_urls, cost):
        self.visited_urls = visited_urls
        self._cost = cost

    def get_costs(self):
        return self._cost


class _FixedNowObj:
    def __init__(self, iso_value):
        self._iso = iso_value

    def isoformat(self, timespec="seconds"):
        return self._iso


class _FixedDatetime:
    def __init__(self, iso_value):
        self._iso_value = iso_value

    def now(self):
        return _FixedNowObj(self._iso_value)


def test_build_frontmatter_with_domains_and_researcher(monkeypatch):
    mod = _load_cli_module()
    assert hasattr(mod, "_build_frontmatter"), "cli.py does not define _build_frontmatter"
    build = getattr(mod, "_build_frontmatter")

    fixed_iso = "2020-01-02T03:04:05"
    monkeypatch.setattr(mod, "datetime", _FixedDatetime(fixed_iso), raising=True)

    args = argparse.Namespace(
        query='find "something" \\path',
        report_type='summary',
        report_source='web',
        tone='neutral',
        query_domains="example.com,,sub.example"
    )

    researcher = DummyResearcher(visited_urls=["a", "b", "c"], cost=1.23456789)

    out = build("task-123", 'Title "special" \\x', args, researcher)

    # Basic content checks
    assert out.startswith("---\n")
    assert 'task_id: "task-123"' in out
    assert 'title: "Title \\"special\\" \\\\x"' in out
    assert 'query: "find \\"something\\" \\\\path"' in out
    assert 'report_type: "summary"' in out
    assert 'report_source: "web"' in out
    assert 'tone: "neutral"' in out

    # Domains block and entries
    assert "query_domains:" in out
    assert '  - "example.com"' in out
    assert '  - "sub.example"' in out
    assert '  - ""' not in out

    # created_at field present and matches fixed ISO
    assert f'created_at: "{fixed_iso}"' in out

    # counts and costs
    assert "sources_count: 3" in out
    assert "total_cost_usd: 1.234568" in out

    # Ensure there are two '---' markers (opening and closing)
    assert out.count("---") >= 2


def test_build_frontmatter_without_researcher_and_no_domains(monkeypatch):
    mod = _load_cli_module()
    build = getattr(mod, "_build_frontmatter")

    fixed_iso = "2021-12-31T23:59:59"
    monkeypatch.setattr(mod, "datetime", _FixedDatetime(fixed_iso), raising=True)

    args = argparse.Namespace(
        query="simple query",
        report_type="full",
        report_source="local",
        tone="formal",
        query_domains=""
    )

    researcher = None

    out = build("tid", "A title", args, researcher)

    # Basic content checks
    assert out.startswith("---\n")
    assert f'created_at: "{fixed_iso}"' in out

    # No domains block
    assert "query_domains:" not in out
    assert "  - " not in out

    # sources_count and total_cost_usd when researcher is None
    assert "sources_count: 0" in out
    assert re.search(r"total_cost_usd:\s*0(\.0+)?", out)

    # Other fields present
    assert 'task_id: "tid"' in out
    assert 'title: "A title"' in out
    assert 'query: "simple query"' in out
    assert 'report_type: "full"' in out
    assert 'report_source: "local"' in out
    assert 'tone: "formal"' in out

    # Ensure there are two '---' markers (opening and closing)
    assert out.count("---") >= 2
