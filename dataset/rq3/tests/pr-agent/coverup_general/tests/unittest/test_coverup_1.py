# file: pr_agent/tools/pr_similar_issue.py:19-257
# asked: {"lines": [25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 36, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50, 51, 52, 55, 56, 57, 58, 59, 60, 61, 63, 64, 65, 66, 67, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 82, 83, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 105, 107, 108, 109, 111, 113, 114, 115, 116, 117, 118, 119, 121, 122, 123, 124, 125, 126, 128, 129, 130, 131, 133, 134, 136, 137, 138, 139, 140, 142, 143, 145, 146, 147, 149, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 170, 172, 173, 174, 176, 178, 179, 180, 181, 184, 185, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 199, 201, 202, 204, 205, 206, 207, 208, 209, 212, 213, 215, 216, 217, 218, 219, 222, 224, 225, 226, 227, 228, 229, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 247, 248, 249, 251, 253, 254, 255, 257], "branches": [[22, 25], [36, 37], [36, 113], [48, 49], [48, 52], [56, 57], [56, 63], [58, 59], [58, 63], [65, 66], [65, 69], [69, 70], [69, 72], [74, 75], [74, 77], [77, 78], [77, 85], [89, 90], [89, 107], [90, 91], [90, 92], [97, 98], [97, 101], [98, 97], [98, 99], [101, 102], [101, 105], [107, 108], [107, 111], [113, 114], [113, 178], [122, 123], [122, 128], [123, 124], [123, 128], [129, 130], [129, 133], [133, 134], [133, 136], [139, 140], [139, 142], [142, 143], [142, 151], [154, 155], [154, 172], [155, 156], [155, 157], [162, 163], [162, 166], [163, 162], [163, 164], [166, 167], [166, 170], [172, 173], [172, 176], [178, 0], [178, 179], [193, 194], [193, 197], [204, 205], [204, 212], [212, 213], [212, 215], [224, 225], [224, 231], [234, 235], [234, 253], [235, 236], [235, 237], [247, 248], [247, 251], [253, 254], [253, 257]]}
# gained: {"lines": [25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 36, 37, 38, 39, 40, 44, 45, 46, 55, 56, 63, 64, 65, 69, 72, 73, 74, 75, 77, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 101, 102, 103, 107, 108, 109, 113, 114, 115, 118, 119, 121, 122, 128, 129, 133, 136, 137, 138, 139, 140, 142, 151, 152, 153, 154, 155, 157, 158, 159, 160, 161, 162, 166, 167, 168, 172, 173, 174, 178, 179, 180, 181, 187, 188, 189, 190, 191, 199, 201, 202, 204, 212, 215, 216, 217, 218, 219, 222, 224, 231, 232, 233, 234, 235, 237, 238, 239, 240, 241, 242, 243, 244, 247, 248, 249, 253, 254, 255], "branches": [[22, 25], [36, 37], [36, 113], [56, 63], [65, 69], [69, 72], [74, 75], [77, 85], [89, 90], [89, 107], [90, 91], [90, 92], [97, 98], [97, 101], [98, 97], [101, 102], [107, 108], [113, 114], [113, 178], [122, 128], [129, 133], [133, 136], [139, 140], [142, 151], [154, 155], [154, 172], [155, 157], [162, 166], [166, 167], [172, 173], [178, 179], [204, 212], [212, 215], [224, 231], [234, 235], [234, 253], [235, 237], [247, 248], [253, 254]]}

import sys
import types
from types import SimpleNamespace
import pytest

from pr_agent.tools.pr_similar_issue import PRSimilarIssue


def make_settings(vectordb):
    settings = SimpleNamespace()
    settings.config = SimpleNamespace(git_provider="github")
    settings.CONFIG = SimpleNamespace(CLI_MODE=False)
    pr_sim = SimpleNamespace()
    pr_sim.vectordb = vectordb
    pr_sim.max_issues_to_scan = 10
    pr_sim.force_update_dataset = False
    pr_sim.skip_comments = True  # avoid calling issue.get_comments in tests
    settings.pr_similar_issue = pr_sim
    settings.pinecone = SimpleNamespace(api_key="key", environment="env")
    settings.lancedb = SimpleNamespace(uri="fake://uri")
    settings.qdrant = SimpleNamespace(api_key="qk", url="http://qdrant")
    return settings


class FakeIssue:
    def __init__(self, number, pull_request=False):
        self.number = number
        self.pull_request = pull_request
        self.body = f"body {number}"
        self.title = f"title {number}"

    def get_comments(self):
        return []


