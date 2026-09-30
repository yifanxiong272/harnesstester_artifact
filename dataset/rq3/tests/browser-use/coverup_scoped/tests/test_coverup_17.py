# file: browser_use/cli.py:2259-2364
# asked: {"lines": [2259, 2260, 2261, 2262, 2263, 2264, 2266, 2267, 2268, 2269, 2270, 2272, 2273, 2274, 2275, 2276, 2278, 2279, 2280, 2281, 2282, 2283, 2285, 2286, 2287, 2288, 2289, 2314, 2315, 2316, 2317, 2318, 2321, 2322, 2323, 2324, 2325, 2327, 2328, 2329, 2330, 2334, 2337, 2338, 2340, 2343, 2344, 2345, 2346, 2347, 2348, 2349, 2350, 2353, 2354, 2355, 2356, 2357, 2358, 2359, 2360, 2361, 2362, 2364], "branches": [[2314, 2315], [2314, 2321], [2316, 2317], [2316, 2318], [2321, 2322], [2321, 2334], [2323, 2324], [2323, 2325], [2337, 2338], [2337, 2340], [2353, 2354], [2353, 2364]]}
# gained: {"lines": [2259, 2260, 2261, 2262, 2263, 2264, 2266, 2267, 2268, 2269, 2270, 2272, 2273, 2274, 2275, 2276, 2278, 2279, 2280, 2281, 2282, 2283, 2285, 2286, 2287, 2314, 2315, 2316, 2317, 2318, 2321, 2322, 2323, 2324, 2325, 2327, 2328, 2329, 2330, 2334, 2337, 2340, 2343, 2344, 2345, 2346, 2347, 2348, 2349, 2350, 2353, 2354, 2355, 2356, 2357, 2358, 2359, 2360, 2361, 2362, 2364], "branches": [[2314, 2315], [2314, 2321], [2316, 2317], [2316, 2318], [2321, 2322], [2321, 2334], [2323, 2324], [2323, 2325], [2337, 2340], [2353, 2354], [2353, 2364]]}

import sys
from pathlib import Path
import pytest
import click

import browser_use.cli as cli


def test_list_templates_prints_available(monkeypatch, capsys):
    # Arrange: set INIT_TEMPLATES to known small mapping
    monkeypatch.setattr(cli, "INIT_TEMPLATES", {
        "default": {"description": "Default template", "file": "default.txt"},
        "advanced": {"description": "Advanced template", "file": "advanced.txt"},
    })

    # Act: call underlying callback with list_templates True
    cli.init.callback(template=None, output=None, force=False, list_templates=True)

    # Assert: stdout contains the listed templates and descriptions
    captured = capsys.readouterr()
    out = captured.out
    assert "Available templates" in out
    assert "default" in out and "Default template" in out
    assert "advanced" in out and "Advanced template" in out


def test_interactive_prompt_reads_template_and_writes_success(tmp_path, monkeypatch, capsys):
    # Arrange
    # Point module __file__ to a fake location inside tmp_path so templates_dir is controlled
    fake_module_file = tmp_path / "fake_module.py"
    fake_module_file.write_text("# fake")
    monkeypatch.setattr(cli, "__file__", str(fake_module_file))

    # Create cli_templates dir and a template file
    templates_dir = tmp_path / "cli_templates"
    templates_dir.mkdir()
    template_filename = "default_template.txt"
    template_path = templates_dir / template_filename
    template_content = "# example template content\nprint('hello')\n"
    template_path.write_text(template_content, encoding="utf-8")

    # Set INIT_TEMPLATES to refer to that filename
    monkeypatch.setattr(cli, "INIT_TEMPLATES", {
        "default": {"description": "Default template", "file": template_filename},
        "advanced": {"description": "Advanced template", "file": "advanced.txt"},
    })

    # Simulate interactive prompt returning 'default'
    monkeypatch.setattr(click, "prompt", lambda *a, **k: "default")

    # Mock the internal _write_init_file to avoid actual file writes; return True to hit success branch
    monkeypatch.setattr(cli, "_write_init_file", lambda output_path, content, force: True)

    # Act: call the underlying callback
    cli.init.callback(template=None, output=None, force=False, list_templates=False)

    # Assert: printed success messages and next steps, and uses default output filename
    captured = capsys.readouterr()
    out = captured.out
    assert "✅ Created" in out
    assert "Next steps" in out
    assert "Install browser-use" in out
    # Output filename should be browser_use_default.py as per code when output is None
    assert "python browser_use_default.py" in out


def test_interactive_prompt_write_failure_exits(tmp_path, monkeypatch):
    # Arrange similar to success case but make _write_init_file return False
    fake_module_file = tmp_path / "fake_module2.py"
    fake_module_file.write_text("# fake")
    monkeypatch.setattr(cli, "__file__", str(fake_module_file))

    templates_dir = tmp_path / "cli_templates"
    templates_dir.mkdir()
    template_filename = "default_template2.txt"
    (templates_dir / template_filename).write_text("content", encoding="utf-8")

    monkeypatch.setattr(cli, "INIT_TEMPLATES", {
        "default": {"description": "Default template", "file": template_filename},
    })

    monkeypatch.setattr(click, "prompt", lambda *a, **k: "default")

    monkeypatch.setattr(cli, "_write_init_file", lambda output_path, content, force: False)

    # Act / Assert: expect SystemExit with code 1 when calling underlying callback
    with pytest.raises(SystemExit) as excinfo:
        cli.init.callback(template=None, output=None, force=False, list_templates=False)
    assert excinfo.value.code == 1


def test_read_template_error_prints_and_exits(tmp_path, monkeypatch, capsys):
    # Arrange: point __file__ to tmp_path but do NOT create the template file to force read_text error
    fake_module_file = tmp_path / "fake_module3.py"
    fake_module_file.write_text("# fake")
    monkeypatch.setattr(cli, "__file__", str(fake_module_file))

    # INIT_TEMPLATES points to a non-existent file
    monkeypatch.setattr(cli, "INIT_TEMPLATES", {
        "default": {"description": "Default template", "file": "does_not_exist.txt"},
    })

    # Act / Assert: SystemExit raised and error message printed to stderr when calling underlying callback
    with pytest.raises(SystemExit) as excinfo:
        cli.init.callback(template="default", output=None, force=False, list_templates=False)

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    # click.echo(..., err=True) writes to stderr
    assert "❌ Error reading template" in captured.err
