# file: openhands/runtime/action_execution_server.py:178-230
# asked: {"lines": [178, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 194, 195, 197, 198, 199, 200, 201, 202, 203, 204, 206, 207, 208, 211, 212, 213, 214, 215, 217, 218, 219, 220, 221, 224, 226, 227, 228, 230], "branches": [[194, 195], [194, 197], [206, 207], [206, 211], [218, 219], [218, 224]]}
# gained: {"lines": [178, 185, 186, 187, 188, 189, 190, 191, 192, 194, 195, 197, 198, 199, 200, 201, 202, 203, 204, 206, 207, 208, 211, 212, 213, 214, 215, 217, 218, 219, 220, 221, 224, 226, 227, 228, 230], "branches": [[194, 195], [194, 197], [206, 207], [206, 211], [218, 219], [218, 224]]}

import os
import sys
import pytest
import importlib

MODULE_PATH = "openhands.runtime.action_execution_server"


@pytest.fixture(autouse=True)
def reload_module_between_tests():
    # Ensure a fresh module state for each test
    if MODULE_PATH in sys.modules:
        del sys.modules[MODULE_PATH]
    module = importlib.import_module(MODULE_PATH)
    yield module
    # cleanup env vars that tests may set
    for k in ("RUNTIME_MAX_MEMORY_GB", "RUNTIME_MEMORY_MONITOR"):
        os.environ.pop(k, None)
    # ensure module removed after test to avoid leakage
    if MODULE_PATH in sys.modules:
        del sys.modules[MODULE_PATH]


def make_dummy_memory_monitor_collector(monkeypatch, module):
    started = {"called": False}
    created_instances = []

    class DummyMemoryMonitor:
        def __init__(self, enable=False):
            self.enable = enable
            self.started = False
            created_instances.append(self)

        def start_monitoring(self):
            started["called"] = True
            self.started = True

    # set on module object, allow creation even if attribute doesn't exist
    monkeypatch.setattr(module, "MemoryMonitor", DummyMemoryMonitor, raising=False)
    return started, created_instances


def make_dummy_oheditor(monkeypatch, module):
    created = []

    class DummyOHEditor:
        def __init__(self, workspace_root):
            self.workspace_root = workspace_root
            created.append(self)

    monkeypatch.setattr(module, "OHEditor", DummyOHEditor, raising=False)
    return created


def make_dummy_init_user(monkeypatch, module, return_value):
    def dummy_init_user_and_working_directory(username, user_id, initial_cwd):
        return return_value

    monkeypatch.setattr(module, "init_user_and_working_directory", dummy_init_user_and_working_directory, raising=False)


def import_module():
    return importlib.import_module(MODULE_PATH)


def test_init_updates_user_and_sets_max_memory_and_starts_monitor(monkeypatch, reload_module_between_tests):
    module = reload_module_between_tests
    # Prepare dummy components
    started_flag, instances = make_dummy_memory_monitor_collector(monkeypatch, module)
    created_editors = make_dummy_oheditor(monkeypatch, module)
    # Simulate init_user_and_working_directory returning a different uid
    make_dummy_init_user(monkeypatch, module, return_value=9999)

    # Set environment variables to hit the branch where max memory is set and monitor enabled
    monkeypatch.setenv("RUNTIME_MAX_MEMORY_GB", "8")
    monkeypatch.setenv("RUNTIME_MEMORY_MONITOR", "yes")

    # Import ActionExecutor from the module
    ActionExecutor = getattr(module, "ActionExecutor")

    work_dir = "/some/work/dir"
    ae = ActionExecutor(plugins_to_load=[], work_dir=work_dir, username="u", user_id=1000, enable_browser=True, browsergym_eval_env=None)

    # Assertions for the updated user id branch
    assert ae.user_id == 9999, "user_id should be updated from init_user_and_working_directory return value"

    # Assertions for max memory branch
    assert ae.max_memory_gb == 8
    # The dummy MemoryMonitor should have been constructed and started
    assert started_flag["called"] is True
    assert len(instances) == 1
    assert instances[0].enable is True
    assert instances[0].started is True

    # OHEditor should be created with the provided workspace root
    assert len(created_editors) == 1
    assert created_editors[0].workspace_root == work_dir

    # Other basic attributes set by __init__
    assert ae._initial_cwd == work_dir
    assert ae.enable_browser is True
    assert ae.browser is None


def test_init_no_max_memory_and_monitor_disabled(monkeypatch, reload_module_between_tests):
    module = reload_module_between_tests
    started_flag, instances = make_dummy_memory_monitor_collector(monkeypatch, module)
    created_editors = make_dummy_oheditor(monkeypatch, module)
    make_dummy_init_user(monkeypatch, module, return_value=None)

    # Ensure env var for max memory is not set and monitor is set to a false value
    monkeypatch.delenv("RUNTIME_MAX_MEMORY_GB", raising=False)
    monkeypatch.setenv("RUNTIME_MEMORY_MONITOR", "no")

    ActionExecutor = getattr(module, "ActionExecutor")
    work_dir = "/another/work/dir"
    ae = ActionExecutor(plugins_to_load=[], work_dir=work_dir, username="u2", user_id=2000, enable_browser=True, browsergym_eval_env=None)

    # No override, so max_memory_gb should be None
    assert ae.max_memory_gb is None

    # Memory monitor should still be started, but with enable False
    assert started_flag["called"] is True
    assert len(instances) == 1
    assert instances[0].enable is False
    assert instances[0].started is True

    # OHEditor present
    assert len(created_editors) == 1
    assert created_editors[0].workspace_root == work_dir


def test_init_raises_when_browser_disabled_but_browsergym_set(monkeypatch, reload_module_between_tests):
    module = reload_module_between_tests
    # Use dummy components to avoid side effects
    make_dummy_memory_monitor_collector(monkeypatch, module)
    make_dummy_oheditor(monkeypatch, module)
    make_dummy_init_user(monkeypatch, module, return_value=None)

    ActionExecutor = getattr(module, "ActionExecutor")

    with pytest.raises(getattr(module, "BrowserUnavailableException")):
        ActionExecutor(plugins_to_load=[], work_dir="/wd", username="u3", user_id=3000, enable_browser=False, browsergym_eval_env="some_env")
