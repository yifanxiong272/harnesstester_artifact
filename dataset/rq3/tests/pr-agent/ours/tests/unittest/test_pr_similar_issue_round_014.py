import importlib
import datetime
from types import SimpleNamespace
import pytest

# Tests target: pr_agent.tools.pr_similar_issue.PRSimilarIssue._update_index_with_issues
MODULE_PATH = "pr_agent.tools.pr_similar_issue"


def _make_fake_environment():
    mod = importlib.import_module(MODULE_PATH)

    # Fake Record, Corpus, Metadata, IssueLevel
    class FakeRecord:
        def __init__(self, id=None, text=None, metadata=None):
            self.id = id
            self.text = text
            self.metadata = metadata

    class FakeCorpus:
        def __init__(self):
            self._records = []

        def append(self, r):
            self._records.append(r)

        def model_dump(self):
            # return structure expected by the code: {"documents": [{"text": ...}, ...]}
            return {"documents": [{"text": getattr(r, "text", None)} for r in self._records]}

    class FakeMetadata:
        def __init__(self, repo=None, username=None, created_at=None, level=None):
            self.repo = repo
            self.username = username
            self.created_at = created_at
            self.level = level

    class FakeIssueLevel:
        ISSUE = "ISSUE"
        COMMENT = "COMMENT"

    # Fake token handler
    class FakeTokenHandler:
        def count_tokens(self, s):
            if s is None:
                return 0
            return len(str(s).split())

    # Fake DataFrame to emulate minimal pandas behavior used in the function
    class FakeDF:
        def __init__(self, documents):
            # documents is a list of dicts with at least 'text' key
            self._documents = documents

        def __getitem__(self, key):
            # Return an object that has .values attribute similar to pandas Series
            return SimpleNamespace(values=[d.get(key) for d in self._documents])

        # allow assignment like df["values"] = embeds (store it for possible inspection)
        def __setitem__(self, key, value):
            # store on instance for tests if needed
            setattr(self, f"_{key}", value)

    # Fake Dataset and DatasetMetadata
    class FakeDataset:
        def __init__(self, df, meta):
            self.df = df
            self.meta = meta

        def to_pinecone_index(self, index_name, api_key=None, environment=None):
            # expose last call on module for assertions
            mod._last_to_pinecone = (index_name, api_key, environment)

        def _upsert_to_index(self, index_name, namespace, batch_size, concurrency):
            mod._last_upsert_args = (index_name, namespace, batch_size, concurrency)

        @classmethod
        def from_pandas(cls, df, meta):
            return cls(df, meta)

    class FakeDatasetMetadata:
        @classmethod
        def empty(cls):
            inst = SimpleNamespace()
            inst.dense_model = SimpleNamespace()
            inst.dense_model.dimension = None
            return inst

    # Fake openai embedding: default behavior
    class FakeOpenAIEmbedding:
        @staticmethod
        def create(input, engine=None):
            items = input if isinstance(input, list) else [input]
            return {"data": [{"embedding": [1, 2, 3]} for _ in items]}

    fake_openai = SimpleNamespace(Embedding=FakeOpenAIEmbedding)

    # Fake get_settings
    def fake_get_settings():
        s = SimpleNamespace()
        s.openai = SimpleNamespace(key="fake-key")
        s.pinecone = SimpleNamespace(api_key="pine-key", environment="pine-env")
        return s

    # Fake pinecone module
    fake_pinecone = SimpleNamespace()

    def fake_pinecone_init(api_key=None, environment=None):
        fake_pinecone.inited = (api_key, environment)

    fake_pinecone.init = fake_pinecone_init

    # Fake logger
    class FakeLogger:
        def __init__(self):
            self.infos = []
            self.errors = []

        def info(self, msg):
            self.infos.append(msg)

        def error(self, msg):
            self.errors.append(msg)

    fake_logger = FakeLogger()

    # Patch module symbols where they are resolved in the implementation
    mod.Corpus = FakeCorpus
    mod.Record = FakeRecord
    mod.Metadata = FakeMetadata
    mod.IssueLevel = FakeIssueLevel
    mod.Dataset = FakeDataset
    mod.DatasetMetadata = FakeDatasetMetadata
    mod.openai = fake_openai
    mod.get_settings = fake_get_settings
    mod.pinecone = fake_pinecone
    mod.get_logger = lambda: fake_logger
    mod.MODEL = getattr(mod, "MODEL", "test-model")
    mod.MAX_TOKENS = getattr(mod, "MAX_TOKENS", {mod.MODEL: 10000})
    mod.get_max_tokens = lambda m: 10000
    # Avoid sleeping delays
    mod.time.sleep = lambda s: None
    # Provide a minimal pandas-like API
    mod.pd = SimpleNamespace(DataFrame=lambda documents: FakeDF(documents))

    return mod, FakeTokenHandler(), fake_logger


