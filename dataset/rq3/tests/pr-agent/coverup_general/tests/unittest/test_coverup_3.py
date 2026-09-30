# file: pr_agent/tools/pr_similar_issue.py:260-388
# asked: {"lines": [269, 270, 271, 272, 275, 276, 277, 278, 279, 280, 282, 283, 284, 286, 287, 288, 290, 291, 292, 293, 294, 295, 297, 299, 300, 302, 303, 304, 305, 306, 308, 309, 310, 311, 312, 313, 315, 316, 317, 319, 320, 322, 324, 325, 327, 328, 329, 330, 331, 333, 334, 335, 336, 338, 339, 341, 342, 343, 345, 346, 347, 348, 349, 350, 351, 352, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 371, 372, 373, 375, 376, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388], "branches": [[261, 275], [290, 291], [290, 319], [297, 299], [297, 317], [299, 300], [299, 302], [308, 309], [308, 310], [310, 311], [310, 312], [312, 313], [312, 315], [319, 320], [319, 345], [322, 324], [322, 343], [324, 325], [324, 327], [333, 334], [333, 335], [335, 336], [335, 338], [338, 339], [338, 341], [345, 346], [345, 375], [355, 356], [355, 373], [357, 358], [357, 359], [364, 365], [364, 366], [366, 367], [366, 368], [368, 369], [368, 371], [378, 379], [378, 385], [382, 383], [382, 384], [385, 386], [385, 387]]}
# gained: {"lines": [269, 270, 271, 272, 275, 276, 277, 278, 279, 280, 282, 283, 284, 286, 287, 288, 290, 291, 292, 293, 294, 295, 297, 299, 300, 302, 303, 304, 305, 306, 308, 310, 311, 312, 313, 315, 316, 317, 319, 320, 322, 324, 325, 327, 328, 329, 330, 331, 333, 335, 336, 338, 341, 342, 343, 345, 346, 347, 348, 349, 350, 351, 352, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 366, 367, 368, 369, 372, 373, 375, 376, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388], "branches": [[261, 275], [290, 291], [290, 319], [297, 299], [297, 317], [299, 300], [299, 302], [308, 310], [310, 311], [312, 313], [312, 315], [319, 320], [319, 345], [322, 324], [322, 343], [324, 325], [324, 327], [333, 335], [335, 336], [338, 341], [345, 346], [355, 356], [355, 373], [357, 358], [357, 359], [364, 366], [366, 367], [368, 369], [378, 379], [378, 385], [382, 383], [382, 384], [385, 386]]}

import asyncio
import types
import sys
import pytest

from pr_agent.tools import pr_similar_issue as psi_module
from pr_agent.tools.pr_similar_issue import PRSimilarIssue


class DummySettings:
    def __init__(self, publish_output=True, vectordb="pinecone"):
        self.config = types.SimpleNamespace(publish_output=publish_output)
        self.openai = types.SimpleNamespace(key="testkey")
        self.pr_similar_issue = types.SimpleNamespace(vectordb=vectordb)
        # values referenced elsewhere but not used in these tests
        self.CONFIG = types.SimpleNamespace(CLI_MODE=False)
        self.pr_similar_issue.max_issues_to_scan = 10
        self.pr_similar_issue.force_update_dataset = False


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.warnings = []
        self.debugs = []

    def info(self, *args, **kwargs):
        self.infos.append((args, kwargs))

    def warning(self, *args, **kwargs):
        self.warnings.append((args, kwargs))

    def debug(self, *args, **kwargs):
        self.debugs.append((args, kwargs))


@pytest.mark.asyncio
async def test_unsupported_publish_comment_exception(monkeypatch):
    """
    Exercise the branch where the tool is unsupported and publishing the unsupported
    message raises an exception. This should trigger the logger.warning branch and
    return an empty string.
    """
    dummy_logger = DummyLogger()
    # Patch module-level get_logger and get_settings
    monkeypatch.setattr(psi_module, "get_logger", lambda: dummy_logger)
    monkeypatch.setattr(psi_module, "get_settings", lambda: DummySettings(publish_output=True))

    # Prepare a fake provider factory that raises when publish_comment is called
    class BadProvider:
        def publish_comment(self, message):
            raise RuntimeError("publish failed")

    def fake_get_provider(issue_url):
        return BadProvider()

    # Patch the git provider getter used in the unsupported branch by altering the actual module
    monkeypatch.setattr("pr_agent.git_providers.get_git_provider_with_context", fake_get_provider, raising=True)

    # Create the PRSimilarIssue instance bypassing __init__
    inst = object.__new__(PRSimilarIssue)
    inst.supported = False
    inst.issue_url = "https://example.com/?issue=1"

    res = await inst.run()
    assert res == ""
    # Ensure the warning was recorded with expected message
    assert any("Failed to publish /similar_issue unsupported message" in args[0] for args, _ in dummy_logger.warnings)


