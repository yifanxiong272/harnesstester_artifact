# file: gpt_researcher/agent.py:216-280
# asked: {"lines": [236, 237, 239, 240, 241, 242, 243, 244, 245, 246, 248, 249, 250, 254, 255, 257, 258, 259, 260, 261, 262, 265, 274, 275, 276, 277, 280], "branches": [[234, 236], [236, 237], [236, 239], [239, 240], [239, 243], [243, 244], [243, 248], [253, 254], [257, 258], [257, 259], [259, 260], [259, 261], [261, 262], [261, 265], [268, 280], [271, 274], [274, 275], [274, 276], [276, 277], [276, 280]]}
# gained: {"lines": [236, 237, 239, 240, 241, 242, 243, 244, 245, 246, 248, 249, 250, 254, 255, 257, 258, 259, 260, 261, 262, 265, 274, 275, 276, 277, 280], "branches": [[234, 236], [236, 237], [236, 239], [239, 240], [239, 243], [243, 244], [243, 248], [253, 254], [257, 258], [257, 259], [259, 260], [259, 261], [261, 262], [261, 265], [268, 280], [271, 274], [274, 275], [274, 276], [276, 277]]}

import sys
import importlib.util
import types
from pathlib import Path
from types import SimpleNamespace
import pytest

def load_gptresearcher_class():
    # locate agent.py containing GPTResearcher
    cwd = Path.cwd()
    candidates = list(cwd.rglob('agent.py'))
    agent_path = None
    for p in candidates:
        try:
            txt = p.read_text(encoding='utf-8')
        except Exception:
            continue
        if 'class GPTResearcher' in txt and 'def _resolve_mcp_strategy' in txt:
            agent_path = p
            break
    if agent_path is None:
        # broaden search
        for p in candidates:
            try:
                txt = p.read_text(encoding='utf-8')
            except Exception:
                continue
            if 'class GPTResearcher' in txt:
                agent_path = p
                break
    if agent_path is None:
        pytest.skip("Could not find agent.py defining GPTResearcher in repository tree")

    parent_dir = agent_path.parent
    package_name = parent_dir.name

    # Prepare a package module so relative imports inside agent.py work
    pkg_fullname = package_name
    created_modules = []
    if pkg_fullname not in sys.modules:
        pkg = types.ModuleType(pkg_fullname)
        # Set __path__ so imports find sibling modules in the directory
        pkg.__path__ = [str(parent_dir)]
        sys.modules[pkg_fullname] = pkg
        created_modules.append(pkg_fullname)

    module_name = f"{pkg_fullname}.agent"
    spec = importlib.util.spec_from_file_location(module_name, str(agent_path))
    module = importlib.util.module_from_spec(spec)
    # Ensure the module knows its package to allow relative imports
    module.__package__ = pkg_fullname
    # Execute module
    try:
        spec.loader.exec_module(module)
    except Exception:
        # cleanup any modules we added before re-raising to avoid pollution
        for name in created_modules:
            sys.modules.pop(name, None)
        raise

    # Register the loaded module under its full name to mimic normal import behavior
    sys.modules[module_name] = module
    created_modules.append(module_name)

    # Verify class exists
    if not hasattr(module, 'GPTResearcher'):
        # cleanup
        for name in created_modules:
            sys.modules.pop(name, None)
        pytest.skip("Loaded agent module does not contain GPTResearcher")

    # Return class and a cleanup function
    def cleanup():
        for name in created_modules:
            sys.modules.pop(name, None)

    return module.GPTResearcher, cleanup

@pytest.fixture(scope="module")
def GPTResearcher():
    cls, cleanup = load_gptresearcher_class()
    try:
        yield cls
    finally:
        cleanup()

@pytest.mark.parametrize(
    "mcp_strategy, expected",
    [
        ("fast", "fast"),
        ("deep", "deep"),
        ("disabled", "disabled"),
        ("optimized", "fast"),
        ("comprehensive", "deep"),
        ("invalid-name", "fast"),
    ],
)
def test_resolve_mcp_strategy_with_mcp_strategy_param(GPTResearcher, mcp_strategy, expected):
    researcher = object.__new__(GPTResearcher)
    researcher.cfg = SimpleNamespace()
    result = researcher._resolve_mcp_strategy(mcp_strategy, None)
    assert result == expected

@pytest.mark.parametrize(
    "mcp_max_iterations, expected",
    [
        (0, "disabled"),
        (1, "fast"),
        (-1, "deep"),
        (2, "fast"),
        (999, "fast"),
    ],
)
def test_resolve_mcp_strategy_with_mcp_max_iterations(GPTResearcher, mcp_max_iterations, expected):
    researcher = object.__new__(GPTResearcher)
    researcher.cfg = SimpleNamespace()
    result = researcher._resolve_mcp_strategy(None, mcp_max_iterations)
    assert result == expected

def test_resolve_mcp_strategy_with_cfg_strategy_values_and_default(GPTResearcher):
    researcher = object.__new__(GPTResearcher)
    researcher.cfg = SimpleNamespace(mcp_strategy="fast")
    assert researcher._resolve_mcp_strategy(None, None) == "fast"

    researcher = object.__new__(GPTResearcher)
    researcher.cfg = SimpleNamespace(mcp_strategy="optimized")
    assert researcher._resolve_mcp_strategy(None, None) == "fast"

    researcher = object.__new__(GPTResearcher)
    researcher.cfg = SimpleNamespace(mcp_strategy="comprehensive")
    assert researcher._resolve_mcp_strategy(None, None) == "deep"

    researcher = object.__new__(GPTResearcher)
    researcher.cfg = SimpleNamespace()
    assert researcher._resolve_mcp_strategy(None, None) == "fast"