class FakeRepoObj:
    def __init__(self, full_name, issues):
        self.full_name = full_name
        self._issues = issues

    def get_issues(self, state='all'):
        return list(self._issues)

    def get_issue(self, number):
        class C:
            def create_comment(self, txt):
                self.last_comment = txt
        return C()


class FakeGitProvider:
    def __init__(self, repo_obj):
        self.repo_obj = repo_obj
        self.github_client = SimpleNamespace(get_repo=lambda name: repo_obj)
        self.repo = None

    def _parse_issue_url(self, tail):
        return (self.repo_obj.full_name, int(tail))


def setup_fake_git_provider(monkeypatch, repo_obj):
    def factory():
        return FakeGitProvider(repo_obj)
    monkeypatch.setattr("pr_agent.tools.pr_similar_issue.get_git_provider", lambda: factory)


def setup_get_settings(monkeypatch, settings):
    monkeypatch.setattr("pr_agent.tools.pr_similar_issue.get_settings", lambda: settings)


def setup_token_handler(monkeypatch):
    class DummyTokenHandler:
        def __init__(self):
            pass
    monkeypatch.setattr("pr_agent.tools.pr_similar_issue.TokenHandler", DummyTokenHandler)


def cleanup_modules(*names):
    for name in names:
        if name in sys.modules:
            del sys.modules[name]


def test_prsimilarissue_pinecone_updates(monkeypatch):
    settings = make_settings("pinecone")
    setup_get_settings(monkeypatch, settings)

    issues = [FakeIssue(1, pull_request=False), FakeIssue(2, pull_request=True)]
    repo_obj = FakeRepoObj("Owner/Repo", issues)
    setup_fake_git_provider(monkeypatch, repo_obj)
    setup_token_handler(monkeypatch)

    pinecone = types.SimpleNamespace()
    pinecone._indexes = ["codium-ai-pr-agent-issues"]

    def init(api_key=None, environment=None):
        pass

    def list_indexes():
        return list(pinecone._indexes)

    class FakeIndex:
        def __init__(self, index_name=None):
            self.index_name = index_name

        def fetch(self, ids):
            id0 = ids[0] if ids else ""
            if id0.startswith("example_issue_"):
                return SimpleNamespace(to_dict=lambda: {"vectors": {"v0": {"metadata": {"repo": "some-other-repo"}}}})
            else:
                return SimpleNamespace(to_dict=lambda: {"vectors": {"v1": {"metadata": {"repo": "not-our-repo"}}}})

    pinecone.init = init
    pinecone.list_indexes = list_indexes
    pinecone.Index = FakeIndex

    pinecone_datasets = types.SimpleNamespace(Dataset=object, DatasetMetadata=object)
    pandas = types.SimpleNamespace()

    sys.modules['pinecone'] = pinecone
    sys.modules['pandas'] = pandas
    sys.modules['pinecone_datasets'] = pinecone_datasets

    monkeypatch.setattr("pr_agent.tools.pr_similar_issue.get_logger", lambda: SimpleNamespace(info=lambda *a, **k: None))

    called = {}
    def fake_update_index(self, issues_list, repo_name_for_index, upsert=False):
        called['issues'] = issues_list
        called['repo'] = repo_name_for_index
        called['upsert'] = upsert

    monkeypatch.setattr("pr_agent.tools.pr_similar_issue.PRSimilarIssue._update_index_with_issues", fake_update_index)

    try:
        obj = PRSimilarIssue("dummy_issue=1", ai_handler=None, args=[])
    finally:
        cleanup_modules('pinecone', 'pandas', 'pinecone_datasets')

    assert 'issues' in called
    assert isinstance(called['issues'], list)
    assert len(called['issues']) == 1
    assert called['issues'][0].number == 1
    assert called['repo'] == repo_obj.full_name.lower().replace('/', '-').replace('_/', '-')
    assert isinstance(called['upsert'], bool)


