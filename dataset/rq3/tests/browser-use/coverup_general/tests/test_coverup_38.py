# file: browser_use/cli.py:2259-2364
# asked: {"lines": [2259, 2260, 2261, 2262, 2263, 2264, 2266, 2267, 2268, 2269, 2270, 2272, 2273, 2274, 2275, 2276, 2278, 2279, 2280, 2281, 2282, 2283, 2285, 2286, 2287, 2288, 2289, 2314, 2315, 2316, 2317, 2318, 2321, 2322, 2323, 2324, 2325, 2327, 2328, 2329, 2330, 2334, 2337, 2338, 2340, 2343, 2344, 2345, 2346, 2347, 2348, 2349, 2350, 2353, 2354, 2355, 2356, 2357, 2358, 2359, 2360, 2361, 2362, 2364], "branches": [[2314, 2315], [2314, 2321], [2316, 2317], [2316, 2318], [2321, 2322], [2321, 2334], [2323, 2324], [2323, 2325], [2337, 2338], [2337, 2340], [2353, 2354], [2353, 2364]]}
# gained: {"lines": [2259, 2260, 2261, 2262, 2263, 2264, 2266, 2267, 2268, 2269, 2270, 2272, 2273, 2274, 2275, 2276, 2278, 2279, 2280, 2281, 2282, 2283, 2285, 2286, 2287, 2314, 2315, 2316, 2317, 2318, 2321, 2322, 2323, 2324, 2325, 2327, 2328, 2329, 2330, 2334, 2337, 2338, 2340, 2343, 2344, 2345, 2346, 2347, 2348, 2349, 2350, 2353, 2354, 2355, 2356, 2357, 2358, 2359, 2360, 2361, 2362, 2364], "branches": [[2314, 2315], [2314, 2321], [2316, 2317], [2316, 2318], [2321, 2322], [2321, 2334], [2323, 2324], [2323, 2325], [2337, 2338], [2337, 2340], [2353, 2354], [2353, 2364]]}

import pathlib
import sys
import click
from click.testing import CliRunner
import browser_use.cli as cli
import pytest


def _make_fake_path_for_module(tmp_parent_path, module_file):
    """
    Return a fake Path callable that:
    - When called with module_file returns an object whose .parent is tmp_parent_path (a pathlib.Path)
    - Otherwise delegates to the real pathlib.Path
    Also exposes cwd as pathlib.Path.cwd so code that calls Path.cwd() continues to work.
    """
    real_Path = pathlib.Path

    def fake_Path(arg=None):
        # When called as Path(__file__) inside the module, return an object with .parent = tmp_parent_path
        if arg == module_file:
            class M:
                pass
            m = M()
            m.parent = tmp_parent_path
            return m
        # Delegate other calls to the real pathlib.Path
        if arg is None:
            return real_Path()
        return real_Path(arg)

    # Provide cwd attribute used as classmethod in code
    fake_Path.cwd = real_Path.cwd
    return fake_Path


def test_init_list_templates(monkeypatch):
    runner = CliRunner()
    # Prepare a simple INIT_TEMPLATES mapping
    templates = {
        'default': {'description': 'Default template', 'file': 'default.py'},
        'advanced': {'description': 'Advanced template', 'file': 'advanced.py'},
        'tools': {'description': 'Tools template', 'file': 'tools.py'},
    }
    monkeypatch.setattr(cli, 'INIT_TEMPLATES', templates)

    result = runner.invoke(cli.main, ['init', '--list'])
    assert result.exit_code == 0
    out = result.output
    assert 'Available templates:' in out
    # Check that each template name and description is printed
    assert 'default' in out
    assert 'Default template' in out
    assert 'advanced' in out
    assert 'Advanced template' in out
    assert 'tools' in out
    assert 'Tools template' in out


def test_init_interactive_prompt_and_write_success(tmp_path, monkeypatch):
    runner = CliRunner()

    # Create cli_templates directory and a default template file
    templates_dir = tmp_path / 'cli_templates'
    templates_dir.mkdir()
    default_file = templates_dir / 'default.py'
    content = "# sample template\nprint('hello')\n"
    default_file.write_text(content, encoding='utf-8')

    # Set INIT_TEMPLATES to point to the file name
    templates = {
        'default': {'description': 'Default template', 'file': 'default.py'},
        'advanced': {'description': 'Advanced template', 'file': 'advanced.py'},
        'tools': {'description': 'Tools template', 'file': 'tools.py'},
    }
    monkeypatch.setattr(cli, 'INIT_TEMPLATES', templates)

    # Monkeypatch Path used inside cli to ensure Path(__file__).parent is tmp_path
    fake_Path = _make_fake_path_for_module(tmp_path, cli.__file__)
    monkeypatch.setattr(cli, 'Path', fake_Path)

    # Capture _write_init_file calls and assert proper args, then return True (success)
    captured = {}

    def fake_write_init_file(output_path, c, force_flag):
        # output_path will be a pathlib.Path if Path was used for non-module strings
        captured['output_name'] = getattr(output_path, 'name', None)
        captured['content'] = c
        captured['force'] = force_flag
        return True

    monkeypatch.setattr(cli, '_write_init_file', fake_write_init_file)

    # Run interactive init: no --template provided so prompt occurs. Provide blank input to select default.
    result = runner.invoke(cli.main, ['init'], input='\n')
    assert result.exit_code == 0, result.output
    # Verify the stub was called and data matches
    assert captured.get('output_name') == 'browser_use_default.py'
    assert captured.get('content') == content
    assert captured.get('force') is False
    # Verify success messages in output
    assert '✅ Created' in result.output
    assert 'Next steps:' in result.output
    assert 'python browser_use_default.py' in result.output


def test_init_read_error_and_write_failure_exit(tmp_path, monkeypatch):
    runner = CliRunner()

    # Prepare directory but do NOT create the requested template file to force read error
    templates_dir = tmp_path / 'cli_templates'
    templates_dir.mkdir()

    # Map default to a missing file name to trigger read error
    templates = {
        'default': {'description': 'Default template', 'file': 'missing_default.py'},
    }
    monkeypatch.setattr(cli, 'INIT_TEMPLATES', templates)

    # Ensure Path(__file__).parent points to tmp_path so template lookup uses tmp_path/cli_templates
    fake_Path = _make_fake_path_for_module(tmp_path, cli.__file__)
    monkeypatch.setattr(cli, 'Path', fake_Path)

    # 1) Test read error when template file missing
    result = runner.invoke(cli.main, ['init', '--template', 'default'])
    # sys.exit(1) should cause non-zero exit
    assert result.exit_code == 1
    # Error message printed to stderr/stdout includes 'Error reading template'
    assert 'Error reading template' in result.output or '❌ Error reading template' in result.output

    # 2) Now create the file but make _write_init_file return False to hit the final sys.exit(1) branch
    good_file = templates_dir / 'missing_default.py'
    good_file.write_text("print('ok')\n", encoding='utf-8')
    # Monkeypatch write function to simulate failure
    def fake_write_failure(output_path, c, force_flag):
        return False

    monkeypatch.setattr(cli, '_write_init_file', fake_write_failure)

    # Provide an explicit output path to exercise the output-argument branch
    result2 = runner.invoke(cli.main, ['init', '--template', 'default', '--output', 'my_script.py'])
    assert result2.exit_code == 1
    # No success message present
    assert '✅ Created' not in result2.output
