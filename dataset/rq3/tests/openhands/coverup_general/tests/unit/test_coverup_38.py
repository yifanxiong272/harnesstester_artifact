# file: openhands/app_server/app_conversation/live_status_app_conversation_service.py:1655-1713
# asked: {"lines": [1670, 1671, 1672, 1674, 1675, 1676, 1680, 1681, 1686, 1687, 1689, 1690, 1696, 1697, 1698, 1699, 1701, 1702, 1703, 1704, 1708, 1709, 1710, 1712, 1713], "branches": [[1670, 1671], [1670, 1708], [1672, 1674], [1672, 1696], [1674, 1675], [1674, 1680], [1680, 1681], [1680, 1685], [1685, 1689], [1685, 1708], [1696, 1697], [1696, 1701], [1697, 1698], [1697, 1701], [1701, 1702], [1701, 1708], [1702, 1703], [1702, 1708], [1708, 0], [1708, 1709], [1710, 0], [1710, 1712], [1712, 0], [1712, 1713]]}
# gained: {"lines": [1670, 1671, 1672, 1674, 1675, 1676, 1680, 1681, 1686, 1687, 1689, 1690, 1696, 1697, 1698, 1699, 1701, 1702, 1703, 1704, 1708, 1709, 1710, 1712, 1713], "branches": [[1670, 1671], [1670, 1708], [1672, 1674], [1672, 1696], [1674, 1675], [1674, 1680], [1680, 1681], [1680, 1685], [1685, 1689], [1696, 1697], [1696, 1701], [1697, 1698], [1701, 1702], [1702, 1703], [1708, 0], [1708, 1709], [1710, 1712], [1712, 1713]]}

import importlib
import pytest

from openhands.app_server.app_conversation.app_conversation_models import AppConversationUpdateRequest
from openhands.app_server.app_conversation.live_status_app_conversation_service import (
    LiveStatusAppConversationService,
)
from openhands.integrations.service_types import ProviderType


def _make_service():
    # Minimal constructor arguments; provide required init_git_in_empty_workspace flag.
    return LiveStatusAppConversationService(
        user_context=None,
        app_conversation_info_service=None,
        app_conversation_start_task_service=None,
        event_callback_service=None,
        event_service=None,
        sandbox_service=None,
        sandbox_spec_service=None,
        jwt_service=None,
        pending_message_service=None,
        sandbox_startup_timeout=1,
        sandbox_startup_poll_frequency=1,
        max_num_conversations_per_sandbox=1,
        httpx_client=None,
        web_url=None,
        openhands_provider_base_url=None,
        access_token_hard_timeout=None,
        init_git_in_empty_workspace=False,
    )


def test_invalid_repository_format_raises():
    svc = _make_service()
    # no slash
    req = AppConversationUpdateRequest(selected_repository="ownerrepo")
    with pytest.raises(ValueError) as exc:
        svc._validate_repository_update(req, existing_branch=None)
    assert "Invalid repository format" in str(exc.value)

    # too many slashes
    req2 = AppConversationUpdateRequest(selected_repository="a/b/c")
    with pytest.raises(ValueError) as exc2:
        svc._validate_repository_update(req2, existing_branch=None)
    assert "Invalid repository format" in str(exc2.value)


def test_repository_with_invalid_characters_raises():
    svc = _make_service()
    # contains semicolon but only one slash (so format check passes and char check triggers)
    req = AppConversationUpdateRequest(selected_repository="owner/repo;rm -rf")
    with pytest.raises(ValueError) as exc:
        svc._validate_repository_update(req, existing_branch=None)
    assert "Invalid characters in repository name" in str(exc.value)

    # contains newline (still only one slash)
    req2 = AppConversationUpdateRequest(selected_repository="owner/repo\nx")
    with pytest.raises(ValueError) as exc2:
        svc._validate_repository_update(req2, existing_branch=None)
    assert "Invalid characters in repository name" in str(exc2.value)


def test_setting_repository_without_branch_logs_warning(monkeypatch):
    svc = _make_service()
    module = importlib.import_module(
        "openhands.app_server.app_conversation.live_status_app_conversation_service"
    )

    class DummyLogger:
        def __init__(self):
            self.warnings = []

        def warning(self, msg):
            self.warnings.append(msg)

    dummy = DummyLogger()
    monkeypatch.setattr(module, "_logger", dummy)
    req = AppConversationUpdateRequest(selected_repository="owner/repo")
    # Should not raise, but should log a warning because no branch provided and none exists
    svc._validate_repository_update(req, existing_branch=None)
    assert dummy.warnings, "Expected a warning when setting repository without branch"
    assert "Repository owner/repo set without branch" in dummy.warnings[0]


def test_removing_repository_requires_branch_and_provider_cleared_branch_violation():
    svc = _make_service()
    # selected_repository explicitly set to None and selected_branch set to non-None -> raises
    req = AppConversationUpdateRequest(selected_repository=None, selected_branch="main")
    with pytest.raises(ValueError) as exc:
        svc._validate_repository_update(req, existing_branch=None)
    assert "When removing repository, branch must also be cleared" in str(exc.value)


def test_removing_repository_requires_branch_and_provider_cleared_provider_violation():
    svc = _make_service()
    # selected_repository explicitly set to None and git_provider set to non-None -> raises
    req = AppConversationUpdateRequest(selected_repository=None, git_provider=ProviderType.GITHUB)
    with pytest.raises(ValueError) as exc:
        svc._validate_repository_update(req, existing_branch=None)
    assert "When removing repository, git_provider must also be cleared" in str(exc.value)


def test_branch_sanitization_invalid_characters_raise():
    svc = _make_service()
    # branch contains space -> invalid
    req = AppConversationUpdateRequest(selected_branch="feature new")
    with pytest.raises(ValueError) as exc:
        svc._validate_repository_update(req, existing_branch=None)
    assert "Invalid characters in branch name" in str(exc.value)

    # branch contains semicolon -> invalid
    req2 = AppConversationUpdateRequest(selected_branch="main;rm")
    with pytest.raises(ValueError) as exc2:
        svc._validate_repository_update(req2, existing_branch=None)
    assert "Invalid characters in branch name" in str(exc2.value)
