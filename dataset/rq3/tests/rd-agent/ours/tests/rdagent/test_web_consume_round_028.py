import importlib
import types
import pytest

# import the module under test
web = importlib.import_module("rdagent.log.ui.web")

# Dummy classes and helpers to patch into the module so isinstance checks
# and constructions behave deterministically without external deps.
class DummyWindowBase:
    def __init__(self, *args, **kwargs):
        self.init_args = args
        self.init_kwargs = kwargs
        self.consumed = False
        self.last_msg = None

    def consume_msg(self, msg):
        self.consumed = True
        self.last_msg = msg


class DummyObjectsTabsWindow(DummyWindowBase):
    last_init = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # record what was used to create this object for assertions
        DummyObjectsTabsWindow.last_init = {
            "args": args,
            "kwargs": kwargs,
        }


class DummyContainer:
    def __init__(self):
        self.header_calls = []
        self.expanders = {}

    def header(self, *args, **kwargs):
        self.header_calls.append((args, kwargs))

    def expander(self, name):
        # return a sentinel object to simulate streamlit expander
        obj = object()
        self.expanders[name] = obj
        return obj


# Minimal dummy payload classes used in isinstance checks in the code under test
class Hypothesis:
    pass


class HypothesisFeedback:
    pass


class QlibFactorExperiment:
    pass


class QlibModelExperiment:
    pass


class FactorTask:
    def __init__(self, factor_name="f"):
        self.factor_name = factor_name


class ModelTask:
    def __init__(self, name="m"):
        self.name = name


class _TargetTask:
    def __init__(self, factor_name=None, name=None):
        self.factor_name = factor_name
        self.name = name


class FactorFBWorkspace:
    def __init__(self, target_task):
        self.target_task = target_task


class ModelFBWorkspace:
    def __init__(self, target_task):
        self.target_task = target_task


class FactorSingleFeedback:
    pass


class ModelSingleFeedback:
    pass


# Helper to create a minimal message-like object with tag and content attributes
def make_msg(tag, content):
    return types.SimpleNamespace(tag=tag, content=content)


@pytest.fixture(autouse=True)
def patch_module_classes(monkeypatch):
    """
    Patch names in the web module to deterministic local dummy classes.
    The real module imported different concrete classes; here we replace
    them with minimal stand-ins used by the tests.
    """
    # Patch the type-check targets
    monkeypatch.setattr(web, "Hypothesis", Hypothesis)
    monkeypatch.setattr(web, "HypothesisFeedback", HypothesisFeedback)
    monkeypatch.setattr(web, "QlibFactorExperiment", QlibFactorExperiment)
    monkeypatch.setattr(web, "QlibModelExperiment", QlibModelExperiment)
    monkeypatch.setattr(web, "FactorTask", FactorTask)
    monkeypatch.setattr(web, "ModelTask", ModelTask)
    monkeypatch.setattr(web, "FactorFBWorkspace", FactorFBWorkspace)
    monkeypatch.setattr(web, "ModelFBWorkspace", ModelFBWorkspace)
    monkeypatch.setattr(web, "FactorSingleFeedback", FactorSingleFeedback)
    monkeypatch.setattr(web, "ModelSingleFeedback", ModelSingleFeedback)

    # Patch window classes constructed inside consume_msg
    monkeypatch.setattr(web, "LLMWindow", DummyWindowBase)
    monkeypatch.setattr(web, "HypothesisWindow", DummyWindowBase)
    monkeypatch.setattr(web, "HypothesisFeedbackWindow", DummyWindowBase)
    monkeypatch.setattr(web, "QlibFactorExpWindow", DummyWindowBase)
    monkeypatch.setattr(web, "QlibModelExpWindow", DummyWindowBase)
    monkeypatch.setattr(web, "ObjectsTabsWindow", DummyObjectsTabsWindow)
    monkeypatch.setattr(web, "StWindow", DummyWindowBase)
    monkeypatch.setattr(web, "WorkspaceWindow", DummyWindowBase)
    monkeypatch.setattr(web, "FactorTaskWindow", DummyWindowBase)
    monkeypatch.setattr(web, "ModelTaskWindow", DummyWindowBase)
    monkeypatch.setattr(web, "FactorFeedbackWindow", DummyWindowBase)
    monkeypatch.setattr(web, "ModelFeedbackWindow", DummyWindowBase)

    yield


