# file: openhands/runtime/base.py:794-964
# asked: {"lines": [826, 827, 828, 830, 840, 860, 887, 888, 889, 891, 910, 911, 912, 913, 917, 918, 919, 920, 923, 924, 927, 928, 929, 933, 934, 936, 937, 938, 939, 941, 942, 944, 945, 946, 948, 949, 950, 954, 955, 956], "branches": [[825, 826], [839, 840], [857, 860], [910, 911], [910, 936]]}
# gained: {"lines": [826, 827, 828, 830, 840, 860, 887, 888, 889, 891, 910, 911, 912, 913, 917, 918, 919, 920, 923, 924, 927, 928, 929, 933, 934, 936, 937, 938, 941, 942, 944, 945, 946, 948, 949, 950, 954, 955, 956], "branches": [[825, 826], [839, 840], [857, 860], [910, 911], [910, 936]]}

import pytest
from pathlib import Path
from types import SimpleNamespace

from openhands.events.observation import CmdOutputObservation
from openhands.integrations.service_types import AuthenticationError
from openhands.runtime.base import Runtime


class DummyRuntime(Runtime):
    """Minimal Runtime subclass that overrides abstract methods and provides
    controlled behaviors for testing get_microagents_from_org_or_user.
    """

    def __init__(self, workspace_root: Path):
        # Provide a config so the workspace_root property works
        self.config = SimpleNamespace(workspace_mount_path_in_sandbox=str(workspace_root))
        self.logged = []
        # provider_handler with default coroutine get_authenticated_git_url; tests may override
        async def default_get_auth(repo, is_optional=True):
            return f'https://git/{repo}.git'
        self.provider_handler = SimpleNamespace()
        self.provider_handler.get_authenticated_git_url = default_get_auth
        # hooks to control behavior
        self._is_gitlab = False
        self._is_azure = False
        self._loaded_microagents_return = []
        self._last_loaded_dir = None
        self._run_action_responses = []
        self._run_action_calls = []

    # Minimal logger capturing calls
    def log(self, level: str, message: str) -> None:
        self.logged.append((level, message))

    # Control repository type detection (tests patch these attributes directly)
    def _is_gitlab_repository(self, repo_name: str) -> bool:
        return self._is_gitlab

    def _is_azure_devops_repository(self, repo_name: str) -> bool:
        return self._is_azure

    # Implement abstract methods with minimal behavior
    async def connect(self) -> None:
        pass

    def get_mcp_config(self, extra_stdio_servers=None):
        raise NotImplementedError()

    def run(self, action):
        raise NotImplementedError()

    def run_ipython(self, action):
        raise NotImplementedError()

    def read(self, action):
        raise NotImplementedError()

    def write(self, action):
        raise NotImplementedError()

    def edit(self, action):
        raise NotImplementedError()

    def browse(self, action):
        raise NotImplementedError()

    def browse_interactive(self, action):
        raise NotImplementedError()

    async def call_tool_mcp(self, action):
        raise NotImplementedError()

    def copy_to(self, host_src, sandbox_dest, recursive=False):
        raise NotImplementedError()

    def list_files(self, path=None):
        return []

    def copy_from(self, path):
        return Path(path)

    @property
    def session_api_key(self):
        return None

    @property
    def vscode_enabled(self):
        return False

    @property
    def vscode_url(self):
        return None

    @property
    def web_hosts(self):
        return {}

    def _execute_shell_fn_git_handler(self, command: str, cwd: str | None):
        # Not used in tests
        return SimpleNamespace(exit_code=0, content='')

    def _create_file_fn_git_handler(self, path: str, content: str):
        return 0

    def get_git_changes(self, cwd: str):
        return None

    def get_git_diff(self, file_path: str, cwd: str):
        return {}

    def get_workspace_branch(self, primary_repo_path: str | None = None):
        return None

    @property
    def additional_agent_instructions(self) -> str:
        return ''

    def subscribe_to_shell_stream(self, callback=None) -> bool:
        return False

    @classmethod
    def setup(cls, config, headless_mode=False):
        pass

    @classmethod
    def teardown(cls, config):
        pass

    # Helpers used by get_microagents_from_org_or_user
    def _load_microagents_from_directory(self, microagents_dir: Path, source_description: str):
        self._last_loaded_dir = microagents_dir
        return self._loaded_microagents_return

    def run_action(self, action):
        # record invocation and return next response from queue
        self._run_action_calls.append(action)
        if self._run_action_responses:
            resp = self._run_action_responses.pop(0)
            return resp
        # Default: return a successful CmdOutputObservation.
        return CmdOutputObservation("ok", "cmd", exit_code=0)


