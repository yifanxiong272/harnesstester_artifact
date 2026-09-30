import asyncio
from types import SimpleNamespace
from pr_agent.tools.pr_code_suggestions import PRCodeSuggestions


class FakeLogger:
    def __init__(self, raise_on_info=False):
        self.raise_on_info = raise_on_info
        self.infos = []
        self.errors = []
        self.debugs = []
        self.warnings = []
        self.exceptions = []

    def info(self, *args, **kwargs):
        if self.raise_on_info:
            raise RuntimeError("logger info failed")
        self.infos.append((args, kwargs))

    def error(self, *args, **kwargs):
        self.errors.append((args, kwargs))

    def debug(self, *args, **kwargs):
        self.debugs.append((args, kwargs))

    def warning(self, *args, **kwargs):
        self.warnings.append((args, kwargs))

    def exception(self, *args, **kwargs):
        # record exceptions (stack/info) but do not raise
        self.exceptions.append((args, kwargs))


def _make_instance():
    # create instance without running initializer to avoid side effects
    inst = PRCodeSuggestions.__new__(PRCodeSuggestions)
    # bind method validate_one_liner_suggestion_not_repeating_code from class to instance
    inst.validate_one_liner_suggestion_not_repeating_code = (
        PRCodeSuggestions.validate_one_liner_suggestion_not_repeating_code.__get__(inst, PRCodeSuggestions)
    )
    return inst


def test_analyze_reflection_logging_success_round_091(monkeypatch):
    """When publish_output is True and suggestion has falsy score (0), logging uses score -1
    and label is lowercased and <br> replaced with space."""
    inst = _make_instance()

    # Setup data and feedback so length matches
    data = {
        "code_suggestions": [
            {
                "label": "My<BR>Label ",
                "existing_code": "old_code",
                "improved_code": "new_code",
            }
        ]
    }

    # feedback: suggestion_score present but relevant lines negative -> sets score to 0
    response_yaml = {"code_suggestions": [{"suggestion_score": 5, "why": "ok", "relevant_lines_start": -1, "relevant_lines_end": -1}]}

    # Patch load_yaml to return our prepared YAML
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.load_yaml", lambda s: response_yaml)

    # Patch settings: publish_output True
    settings = SimpleNamespace(
        config=SimpleNamespace(publish_output=True),
        pr_code_suggestions=SimpleNamespace(commitable_code_suggestions=True),
    )
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_settings", lambda: settings)

    # Patch logger
    fake_logger = FakeLogger()
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_logger", lambda: fake_logger)

    # Run async method
    asyncio.run(inst.analyze_self_reflection_response(data, "yaml-string-not-used"))

    # After execution, feedback had negative relevant lines -> suggestion score overridden to 0
    # Logging should have been invoked and recorded a statistics kwarg
    assert fake_logger.infos, "expected logger.info to be called"
    # Extract statistics dict from the first info call kwargs
    args, kwargs = fake_logger.infos[0]
    # The module calls info with keyword 'statistics'
    stats = kwargs.get("statistics")
    assert isinstance(stats, dict)
    # Because suggestion["score"] becomes 0 (falsy), score variable used in statistics should be -1
    assert stats["score"] == -1
    # Label should have been lowercased and '<br>' replaced with space
    assert stats["label"] == "my label"


def test_analyze_reflection_logging_raises_and_is_caught_round_091(monkeypatch):
    """If the logger.info call raises, the code should catch the exception and call logger.error."""
    inst = _make_instance()

    data = {
        "code_suggestions": [
            {"label": "L<br>", "existing_code": "x", "improved_code": "y"}
        ]
    }

    response_yaml = {"code_suggestions": [{"suggestion_score": 1, "why": "fine", "relevant_lines_start": 1, "relevant_lines_end": 2}]}
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.load_yaml", lambda s: response_yaml)

    settings = SimpleNamespace(
        config=SimpleNamespace(publish_output=True),
        pr_code_suggestions=SimpleNamespace(commitable_code_suggestions=True),
    )
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_settings", lambda: settings)

    # Logger that raises on info
    fake_logger = FakeLogger(raise_on_info=True)
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_logger", lambda: fake_logger)

    # Running should not raise despite logger throwing; it should be caught
    asyncio.run(inst.analyze_self_reflection_response(data, "yaml-string-not-used"))

    # After running, logger.error should have recorded the failed logging attempt
    assert fake_logger.errors, "expected logger.error to be called when logger.info raises"
    # Ensure one of the error messages mentions 'Failed to log suggestion statistics'
    error_msgs = " ".join(str(a) for a, k in fake_logger.errors)
    assert "Failed to log suggestion statistics" in error_msgs


