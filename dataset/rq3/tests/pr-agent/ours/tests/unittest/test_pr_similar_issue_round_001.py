import sys
from types import ModuleType, SimpleNamespace
import pytest

import pr_agent.tools.pr_similar_issue as psim


class DummyLogger:
    def info(self, *args, **kwargs):
        pass


class DummyTokenHandler:
    def __init__(self):
        pass


def make_provider(repo_full_name="owner/repo", issue_number=123, record_comment=None):
    repo_obj = SimpleNamespace()
    repo_obj.full_name = repo_full_name

    def get_issue(n):
        def create_comment(msg):
            if record_comment is not None:
                record_comment.append(msg)
        return SimpleNamespace(create_comment=create_comment)

    repo_obj.get_issue = get_issue
    repo_obj.get_issues = lambda state='all': []
    github_client = SimpleNamespace(get_repo=lambda name: repo_obj)

    provider = SimpleNamespace()
    provider.github_client = github_client
    provider._parse_issue_url = lambda x: (repo_full_name, issue_number)
    provider.repo_obj = repo_obj
    return provider


def _inject_dummy_modules(names):
    """Insert dummy modules into sys.modules with the specific attributes the production code imports.

    Returns list of inserted module names for cleanup.
    """
    inserted = []
    for n in names:
        if n in sys.modules:
            continue
        m = ModuleType(n)
        # Provide specific attributes depending on module name so 'from X import Y' works
        if n == 'pinecone_datasets':
            # Add Dataset and DatasetMetadata so 'from pinecone_datasets import Dataset, DatasetMetadata' succeeds
            class Dataset:
                def __init__(self, *a, **k):
                    pass
            class DatasetMetadata:
                def __init__(self, *a, **k):
                    pass
            m.Dataset = Dataset
            m.DatasetMetadata = DatasetMetadata
        if n == 'pinecone':
            # provide names so import pinecone succeeds; detailed behavior not needed for these tests
            def init(*a, **k):
                return None
            def list_indexes():
                return []
            class Index:
                def __init__(self, *a, **k):
                    pass
                def fetch(self, *a, **k):
                    return SimpleNamespace(to_dict=lambda: {"vectors": {}})
            m.init = init
            m.list_indexes = list_indexes
            m.Index = Index
        if n == 'pandas':
            # minimal placeholder
            class DataFrame:
                pass
            m.DataFrame = DataFrame

        if n == 'qdrant_client':
            # module placeholder
            class QdrantClient:
                def __init__(self, *a, **k):
                    pass
                def collection_exists(self, *a, **k):
                    return False
                def create_collection(self, *a, **k):
                    pass
                def count(self, *a, **k):
                    return SimpleNamespace(count=0)
            m.QdrantClient = QdrantClient
        if n == 'qdrant_client.models':
            # provide all names imported in production code
            class Distance:
                COSINE = 'cosine'
            class FieldCondition:
                def __init__(self, *a, **k):
                    pass
            class Filter:
                def __init__(self, *a, **k):
                    pass
            class MatchValue:
                def __init__(self, *a, **k):
                    pass
            class PointStruct:
                def __init__(self, *a, **k):
                    pass
            class VectorParams:
                def __init__(self, *a, **k):
                    pass
            m.Distance = Distance
            m.FieldCondition = FieldCondition
            m.Filter = Filter
            m.MatchValue = MatchValue
            m.PointStruct = PointStruct
            m.VectorParams = VectorParams
        sys.modules[n] = m
        inserted.append(n)
    return inserted


def _cleanup_dummy_modules(names):
    for n in names:
        if n in sys.modules:
            del sys.modules[n]


def test_not_supported_round_001(monkeypatch):
    fake_settings = SimpleNamespace()
    fake_settings.config = SimpleNamespace(git_provider="gitlab")
    monkeypatch.setattr(psim, 'get_settings', lambda: fake_settings)
    monkeypatch.setattr(psim, 'get_git_provider', lambda: (lambda: make_provider()))
    monkeypatch.setattr(psim, 'TokenHandler', DummyTokenHandler)
    monkeypatch.setattr(psim, 'get_logger', lambda: DummyLogger())

    obj = psim.PRSimilarIssue("http://example.com?issue=1", ai_handler=None, args=None)
    assert hasattr(obj, 'supported')
    assert obj.supported is False


def test_pinecone_missing_api_settings_triggers_comment_and_exception_round_001(monkeypatch):
    comments = []
    fake_settings = SimpleNamespace()
    fake_settings.config = SimpleNamespace(git_provider="github")
    fake_settings.CONFIG = SimpleNamespace(CLI_MODE=False)
    fake_settings.pr_similar_issue = SimpleNamespace(vectordb="pinecone", max_issues_to_scan=5, force_update_dataset=False)
    # ensure pinecone namespace exists but lacks api_key/environment to trigger the later except
    fake_settings.pinecone = SimpleNamespace()

    monkeypatch.setattr(psim, 'get_settings', lambda: fake_settings)
    provider = make_provider(record_comment=comments)
    monkeypatch.setattr(psim, 'get_git_provider', lambda: (lambda: provider))
    monkeypatch.setattr(psim, 'TokenHandler', DummyTokenHandler)
    monkeypatch.setattr(psim, 'get_logger', lambda: DummyLogger())

    # Inject dummy modules with the expected symbols so imports succeed
    inserted = _inject_dummy_modules(['pandas', 'pinecone', 'pinecone_datasets'])
    try:
        with pytest.raises(Exception) as exc:
            psim.PRSimilarIssue("http://example.com?issue=1", ai_handler=None, args=None)
        # Now the exception should be the missing credential exception raised after imports
        assert "Please set pinecone api key and environment in secrets file" in str(exc.value)
        assert any("Please set pinecone api key and environment in secrets file" in c for c in comments)
    finally:
        _cleanup_dummy_modules(inserted)


def test_qdrant_missing_api_settings_triggers_comment_and_exception_round_001(monkeypatch):
    comments = []
    fake_settings = SimpleNamespace()
    fake_settings.config = SimpleNamespace(git_provider="github")
    fake_settings.CONFIG = SimpleNamespace(CLI_MODE=False)
    fake_settings.pr_similar_issue = SimpleNamespace(vectordb="qdrant", max_issues_to_scan=5, force_update_dataset=False)
    fake_settings.qdrant = SimpleNamespace()

    monkeypatch.setattr(psim, 'get_settings', lambda: fake_settings)
    provider = make_provider(record_comment=comments)
    monkeypatch.setattr(psim, 'get_git_provider', lambda: (lambda: provider))
    monkeypatch.setattr(psim, 'TokenHandler', DummyTokenHandler)
    monkeypatch.setattr(psim, 'get_logger', lambda: DummyLogger())

    inserted = _inject_dummy_modules(['qdrant_client', 'qdrant_client.models'])
    try:
        with pytest.raises(Exception) as exc:
            psim.PRSimilarIssue("http://example.com?issue=1", ai_handler=None, args=None)
        assert "Please set qdrant url and api key in secrets file" in str(exc.value)
        assert any("Please set qdrant url and api key in secrets file" in c for c in comments)
    finally:
        _cleanup_dummy_modules(inserted)