def test_prsimilarissue_lancedb_and_qdrant(monkeypatch):
    issues = [FakeIssue(1, pull_request=False), FakeIssue(2, pull_request=False)]
    repo_obj = FakeRepoObj("Owner/Repo", issues)
    setup_fake_git_provider(monkeypatch, repo_obj)
    setup_token_handler(monkeypatch)
    monkeypatch.setattr("pr_agent.tools.pr_similar_issue.get_logger", lambda: SimpleNamespace(info=lambda *a, **k: None))

    # ---- Lancedb branch ----
    settings = make_settings("lancedb")
    setup_get_settings(monkeypatch, settings)

    class FakeTable:
        def __init__(self, name):
            self.name = name
            self._len = 2

        def __len__(self):
            return self._len

        class _Search:
            def __init__(self, table):
                self.table = table
                self._where = None
                self._limit_count = None

            def limit(self, n):
                self._limit_count = n
                return self

            def where(self, q):
                self._where = q
                return self

            def to_list(self):
                if "example_issue_" in (self._where or ""):
                    return [{"vector": True}]
                return []

        def search(self):
            return FakeTable._Search(self)

    class FakeDB:
        def __init__(self):
            self._tables = {"codium-ai-pr-agent-issues": FakeTable("codium-ai-pr-agent-issues")}

        def table_names(self):
            return list(self._tables.keys())

        def __getitem__(self, name):
            return self._tables[name]

        def drop_table(self, name):
            self._tables.pop(name, None)

    def fake_connect(uri):
        return FakeDB()

    fake_lancedb = types.SimpleNamespace(connect=fake_connect)
    sys.modules['lancedb'] = fake_lancedb

    called_table = {}
    def fake_update_table(self, issues_list, repo_name_for_index, ingest=False):
        called_table['issues'] = issues_list
        called_table['repo'] = repo_name_for_index
        called_table['ingest'] = ingest

    monkeypatch.setattr("pr_agent.tools.pr_similar_issue.PRSimilarIssue._update_table_with_issues", fake_update_table)

    try:
        obj = PRSimilarIssue("dummy_issue=1", ai_handler=None, args=[])
    finally:
        cleanup_modules('lancedb')

    assert 'issues' in called_table
    assert isinstance(called_table['issues'], list)
    assert len(called_table['issues']) == 2
    assert called_table['repo'] == repo_obj.full_name.lower().replace('/', '-').replace('_/', '-')

    # ---- Qdrant branch ----
    settings = make_settings("qdrant")
    setup_get_settings(monkeypatch, settings)

    qdrant_client = types.SimpleNamespace()
    class Distance:
        COSINE = "cosine"

    class MatchValue:
        def __init__(self, value):
            self.value = value

    class FieldCondition:
        def __init__(self, key=None, match=None):
            self.key = key
            self.match = match

    class Filter:
        def __init__(self, must=None):
            self.must = must or []

    class VectorParams:
        def __init__(self, size=None, distance=None):
            self.size = size
            self.distance = distance

    class FakeCountResp:
        def __init__(self, count):
            self.count = count

    class FakeQdrantClient:
        def __init__(self, url=None, api_key=None):
            pass

        def collection_exists(self, collection_name=None):
            return True

        def create_collection(self, collection_name=None, vectors_config=None):
            return None

        def count(self, collection_name=None, count_filter=None):
            vals = []
            for fc in getattr(count_filter, "must", []):
                match = getattr(fc, "match", None)
                if match is not None:
                    val = getattr(match, "value", "")
                    vals.append(val)
            for v in vals:
                if "example_issue_" in str(v):
                    return FakeCountResp(1)
            return FakeCountResp(0)

    qdrant_client.QdrantClient = FakeQdrantClient
    qdrant_client.models = SimpleNamespace(Distance=Distance, FieldCondition=FieldCondition, Filter=Filter, MatchValue=MatchValue, PointStruct=object, VectorParams=VectorParams)

    sys.modules['qdrant_client'] = qdrant_client
    sys.modules['qdrant_client.models'] = qdrant_client.models

    called_qdrant = {}
    def fake_update_qdrant(self, issues_list, repo_name_for_index, ingest=False):
        called_qdrant['issues'] = issues_list
        called_qdrant['repo'] = repo_name_for_index
        called_qdrant['ingest'] = ingest

    monkeypatch.setattr("pr_agent.tools.pr_similar_issue.PRSimilarIssue._update_qdrant_with_issues", fake_update_qdrant)

    try:
        obj = PRSimilarIssue("dummy_issue=1", ai_handler=None, args=[])
    finally:
        cleanup_modules('qdrant_client', 'qdrant_client.models')

    assert 'issues' in called_qdrant
    assert isinstance(called_qdrant['issues'], list)
    assert len(called_qdrant['issues']) == 2
    assert called_qdrant['repo'] == repo_obj.full_name.lower().replace('/', '-').replace('_/', '-')