def test_analyze_reflection_outer_exception_sets_default_score_round_091(monkeypatch):
    """If assigning suggestion score from feedback raises, outer except sets suggestion score to 7."""
    inst = _make_instance()

    # Prepare a suggestion that will cause KeyError when accessing suggestion_score in feedback
    data = {
        "code_suggestions": [
            {"label": "lbl", "existing_code": "e", "improved_code": "i"}
        ]
    }

    # feedback missing 'suggestion_score' key -> will raise KeyError inside try
    response_yaml = {"code_suggestions": [{}]}
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.load_yaml", lambda s: response_yaml)

    settings = SimpleNamespace(
        config=SimpleNamespace(publish_output=False),  # logging block will be skipped
        pr_code_suggestions=SimpleNamespace(commitable_code_suggestions=True),
    )
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_settings", lambda: settings)

    fake_logger = FakeLogger()
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_logger", lambda: fake_logger)

    asyncio.run(inst.analyze_self_reflection_response(data, "yaml-string-not-used"))

    # The function should have set suggestion score to 7 after catching the error
    # We can only inspect the mutated data structure passed in
    assert data["code_suggestions"][0].get("score") == 7
    assert data["code_suggestions"][0].get("score_why") == ""


def test_analyze_reflection_existing_equals_commitable_true_round_091(monkeypatch):
    """When existing_code == improved_code and commitable_code_suggestions is True,
    improved_code should be cleared and debug should be invoked."""
    inst = _make_instance()

    data = {
        "code_suggestions": [
            {"label": "lbl", "existing_code": "same", "improved_code": "same"}
        ]
    }

    response_yaml = {"code_suggestions": [{"suggestion_score": 3, "why": "ok", "relevant_lines_start": 1, "relevant_lines_end": 2}]}
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.load_yaml", lambda s: response_yaml)

    settings = SimpleNamespace(
        config=SimpleNamespace(publish_output=False),
        pr_code_suggestions=SimpleNamespace(commitable_code_suggestions=True),
    )
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_settings", lambda: settings)

    fake_logger = FakeLogger()
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_logger", lambda: fake_logger)

    asyncio.run(inst.analyze_self_reflection_response(data, "yaml-string-not-used"))

    # improved_code should have been cleared because commitable_code_suggestions is True
    assert data["code_suggestions"][0]["improved_code"] == ""
    # debug should have been called to note the edited improved suggestion
    assert fake_logger.debugs, "expected logger.debug to be called when codes are equal"


def test_analyze_reflection_existing_equals_commitable_false_round_091(monkeypatch):
    """When existing_code == improved_code and commitable_code_suggestions is False,
    existing_code should be cleared."""
    inst = _make_instance()

    data = {
        "code_suggestions": [
            {"label": "lbl", "existing_code": "same", "improved_code": "same"}
        ]
    }

    response_yaml = {"code_suggestions": [{"suggestion_score": 2, "why": "ok", "relevant_lines_start": 1, "relevant_lines_end": 2}]}
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.load_yaml", lambda s: response_yaml)

    settings = SimpleNamespace(
        config=SimpleNamespace(publish_output=False),
        pr_code_suggestions=SimpleNamespace(commitable_code_suggestions=False),
    )
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_settings", lambda: settings)

    fake_logger = FakeLogger()
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_logger", lambda: fake_logger)

    asyncio.run(inst.analyze_self_reflection_response(data, "yaml-string-not-used"))

    # existing_code should have been cleared because commitable_code_suggestions is False
    assert data["code_suggestions"][0]["existing_code"] == ""
    assert fake_logger.debugs, "expected logger.debug to be called when codes are equal"