@pytest.fixture
def env():
    return _make_fake_environment()


def _make_issue(pull_request=False, user_login="alice", created_at=None):
    class FakeUser:
        def __init__(self, login):
            self.login = login

    class FakeIssue:
        def __init__(self, pull_request, user, created_at):
            self.pull_request = pull_request
            self.user = user
            self.created_at = created_at

    return FakeIssue(pull_request, FakeUser(user_login), created_at or datetime.datetime(2020, 1, 1))


def test_update_index_with_issues_upsert_false_round_014(env, monkeypatch):
    mod, token_handler, fake_logger = env

    PRSimilarIssue = importlib.import_module(MODULE_PATH).PRSimilarIssue
    inst = object.__new__(PRSimilarIssue)
    inst.token_handler = token_handler
    inst.max_issues_to_scan = 1000
    inst.index_name = "idx"

    class FakeComment:
        def __init__(self, body):
            self.body = body

    def fake_process_issue(issue):
        # produce an issue string and a comment with many words to be accepted
        return ("issue text for indexing", [FakeComment("this comment has more than ten words to be included in the index for sure")], 7)

    monkeypatch.setattr(inst, "_process_issue", fake_process_issue, raising=False)

    issues = [
        _make_issue(pull_request=True),
        _make_issue(pull_request=False)
    ]

    def bulk_embedding(input, engine=None):
        items = input if isinstance(input, list) else [input]
        return {"data": [{"embedding": [1, 2, 3]} for _ in items]}

    mod.openai.Embedding.create = staticmethod(bulk_embedding)

    # Run function under test with upsert=False
    inst._update_index_with_issues(issues, repo_name_for_index="repoX", upsert=False)

    # Assertions:
    # - module recorded a to_pinecone_index call
    assert hasattr(mod, "_last_to_pinecone") and mod._last_to_pinecone[0] == inst.index_name
    # - logger should contain 'Creating index' or 'Done' info
    assert any("Creating index" in i or "Creating index from scratch" in i for i in fake_logger.infos) or any("Done" in i for i in fake_logger.infos)


def test_update_index_with_issues_upsert_true_and_fallback_round_014(env, monkeypatch):
    mod, token_handler, fake_logger = env
    PRSimilarIssue = importlib.import_module(MODULE_PATH).PRSimilarIssue

    inst = object.__new__(PRSimilarIssue)
    inst.token_handler = token_handler
    inst.max_issues_to_scan = 1000
    inst.index_name = "idx"

    class FakeComment:
        def __init__(self, body):
            self.body = body

    def fake_process_issue(issue):
        # Return an issue string and two comments: first short (skipped), second long (included)
        return ("issue text small", [
            FakeComment("short one"),
            FakeComment("this is a sufficiently long comment body that will be included by the code path for sure")
        ], 21)

    monkeypatch.setattr(inst, "_process_issue", fake_process_issue, raising=False)

    issues = [_make_issue(pull_request=False)]

    calls = {"bulk": 0, "per_item": 0}

    def bulk_raise(input, engine=None):
        calls["bulk"] += 1
        raise Exception("bulk embedding failed")

    def per_item(input, engine=None):
        calls["per_item"] += 1
        items = input if isinstance(input, list) else [input]
        return {"data": [{"embedding": [9, 9]} for _ in items]}

    def embedding_bridge(input, engine=None):
        if isinstance(input, list) and len(input) == 1:
            return per_item(input, engine=engine)
        return bulk_raise(input, engine=engine)

    mod.openai.Embedding.create = staticmethod(embedding_bridge)

    # Ensure pinecone.inited gets recorded
    mod.pinecone.inited = None

    inst._update_index_with_issues(issues, repo_name_for_index="repoY", upsert=True)

    # Oracle assertions:
    assert mod.pinecone.inited == (mod.get_settings().pinecone.api_key, mod.get_settings().pinecone.environment)
    assert any("Upserting index" in msg or "Upserting index..." in msg for msg in fake_logger.infos) or any("Upserting" in msg for msg in fake_logger.infos)
    assert calls["per_item"] >= 1
