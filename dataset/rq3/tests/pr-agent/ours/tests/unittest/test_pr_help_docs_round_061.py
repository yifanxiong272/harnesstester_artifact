import pytest
import types

import pr_agent.tools.pr_help_docs as ph


class DummyLogger:
    def __init__(self):
        self.warnings = []
        self.debugs = []
        self.infos = []
        self.exceptions = []

    def warning(self, msg):
        self.warnings.append(msg)

    def debug(self, msg):
        self.debugs.append(msg)

    def info(self, msg):
        self.infos.append(msg)

    def exception(self, msg):
        self.exceptions.append(msg)


class DummyConfig:
    def __init__(self, model):
        self.model = model


class DummySettings:
    def __init__(self, model):
        self.config = DummyConfig(model)


def make_pr_help_docs_with_token_handler(token_counter_callable):
    # Create PRHelpDocs instance without running its real __init__
    inst = object.__new__(ph.PRHelpDocs)
    # token_handler object with the required method
    th = types.SimpleNamespace()
    th.count_tokens = token_counter_callable
    inst.token_handler = th
    return inst


def test_trim_when_len_exceeds_and_only_return_round_061(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(ph, "get_logger", lambda: logger)

    docs = "x" * 10
    inst = make_pr_help_docs_with_token_handler(lambda *a, **k: 0)

    # Call with only_return_if_trim_needed True and max_allowed smaller than len(docs)
    res = ph.PRHelpDocs._trim_docs_input(inst, docs, max_allowed_txt_input=5, only_return_if_trim_needed=True)

    assert res is True
    # ensure a warning was emitted about trimming
    assert any("exceeds the current returned limit" in w for w in logger.warnings)


def test_trim_len_exceeds_and_trim_and_return_doc_round_061(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(ph, "get_logger", lambda: logger)

    # Ensure model is recognized in MAX_TOKENS path
    monkeypatch.setitem(ph.MAX_TOKENS, "test-model", 10000)
    monkeypatch.setattr(ph, "get_settings", lambda: DummySettings("test-model"))

    # token count will be small after trimming
    def token_counter(s, force_accurate=True):
        # confirm that trimmed content is passed by observing length
        return len(s)

    inst = make_pr_help_docs_with_token_handler(token_counter)

    docs = "abcdefghij"
    res = ph.PRHelpDocs._trim_docs_input(inst, docs, max_allowed_txt_input=5, only_return_if_trim_needed=False)

    assert isinstance(res, str)
    assert res == docs[:5]
    assert any("Estimated token count" in d for d in logger.debugs)


def test_token_count_exceeds_only_return_true_round_061(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(ph, "get_logger", lambda: logger)

    # Put model in MAX_TOKENS with a value so threshold (max-delta) is small
    monkeypatch.setitem(ph.MAX_TOKENS, "big-model", 6000)
    monkeypatch.setattr(ph, "get_settings", lambda: DummySettings("big-model"))

    # token count above threshold (6000 - 5000 = 1000)
    def token_counter(s, force_accurate=True):
        return 2000

    inst = make_pr_help_docs_with_token_handler(token_counter)

    docs = "short"
    res = ph.PRHelpDocs._trim_docs_input(inst, docs, max_allowed_txt_input=100, only_return_if_trim_needed=True)

    assert res is True
    # should have logged debug about estimated tokens
    assert any("Estimated token count" in d for d in logger.debugs)


def test_token_count_exceeds_and_clean_clip_return_doc_round_061(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(ph, "get_logger", lambda: logger)

    # Ensure model is NOT in MAX_TOKENS so get_max_tokens path is taken
    monkeypatch.setitem(ph.MAX_TOKENS, "some-other-model", 7000)
    # choose a model that is NOT present in MAX_TOKENS mapping
    monkeypatch.setattr(ph, "get_settings", lambda: DummySettings("unknown-model"))
    # stub get_max_tokens to a predictable value
    monkeypatch.setattr(ph, "get_max_tokens", lambda model: 7000)

    # token count above threshold (7000 - 5000 = 2000)
    def token_counter(s, force_accurate=True):
        return 3000

    inst = make_pr_help_docs_with_token_handler(token_counter)

    # patch clean_markdown_content and clip_tokens to observable behaviors
    monkeypatch.setattr(ph, "clean_markdown_content", lambda s: s + "-CLEANED")
    monkeypatch.setattr(ph, "clip_tokens", lambda s, limit, num_input_tokens=None: "CLIPPED")

    docs = "abc"
    res = ph.PRHelpDocs._trim_docs_input(inst, docs, max_allowed_txt_input=100, only_return_if_trim_needed=False)

    assert res == "CLIPPED"
    # info logger should have been called indicating we attempted to clip
    assert any("Attempting to clip text" in i for i in logger.infos)


def test_exception_propagated_round_061(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(ph, "get_logger", lambda: logger)

    def token_counter_raises(s, force_accurate=True):
        raise RuntimeError("boom")

    inst = make_pr_help_docs_with_token_handler(token_counter_raises)

    with pytest.raises(RuntimeError, match="boom"):
        ph.PRHelpDocs._trim_docs_input(inst, "abc", max_allowed_txt_input=100, only_return_if_trim_needed=False)

    # ensure the exception was logged
    assert len(logger.exceptions) == 1