@pytest.mark.asyncio
async def test_run_with_pinecone(monkeypatch):
    """
    Test the full run when vectordb == "pinecone". Create fake openai embedding,
    a fake pinecone index returning matches, and fake git provider with issues and comments.
    Ensure create_comment is invoked and contents include the title and score.
    """
    dummy_logger = DummyLogger()
    monkeypatch.setattr(psi_module, "get_logger", lambda: dummy_logger)

    # Settings to use pinecone and publish_output True
    monkeypatch.setattr(psi_module, "get_settings", lambda: DummySettings(publish_output=True, vectordb="pinecone"))

    # Fake openai Embedding.create
    class FakeEmbedding:
        @staticmethod
        def create(input, engine):
            return {"data": [{"embedding": [0.1, 0.2, 0.3]}]}

    monkeypatch.setattr(psi_module, "openai", types.SimpleNamespace(Embedding=FakeEmbedding, api_key=None))

    # Fake pinecone index and module
    class FakeIndex:
        def __init__(self, index_name=None):
            self.index_name = index_name

        def query(self, embed, top_k, filter, include_metadata):
            # Return an object with to_dict method
            class R:
                def to_dict(self_inner):
                    return {
                        "matches": [
                            {"id": "example_issue_1"},  # should be skipped
                            {"id": "repo_issue_7.comment_2", "score": 0.9876},
                            {"id": "repo_issue_8", "score": 0.5},
                            {"id": "badformat", "score": 0.1},
                        ]
                    }
            return R()

    # Allow adding attribute even if not present
    monkeypatch.setattr(psi_module, "pinecone", types.SimpleNamespace(Index=FakeIndex), raising=False)

    # Fake git provider, repo_obj and issues
    class FakeComment:
        def __init__(self, html_url):
            self.html_url = html_url

    class FakeIssue:
        def __init__(self, number):
            self.number = number
            self.title = f"Title {number}"
            self.html_url = f"https://example.com/issues/{number}"
            self._comments = [FakeComment(f"https://example.com/issues/{number}#comment0"),
                              FakeComment(f"https://example.com/issues/{number}#comment1"),
                              FakeComment(f"https://example.com/issues/{number}#comment2")]

        def get_comments(self):
            return iter(self._comments)

        def create_comment(self, body):
            # Return a fake response object and record created body
            self.created = body
            return {"created": True}

    class FakeRepoObj:
        def __init__(self):
            # map issue numbers to objects
            self.issues = {1: FakeIssue(1), 7: FakeIssue(7), 8: FakeIssue(8)}

        def get_issue(self, number):
            return self.issues[number]

    class FakeGitProvider:
        def __init__(self):
            self.repo_obj = FakeRepoObj()

        @staticmethod
        def _parse_issue_url(s):
            # Expecting the fragment after '=' from the code; return repo and number
            return ("owner/repo", 1)

    gitp = FakeGitProvider()

    # Instantiate PRSimilarIssue bypassing __init__ and set attributes
    inst = object.__new__(PRSimilarIssue)
    inst.supported = True
    inst.issue_url = "https://example.com/?issue=1"
    inst.git_provider = gitp
    inst.index_name = "idx"
    inst.repo_name_for_index = "owner/repo"

    # _process_issue should return text to be embedded
    monkeypatch.setattr(inst, "_process_issue", lambda issue_main: ("issue text", [], 1))

    # Run async
    res = await inst.run()

    # After run, original issue object should have had create_comment called
    issue_main = gitp.repo_obj.get_issue(1)
    assert hasattr(issue_main, "created"), "Expected create_comment to be called on the original issue"
    # The created body should contain the title of issue 7 and the formatted score for 0.9876 -> "0.99"
    assert "Title 7" in issue_main.created
    assert "(score=0.99)" in issue_main.created
    # Also ensure logger info recorded the similar issues header
    assert any("### Similar Issues" in args[0] for args, _ in dummy_logger.infos)


