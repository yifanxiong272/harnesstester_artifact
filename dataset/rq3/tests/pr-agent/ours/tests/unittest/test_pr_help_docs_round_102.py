import types
import pytest

import pr_agent.tools.pr_help_docs as ph
from pr_agent.tools.pr_help_docs import PRHelpDocs


class DummyLogger:
    def __init__(self):
        self.info_calls = []
        self.exception_calls = []

    def info(self, *args, **kwargs):
        self.info_calls.append((args, kwargs))

    def exception(self, *args, **kwargs):
        self.exception_calls.append((args, kwargs))


def make_instance(return_as_string: bool = False):
    # create PRHelpDocs instance without running __init__
    inst = PRHelpDocs.__new__(PRHelpDocs)
    # minimal attributes used by _format_model_answer
    inst.repo_url = "git://repo"
    inst.repo_url_given_explicitly = False
    inst.repo_desired_branch = "main"
    inst.question = "What is X?"
    inst.supported_doc_exts = [".md"]
    inst.return_as_string = return_as_string
    # a git_provider object with required methods
    class GP:
        def __init__(self):
            self.called = {}

        def get_canonical_url_parts(self, repo_git_url=None, desired_branch=None):
            # record parameters and return deterministic parts
            self.called['get_canonical_url_parts'] = (repo_git_url, desired_branch)
            return ("https://prefix/", "/suffix")

        def is_supported(self, _):
            # default; tests override if needed
            return False

    inst.git_provider = GP()
    return inst


def test_return_as_string_returns_answer_round_102(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(ph, "get_logger", lambda: logger)

    # stub format_markdown_q_and_a_response to return a non-empty answer
    captured = {}

    def fake_format(question, response_str, relevant_sections, supported_suffixes, prefix, suffix):
        # record inputs to assert later
        captured['args'] = (question, response_str, relevant_sections, tuple(supported_suffixes), prefix, suffix)
        return "Q: ...\nA: original answer"

    monkeypatch.setattr(ph, "format_markdown_q_and_a_response", fake_format)

    # stub modify_answer_section to transform the answer so we can detect it
    def fake_modify(ans):
        captured['modified_input'] = ans
        return "💡 Automated answer\n" + ans

    monkeypatch.setattr(ph, "modify_answer_section", fake_modify)

    # instance that requests early string return
    inst = make_instance(return_as_string=True)

    # call method
    result = PRHelpDocs._format_model_answer(inst, response_str="model response", relevant_sections=[{"s": "1"}])

    # Assertions: returned value is the modified answer
    assert result.startswith("💡 Automated answer"), "Expected modify_answer_section output to be returned"

    # format_markdown_q_and_a_response should have been called with expected captured question
    assert captured['args'][0] == inst.question
    assert captured['args'][1] == "model response"

    # get_logger().info should have been invoked for the Chat help docs answer path
    assert any("Chat help docs answer" in (args[0] if args else "") for args, kwargs in logger.info_calls), "logger.info not called with Chat help docs answer"


def test_no_answer_returns_empty_round_102(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(ph, "get_logger", lambda: logger)

    # format returns empty -> no answer
    monkeypatch.setattr(ph, "format_markdown_q_and_a_response", lambda *a, **k: "")
    # modify_answer_section should not be called; set a sentinel that would raise if called
    monkeypatch.setattr(ph, "modify_answer_section", lambda a: (_ for _ in ()).throw(AssertionError("modify_answer_section should not be called")))

    inst = make_instance(return_as_string=False)

    result = PRHelpDocs._format_model_answer(inst, response_str="whatever", relevant_sections=[])

    assert result == "", "Expected empty string when no answer is produced"

    # logger.info should be called with 'No answer found'
    assert any("No answer found" in (args[0] if args else "") for args, kwargs in logger.info_calls), "logger.info not called with No answer found"


def test_appends_help_text_when_supported_round_102(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(ph, "get_logger", lambda: logger)

    # format returns an answer
    monkeypatch.setattr(ph, "format_markdown_q_and_a_response", lambda *a, **k: "base answer")
    monkeypatch.setattr(ph, "modify_answer_section", lambda a: a + " (modified)")

    # make settings enable help text
    monkeypatch.setattr(ph, "get_settings", lambda: types.SimpleNamespace(pr_help_docs=types.SimpleNamespace(enable_help_text=True)))

    # HelpMessage usage guide
    class HM:
        @staticmethod
        def get_help_docs_usage_guide():
            return "USAGE_GUIDE"

    monkeypatch.setattr(ph, "HelpMessage", HM)

    # instance with git_provider.is_supported returning True
    inst = make_instance(return_as_string=False)

    def is_supported_true(val):
        return True

    inst.git_provider.is_supported = is_supported_true

    result = PRHelpDocs._format_model_answer(inst, response_str="r", relevant_sections=[])

    # should contain base modified answer and the usage guide markup
    assert "base answer (modified)" in result
    assert "Tool usage guide:" in result or "USAGE_GUIDE" in result
    assert "USAGE_GUIDE" in result


def test_handles_exception_and_returns_empty_round_102(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(ph, "get_logger", lambda: logger)

    # make format raise an exception to hit the except branch
    def raising_format(*a, **k):
        raise RuntimeError("simulated")

    monkeypatch.setattr(ph, "format_markdown_q_and_a_response", raising_format)

    inst = make_instance(return_as_string=False)

    result = PRHelpDocs._format_model_answer(inst, response_str="x", relevant_sections=[])

    assert result == "", "When an exception occurs, function should return empty string"
    # logger.exception should be called at least once
    assert len(logger.exception_calls) >= 1, "Expected logger.exception to be called on exception"