def make_cmd_obs(exit_code=0, content=''):
    # CmdOutputObservation signature: (content, command, ..., **kwargs)
    return CmdOutputObservation(content, "cmd", exit_code=exit_code)


def test_repo_path_with_insufficient_parts_returns_empty(tmp_path):
    rt = DummyRuntime(workspace_root=tmp_path)
    # Single part repo should return early
    res = rt.get_microagents_from_org_or_user("singlename")
    assert res == []
    # Ensure warning logged about insufficient parts
    assert any("insufficient parts" in msg for level, msg in rt.logged if level == 'warning')


def test_azure_devops_success_clone_and_cleanup(tmp_path):
    rt = DummyRuntime(workspace_root=tmp_path)
    # Simulate Azure DevOps repo type and a successful clone then cleanup
    rt._is_azure = True
    rt._is_gitlab = False

    async def get_auth(repo, is_optional=True):
        return "https://example.com/remote.git"

    rt.provider_handler.get_authenticated_git_url = get_auth

    # Prepare run_action responses: first for clone (success), second for rm -rf
    rt._run_action_responses = [
        make_cmd_obs(exit_code=0, content='cloned'),
        make_cmd_obs(exit_code=0, content='removed'),
    ]
    # Simulate that loading microagents finds one microagent
    dummy_micro = SimpleNamespace(name="m1")
    rt._loaded_microagents_return = [dummy_micro]

    # Use a three-part repo to ensure org_name extracted as first part
    selected_repo = "myorg/project/repo"
    res = rt.get_microagents_from_org_or_user(selected_repo)
    assert res == [dummy_micro]
    # Verify microagents directory was constructed under workspace_root/org_openhands_{org_name}/microagents
    expected_dir = Path(str(tmp_path)) / "org_openhands_myorg" / "microagents"
    assert rt._last_loaded_dir == expected_dir
    # Ensure both clone and cleanup actions were invoked
    assert len(rt._run_action_calls) >= 2
    # Validate logs contain info about successful clone
    assert any("Successfully cloned org-level microagents" in msg for level, msg in rt.logged if level == 'info')


def test_gitlab_clone_failure_logs_and_returns_empty(tmp_path):
    rt = DummyRuntime(workspace_root=tmp_path)
    # Simulate GitLab repository
    rt._is_gitlab = True
    rt._is_azure = False

    async def get_auth(repo, is_optional=True):
        return "https://example.com/remote.git"

    rt.provider_handler.get_authenticated_git_url = get_auth

    # Simulate clone failure with non-zero exit code and error content
    rt._run_action_responses = [
        make_cmd_obs(exit_code=1, content='fatal: repository not found')
    ]
    res = rt.get_microagents_from_org_or_user("owner/repo")
    assert res == []  # no microagents loaded on clone failure
    # Logs should contain messages about no org-level microagents found and include the clone error message
    assert any("No org-level microagents found" in msg for level, msg in rt.logged if level == 'info')
    assert any("repository not found" in msg for level, msg in rt.logged)


def test_authentication_error_is_logged_and_caught(tmp_path):
    rt = DummyRuntime(workspace_root=tmp_path)
    rt._is_gitlab = False
    rt._is_azure = False

    async def raise_auth(repo, is_optional=True):
        raise AuthenticationError("auth failed for testing")

    rt.provider_handler.get_authenticated_git_url = raise_auth

    res = rt.get_microagents_from_org_or_user("owner/repo")
    # Should catch and return empty list
    assert res == []
    # Ensure debug log contains indication of auth failure handling
    assert any("auth failed" in msg or "not found" in msg for level, msg in rt.logged)