def test_llm_message_early_return_when_hidden_round_028():
    """
    If a message tag ends with 'llm_messages' and show_llm is False,
    consume_msg should return early and not replace current_win.
    """
    container = DummyContainer()
    win = web.SimpleTraceWindow(container, show_llm=False, show_common_logs=True)

    # put a sentinel current_win instance to detect no change
    sentinel = DummyWindowBase()
    win.current_win = sentinel

    msg = make_msg("session.llm_messages", "some content")

    # Call consume_msg and expect an early return (no change, no consume call)
    win.consume_msg(msg)

    assert win.current_win is sentinel, "current_win should not be changed when llm display disabled"


def test_header_and_hypothesis_window_round_028():
    """
    When tag depth increases and tag is not llm_messages, a header is written
    and Hypothesis content leads to HypothesisWindow creation and consume_msg called.
    """
    container = DummyContainer()
    # enable llm and common logs so nothing else short-circuits
    win = web.SimpleTraceWindow(container, show_llm=True, show_common_logs=True)

    # ensure current_tag is short so that len(msg.tag) > len(current_tag) triggers
    win.current_tag = "a"

    msg = make_msg("task.level", Hypothesis())

    win.consume_msg(msg)

    # header should have been called with the tag where dots replaced by arrow
    assert container.header_calls, "container.header should have been called for deeper tag"
    args, kwargs = container.header_calls[-1]
    expected_text = msg.tag.replace(".", " \u27a1 ")
    # header called with the converted text as first positional argument and divider=True
    assert args[0] == expected_text
    assert kwargs.get("divider") is True

    # HypothesisWindow is DummyWindowBase so current_win should be instance and it should have consumed the message
    assert isinstance(win.current_win, DummyWindowBase)
    assert win.current_win.consumed is True
    assert win.current_win.last_msg is msg


def test_list_empty_after_filter_returns_and_factor_workspace_then_feedback_round_028():
    """
    - A list content that becomes empty after filtering should return early.
    - Receiving a list of FactorFBWorkspace should create ObjectsTabsWindow and set evolving_tasks.
    - Subsequent FactorSingleFeedback list should create ObjectsTabsWindow with tab_names set to evolving_tasks.
    """
    container = DummyContainer()
    win = web.SimpleTraceWindow(container, show_llm=True, show_common_logs=True)

    # 1) empty-after-filter case
    sentinel = DummyWindowBase()
    win.current_win = sentinel
    msg_empty = make_msg("some.tag", [None, None])
    win.consume_msg(msg_empty)
    # Should return early and current_win remains the same sentinel
    assert win.current_win is sentinel

    # 2) FactorFBWorkspace list -> should set evolving_tasks and create ObjectsTabsWindow
    ft1 = _TargetTask(factor_name="factorA")
    ft2 = _TargetTask(factor_name="factorB")
    ws1 = FactorFBWorkspace(target_task=ft1)
    ws2 = FactorFBWorkspace(target_task=ft2)
    msg_fw = make_msg("work.factor", [ws1, ws2])

    win.consume_msg(msg_fw)

    # ObjectsTabsWindow.last_init was recorded by our dummy; the expander name should be 'Factor Workspaces'
    init_info = DummyObjectsTabsWindow.last_init
    assert init_info is not None, "ObjectsTabsWindow should have been constructed for FactorFBWorkspace"
    # the first arg expected is container.expander("Factor Workspaces") as set by the implementation
    args = init_info["args"]
    # verify evolving_tasks was populated
    assert win.evolving_tasks == ["factorA", "factorB"]

    # 3) FactorSingleFeedback uses previously set evolving_tasks as tab_names
    # Create a list with a FactorSingleFeedback object
    msg_ff = make_msg("feedback.factor", [FactorSingleFeedback()])
    win.consume_msg(msg_ff)

    init_info2 = DummyObjectsTabsWindow.last_init
    assert init_info2 is not None
    kwargs2 = init_info2["kwargs"]
    # verify tab_names kwarg passed equals the evolving_tasks list
    assert kwargs2.get("tab_names") == win.evolving_tasks


def test_common_logs_hidden_returns_round_028():
    """
    If the branch for common logs is reached but show_common_logs is False,
    consume_msg should return early without changing current_win.
    """
    container = DummyContainer()
    win = web.SimpleTraceWindow(container, show_llm=True, show_common_logs=False)
    sentinel = DummyWindowBase()
    win.current_win = sentinel

    # Choose a tag that does NOT end with llm_messages and a content that doesn't match other types,
    # forcing the final else: common logs branch.
    msg = make_msg("ordinary.log", "a plain log string")

    win.consume_msg(msg)

    assert win.current_win is sentinel, "current_win should not change when common logs display disabled"
