import pytest

from pr_agent.git_providers import gitlab_provider as gp
from pr_agent.git_providers.gitlab_provider import GitLabProvider


class DummyLogger:
    def __init__(self):
        self.warnings = []

    def warning(self, msg):
        # store exact message for deterministic assertions
        self.warnings.append(str(msg))


class FakeReaction:
    def __init__(self, name):
        self.name = name
        self.deleted = False

    def delete(self):
        self.deleted = True


class FakeNotes:
    def __init__(self, comment):
        # comment can be any object (including None)
        self._comment = comment

    def get(self, comment_id):
        # return the stored comment regardless of id for simplicity
        return self._comment


class FakeAwardEmojis:
    def __init__(self, reactions):
        self._reactions = reactions

    def list(self):
        return self._reactions


class FakeComment:
    def __init__(self, award_reactions):
        self.awardemojis = FakeAwardEmojis(award_reactions)


class FakeMergeRequestsContainer:
    def __init__(self, mr_obj):
        self._mr = mr_obj

    def get(self, mr_id):
        return self._mr


class FakeProject:
    def __init__(self, mr_obj):
        self.mergerequests = FakeMergeRequestsContainer(mr_obj)


class FakeGLGood:
    def __init__(self, project_obj):
        # projects.get(project_id) -> project_obj
        self._project_obj = project_obj
        self.projects = self

    def get(self, project_id):
        return self._project_obj


class FakeGLException:
    def __init__(self, exc):
        self._exc = exc
        self.projects = self

    def get(self, project_id):
        raise self._exc


def make_provider_with(logger, gl_obj, id_project=42, id_mr=1):
    # Create GitLabProvider instance without running __init__ to avoid external calls
    prov = object.__new__(GitLabProvider)
    prov.id_project = id_project
    prov.id_mr = id_mr
    prov.gl = gl_obj
    # patch module-level get_logger so remove_reaction uses our logger
    gp.get_logger = lambda: logger
    return prov


def test_remove_reaction_no_id_mr_round_100():
    logger = DummyLogger()
    # gl is irrelevant because method should early-return before using it
    prov = object.__new__(GitLabProvider)
    prov.id_mr = None
    prov.id_project = 1
    prov.gl = None
    gp.get_logger = lambda: logger

    result = GitLabProvider.remove_reaction(prov, issue_comment_id=10, reaction_id="eyes")

    assert result is False
    # exact message from source
    assert logger.warnings == ["Cannot remove reaction: merge request ID is not set."]


def test_remove_reaction_comment_missing_round_100():
    logger = DummyLogger()
    # MR with notes.get returning None to simulate missing comment
    mr = type("MR", (), {})()
    mr.notes = FakeNotes(None)
    project = FakeProject(mr)
    gl = FakeGLGood(project)

    prov = make_provider_with(logger, gl, id_project=99, id_mr=1)

    res = prov.remove_reaction(issue_comment_id=7, reaction_id="x")

    assert res is False
    # message should mention the comment id and merge request id
    assert any("Comment with ID 7 not found in merge request 1." == w for w in logger.warnings)


def test_remove_reaction_delete_success_round_100():
    logger = DummyLogger()
    # create a comment with a matching reaction
    reaction = FakeReaction("thumbsup")
    comment = FakeComment([reaction])
    mr = type("MR", (), {})()
    mr.notes = FakeNotes(comment)
    project = FakeProject(mr)
    gl = FakeGLGood(project)

    prov = make_provider_with(logger, gl, id_project=12, id_mr=1)

    res = prov.remove_reaction(issue_comment_id=123, reaction_id="thumbsup")

    assert res is True
    # delete should've been called
    assert reaction.deleted is True
    # no warnings should be emitted on success
    assert logger.warnings == []


def test_remove_reaction_reaction_not_found_round_100():
    logger = DummyLogger()
    # create a comment with reactions that do not match
    reactions = [FakeReaction("smile"), FakeReaction("heart")]
    comment = FakeComment(reactions)
    mr = type("MR", (), {})()
    mr.notes = FakeNotes(comment)
    project = FakeProject(mr)
    gl = FakeGLGood(project)

    prov = make_provider_with(logger, gl, id_project=77, id_mr=1)

    res = prov.remove_reaction(issue_comment_id=5, reaction_id="not-there")

    assert res is False
    # should warn about missing reaction with the exact formatting
    assert any("Reaction 'not-there' not found in comment 5." == w for w in logger.warnings)


def test_remove_reaction_raises_exception_round_100():
    logger = DummyLogger()
    # make the gitlab client raise an exception when accessing projects.get
    gl = FakeGLException(Exception("boom"))
    prov = make_provider_with(logger, gl, id_project=999, id_mr=1)

    res = prov.remove_reaction(issue_comment_id=1, reaction_id="any")

    assert res is False
    # warning should contain the exception string
    assert any("Failed to remove reaction, error: boom" == w for w in logger.warnings)
