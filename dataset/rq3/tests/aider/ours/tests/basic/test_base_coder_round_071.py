import importlib
import types
from unittest import mock

import pytest

base = importlib.import_module("aider.coders.base_coder")


# Create a minimal fake datetime provider that matches the usage in
# Coder.get_platform_info: datetime.now().astimezone().strftime("%Y-%m-%d")
class _FakeNow:
    def astimezone(self):
        return self

    def strftime(self, fmt):
        # return the deterministic date used in assertions
        return "2020-01-02"

class _FakeDatetimeModule:
    @staticmethod
    def now():
        return _FakeNow()


def test_get_platform_info_keyerror_and_lint_and_test_auto_round_071():
    """Covers: platform KeyError path, language present, repo True,
    auto_lint True with both None and named lint entries, and auto_test True.
    """
    fake_dt_mod = _FakeDatetimeModule()

    with mock.patch("aider.coders.base_coder.platform.platform", side_effect=KeyError()), \
         mock.patch("aider.coders.base_coder.os.name", "posix"), \
         mock.patch("aider.coders.base_coder.os.getenv", return_value="/bin/bash"), \
         mock.patch("aider.coders.base_coder.datetime", fake_dt_mod):

        fake_self = types.SimpleNamespace(
            get_user_language=lambda: "en-US",
            repo=True,
            lint_cmds={None: "cmdX", "py": "flake"},
            auto_lint=True,
            test_cmd="test-run",
            auto_test=True,
        )

        out = base.Coder.get_platform_info(fake_self)

    # Assertions that inspect observable output pieces created by branches
    assert out.startswith("- Platform information unavailable\n")
    assert "- Shell: SHELL=/bin/bash\n" in out
    assert "- Language: en-US\n" in out
    assert "- Current date: 2020-01-02\n" in out
    assert "- The user is operating inside a git repository\n" in out
    # lint pre-commit (auto_lint True) message present
    assert "pre-commit runs these lint commands" in out
    # both lint entries formatted as expected (None yields just the cmd)
    assert "  - cmdX\n" in out
    assert "  - py: flake\n" in out
    # auto_test True pre-commit phrasing and test command appended
    assert "pre-commit runs this test command" in out
    assert "test-run\n" in out


def test_get_platform_info_no_user_lang_and_lint_prefers_and_test_prefers_round_071():
    """Covers: platform returns normal string, no language, repo False,
    auto_lint False (preference message), and auto_test False (preference message).
    Also exercises COMSPEC branch for windows-like os.name.
    """
    fake_dt_mod = _FakeDatetimeModule()

    with mock.patch("aider.coders.base_coder.platform.platform", return_value="MyOS-1.2"), \
         mock.patch("aider.coders.base_coder.os.name", "nt"), \
         mock.patch("aider.coders.base_coder.os.getenv", return_value="C:\\Windows\\cmd.exe"), \
         mock.patch("aider.coders.base_coder.datetime", fake_dt_mod):

        fake_self = types.SimpleNamespace(
            get_user_language=lambda: "",  # falsy -> skip language branch
            repo=False,
            lint_cmds={None: "untyped-lint", "js": "eslint"},
            auto_lint=False,
            test_cmd="run-tests",
            auto_test=False,
        )

        out = base.Coder.get_platform_info(fake_self)

    # Platform string present (normal path)
    assert out.startswith("- Platform: MyOS-1.2\n")
    # COMSPEC branch used on Windows-like os.name
    assert "- Shell: COMSPEC=C:\\Windows\\cmd.exe\n" in out
    # Language not present when falsy
    assert "- Language:" not in out
    # Repo message absent
    assert "operating inside a git repository" not in out
    # Lint preference (auto_lint False)
    assert "- The user prefers these lint commands:" in out
    # both lint entries formatted correctly
    assert "  - untyped-lint\n" in out
    assert "  - js: eslint\n" in out
    # Test preference line for auto_test False
    assert "- The user prefers this test command: " in out
    assert "run-tests\n" in out