@pytest.mark.asyncio
async def test_run_with_lancedb_and_qdrant(monkeypatch):
    """
    Test lancedb and qdrant branches to exercise parsing exceptions and comment index usage.
    This test runs the inst.run twice with different vectordb settings.
    """
    dummy_logger = DummyLogger()
    monkeypatch.setattr(psi_module, "get_logger", lambda: dummy_logger)

    # Fake openai embedding used in both runs
    class FakeEmbedding:
        @staticmethod
        def create(input, engine):
            return {"data": [{"embedding": [0.4, 0.5]}]}

    monkeypatch.setattr(psi_module, "openai", types.SimpleNamespace(Embedding=FakeEmbedding, api_key=None))

    # Prepare common fake git provider with issues and comments
    class FakeComment:
        def __init__(self, html_url):
            self.html_url = html_url

    class FakeIssue:
        def __init__(self, number):
            self.number = number
            self.title = f"IssueTitle{number}"
            self.html_url = f"https://example.com/{number}"
            self._comments = [FakeComment(f"https://example.com/{number}#c0"),
                              FakeComment(f"https://example.com/{number}#c1")]

        def get_comments(self):
            return iter(self._comments)

        def create_comment(self, body):
            self.created = body
            return {"ok": True}

    class FakeRepoObj:
        def __init__(self):
            self.issues = {2: FakeIssue(2), 3: FakeIssue(3), 4: FakeIssue(4)}

        def get_issue(self, number):
            return self.issues[number]

    class FakeGitProvider:
        def __init__(self):
            self.repo_obj = FakeRepoObj()

        @staticmethod
        def _parse_issue_url(s):
            return ("owner/repo", 2)

    gitp = FakeGitProvider()

    # First run: lancedb
    monkeypatch.setattr(psi_module, "get_settings", lambda: DummySettings(publish_output=True, vectordb="lancedb"))

    # Fake table with search().where(...).to_list()
    class FakeTableSearch:
        def __init__(self, query_vec):
            self.query_vec = query_vec

        def where(self, q, prefilter=True):
            return self

        def to_list(self):
            # include an example id that should be skipped, a malformed id, and a valid id 'repo_issue_3' with distance
            return [
                {"id": "example_issue_999"},
                {"id": "weirdid"},
                {"id": "repo_issue_3", "_distance": 0.2},
            ]

    class FakeTable:
        def search(self, v):
            return FakeTableSearch(v)

    inst = object.__new__(PRSimilarIssue)
    inst.supported = True
    inst.issue_url = "https://example.com/?issue=2"
    inst.git_provider = gitp
    inst.table = FakeTable()
    inst.index_name = "idx"
    inst.repo_name_for_index = "owner/repo"
    # Patch _process_issue
    monkeypatch.setattr(inst, "_process_issue", lambda issue_main: ("text", [], 2))

    res1 = await inst.run()
    # After run, ensure original issue (2) got create_comment
    issue_main = gitp.repo_obj.get_issue(2)
    assert hasattr(issue_main, "created")
    # Score for _distance 0.2 should be 1 - 0.2 = 0.8 -> formatted "0.80"
    assert "(score=0.80)" in issue_main.created

    # Second run: qdrant
    monkeypatch.setattr(psi_module, "get_settings", lambda: DummySettings(publish_output=True, vectordb="qdrant"))

    # Create fake qdrant_client.models module objects so import inside function succeeds
    mod = types.ModuleType("qdrant_client.models")
    # Simple placeholder classes
    class FieldCondition:
        def __init__(self, key=None, match=None):
            self.key = key
            self.match = match

    class Filter:
        def __init__(self, must=None):
            self.must = must

    class MatchValue:
        def __init__(self, value=None):
            self.value = value

    mod.FieldCondition = FieldCondition
    mod.Filter = Filter
    mod.MatchValue = MatchValue
    sys.modules["qdrant_client.models"] = mod

    # Fake qdrant search result objects
    class QRes:
        def __init__(self, payload_id, score):
            self.payload = {"id": payload_id}
            self.score = score

    q_results = [QRes("example_issue_100", 0.1),
                 QRes("repo_issue_4.comment_1", 0.456),
                 QRes("bad_format", 0.2)]

    class FakeQdrantClient:
        def search(self, collection_name, query_vector, limit, query_filter, with_payload):
            return q_results

    inst2 = object.__new__(PRSimilarIssue)
    inst2.supported = True
    inst2.issue_url = "https://example.com/?issue=2"
    inst2.git_provider = gitp
    inst2.qdrant = FakeQdrantClient()
    inst2.index_name = "idx"
    inst2.repo_name_for_index = "owner/repo"
    monkeypatch.setattr(inst2, "_process_issue", lambda issue_main: ("text", [], 2))

    res2 = await inst2.run()
    # After run, ensure original issue (2) got create_comment by this second run as well
    issue_main2 = gitp.repo_obj.get_issue(2)
    assert hasattr(issue_main2, "created")
    # It should include IssueTitle4 and formatted score "0.46"
    assert "IssueTitle4" in issue_main2.created
    assert "(score=0.46)" in issue_main2.created
