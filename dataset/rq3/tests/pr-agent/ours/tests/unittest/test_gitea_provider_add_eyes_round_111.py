import types

import pytest

from pr_agent.git_providers.gitea_provider import GiteaProvider, ApiException


class DummyLogger:
    def __init__(self):
        self.errors = []

    def error(self, msg):
        # store the message for assertion
        self.errors.append(str(msg))


class DummyComment:
    def __init__(self, id):
        self.id = id


class DummyResponseObj:
    def __init__(self, id):
        self.id = id


def make_provider(repo_api):
    # Instantiate without calling __init__ to avoid external setup.
    prov = object.__new__(GiteaProvider)
    prov.repo_api = repo_api
    prov.owner = "dummy_owner"
    prov.repo = "dummy_repo"
    prov.pr_number = 11
    prov.issue_number = 22
    prov.enabled_pr = True
    prov.logger = DummyLogger()
    return prov


def test_disable_eyes_round_111():
    # When disable_eyes is True, function should return None immediately
    repo_api = types.SimpleNamespace()
    prov = make_provider(repo_api)

    result = prov.add_eyes_reaction(issue_comment_id=1, disable_eyes=True)

    assert result is None
    # No errors should be logged in this fast-return case
    assert prov.logger.errors == []


def test_comment_id_not_found_logs_and_returns_none_round_111():
    # list_all_comments returns comments that do not include the requested id
    def list_all_comments(owner, repo, index):
        return [DummyComment(1), DummyComment(2)]

    repo_api = types.SimpleNamespace(list_all_comments=list_all_comments,
                                     add_reaction_comment=lambda **kwargs: DummyResponseObj(999))
    prov = make_provider(repo_api)

    res = prov.add_eyes_reaction(issue_comment_id=9999)

    assert res is None
    # logger should have a message indicating ID not found and listing available IDs
    assert any("not found" in e or "Available IDs" in e for e in prov.logger.errors)


def test_add_reaction_returns_falsy_logs_and_returns_none_round_111():
    # Happy path until add_reaction_comment, but it returns falsy -> error logged
    def list_all_comments(owner, repo, index):
        return [DummyComment(10)]

    def add_reaction_comment(owner, repo, comment_id, reaction):
        # simulate API returning falsy value
        return False

    repo_api = types.SimpleNamespace(list_all_comments=list_all_comments,
                                     add_reaction_comment=add_reaction_comment)
    prov = make_provider(repo_api)

    r = prov.add_eyes_reaction(issue_comment_id=10)

    assert r is None
    assert any("Failed to add eyes reaction" in msg for msg in prov.logger.errors)


def test_add_reaction_returns_tuple_first_id_round_111():
    # add_reaction_comment returns a tuple; function should return response[0].id
    def list_all_comments(owner, repo, index):
        return [DummyComment(33)]

    def add_reaction_comment(owner, repo, comment_id, reaction):
        return (DummyResponseObj(77),)

    repo_api = types.SimpleNamespace(list_all_comments=list_all_comments,
                                     add_reaction_comment=add_reaction_comment)
    prov = make_provider(repo_api)

    out = prov.add_eyes_reaction(issue_comment_id=33)

    assert out == 77
    assert prov.logger.errors == []


def test_add_reaction_returns_object_with_id_round_111():
    # add_reaction_comment returns a single object; function should return object.id
    def list_all_comments(owner, repo, index):
        return [DummyComment(44)]

    def add_reaction_comment(owner, repo, comment_id, reaction):
        return DummyResponseObj(88)

    repo_api = types.SimpleNamespace(list_all_comments=list_all_comments,
                                     add_reaction_comment=add_reaction_comment)
    prov = make_provider(repo_api)

    out = prov.add_eyes_reaction(issue_comment_id=44)

    assert out == 88
    assert prov.logger.errors == []


def test_add_reaction_raises_ApiException_logs_and_returns_none_round_111():
    # Simulate the repo_api raising the ApiException imported in module
    def list_all_comments(owner, repo, index):
        return [DummyComment(5)]

    def add_reaction_comment(owner, repo, comment_id, reaction):
        raise ApiException("boom")

    repo_api = types.SimpleNamespace(list_all_comments=list_all_comments,
                                     add_reaction_comment=add_reaction_comment)
    prov = make_provider(repo_api)

    r = prov.add_eyes_reaction(issue_comment_id=5)

    assert r is None
    assert any("Error adding eyes reaction" in m for m in prov.logger.errors)


def test_add_reaction_raises_generic_exception_logs_and_returns_none_round_111():
    # Simulate a non-ApiException error being raised
    def list_all_comments(owner, repo, index):
        return [DummyComment(6)]

    def add_reaction_comment(owner, repo, comment_id, reaction):
        raise ValueError("unexpected")

    repo_api = types.SimpleNamespace(list_all_comments=list_all_comments,
                                     add_reaction_comment=add_reaction_comment)
    prov = make_provider(repo_api)

    r = prov.add_eyes_reaction(issue_comment_id=6)

    assert r is None
    assert any("Unexpected error" in m for m in prov.logger.errors)
