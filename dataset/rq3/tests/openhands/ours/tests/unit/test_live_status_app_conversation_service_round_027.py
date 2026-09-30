import logging
import pytest

from openhands.app_server.app_conversation.live_status_app_conversation_service import (
    LiveStatusAppConversationService,
)


class DummyReq:
    """Minimal stand-in for AppConversationUpdateRequest used by _validate_repository_update.

    Provides the attributes accessed by the method under test:
    - model_fields_set: an iterable of field names present in the request
    - selected_repository: str | None
    - selected_branch: str | None
    - git_provider: any (None or non-None)
    """

    def __init__(self, model_fields_set, selected_repository=None, selected_branch=None, git_provider=None):
        # Use a set for membership checks similar to pydantic's model_fields_set
        self.model_fields_set = set(model_fields_set)
        self.selected_repository = selected_repository
        self.selected_branch = selected_branch
        self.git_provider = git_provider


def _svc_instance():
    # Avoid dataclass __init__ requirements by constructing a bare instance
    return object.__new__(LiveStatusAppConversationService)


def test_repo_missing_slash_round_027():
    svc = _svc_instance()
    req = DummyReq(['selected_repository'], selected_repository='ownerrepo')

    with pytest.raises(ValueError) as ei:
        svc._validate_repository_update(req)

    assert "Invalid repository format" in str(ei.value)


def test_repo_multiple_slashes_round_027():
    svc = _svc_instance()
    req = DummyReq(['selected_repository'], selected_repository='a/b/c')

    with pytest.raises(ValueError) as ei:
        svc._validate_repository_update(req)

    assert "Invalid repository format" in str(ei.value)


def test_repo_dangerous_chars_round_027():
    svc = _svc_instance()
    # include a dangerous char (semicolon) in the repo portion
    req = DummyReq(['selected_repository'], selected_repository='owner/rep;name')

    with pytest.raises(ValueError) as ei:
        svc._validate_repository_update(req)

    assert "Invalid characters in repository name" in str(ei.value)


def test_repo_set_without_branch_emits_warning_round_027(caplog):
    svc = _svc_instance()
    req = DummyReq(['selected_repository'], selected_repository='owner/repo')

    caplog.set_level(logging.WARNING)
    # existing_branch is None to trigger the warning path
    svc._validate_repository_update(req, existing_branch=None)

    assert any(
        'set without branch' in rec.getMessage() or 'set without branch' in caplog.text
        for rec in caplog.records
    ), "expected warning about repository set without branch"


def test_removing_repo_requires_branch_cleared_round_027():
    svc = _svc_instance()
    # Repository being removed (None) but branch is left non-None -> error
    req = DummyReq(['selected_repository', 'selected_branch'], selected_repository=None, selected_branch='main')

    with pytest.raises(ValueError) as ei:
        svc._validate_repository_update(req)

    assert 'When removing repository, branch must also be cleared' in str(ei.value)


def test_removing_repo_requires_provider_cleared_round_027():
    svc = _svc_instance()
    # Repository being removed but git_provider left non-None -> error
    req = DummyReq(['selected_repository', 'git_provider'], selected_repository=None, git_provider='github')

    with pytest.raises(ValueError) as ei:
        svc._validate_repository_update(req)

    assert 'When removing repository, git_provider must also be cleared' in str(ei.value)


def test_branch_dangerous_chars_round_027():
    svc = _svc_instance()
    # Branch contains a space (sanitized list includes ' '), should raise
    req = DummyReq(['selected_branch'], selected_branch='feature/new feature')

    with pytest.raises(ValueError) as ei:
        svc._validate_repository_update(req)

    assert "Invalid characters in branch name" in str(ei.value)
