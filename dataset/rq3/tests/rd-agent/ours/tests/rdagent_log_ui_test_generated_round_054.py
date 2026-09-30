import types
import pytest

import rdagent.log.ui.web as web


class FakeObjectsTabsWindow:
    """Fake replacement for ObjectsTabsWindow used to capture constructor args and consume_msg calls."""
    instances = []

    def __init__(self, container, inner_class=None, mapper=None, tab_names=None):
        # store what was passed for assertions
        self.container = container
        self.inner_class = inner_class
        self.mapper = mapper
        self.tab_names = tab_names
        self.consumed = False
        FakeObjectsTabsWindow.instances.append(self)

    def consume_msg(self, msg):
        # mark that consume_msg was invoked
        self.consumed = True


class FakeContainer:
    def __init__(self):
        self.markdown_calls = []
        # some code expects container.container() to exist
        self._inner = object()

    def markdown(self, text):
        self.markdown_calls.append(text)

    def container(self):
        return self._inner


class FakeFactorWorkspace:
    def __init__(self, factor_name):
        class Task:
            def __init__(self, factor_name):
                self.factor_name = factor_name

        self.target_task = Task(factor_name)


class FakeModelWorkspace:
    def __init__(self, name):
        class Task:
            def __init__(self, name):
                self.name = name

        self.target_task = Task(name)


class FakeFactorFeedback:
    pass


class FakeModelFeedback:
    pass


class DummyWindowClasses:
    # simple placeholders to be passed as inner_class
    class WorkspaceWindow:
        pass

    class FactorFeedbackWindow:
        pass

    class ModelFeedbackWindow:
        pass


def setup_module_patch(monkeypatch):
    # Patch the module-level symbols so that isinstance checks and constructor calls
    # in EvolvingWindow.resolve to our fakes
    FakeObjectsTabsWindow.instances.clear()
    monkeypatch.setattr(web, "ObjectsTabsWindow", FakeObjectsTabsWindow, raising=True)
    monkeypatch.setattr(web, "FactorFBWorkspace", FakeFactorWorkspace, raising=True)
    monkeypatch.setattr(web, "ModelFBWorkspace", FakeModelWorkspace, raising=True)
    monkeypatch.setattr(web, "FactorSingleFeedback", FakeFactorFeedback, raising=True)
    monkeypatch.setattr(web, "ModelSingleFeedback", FakeModelFeedback, raising=True)
    # patch window classes referenced as inner_class/args
    monkeypatch.setattr(web, "WorkspaceWindow", DummyWindowClasses.WorkspaceWindow, raising=True)
    monkeypatch.setattr(web, "FactorFeedbackWindow", DummyWindowClasses.FactorFeedbackWindow, raising=True)
    monkeypatch.setattr(web, "ModelFeedbackWindow", DummyWindowClasses.ModelFeedbackWindow, raising=True)


def test_evolving_code_empty_content_round_054(monkeypatch):
    """When evolving code tag contains only falsy items after filtering, consume_msg returns early without producing tabs."""
    setup_module_patch(monkeypatch)
    container = FakeContainer()
    win = web.EvolvingWindow(container)

    class Msg:
        tag = "something evolving code"

        def __init__(self, content):
            self.content = content

    # content list with falsy elements -> filtered to empty -> should return early
    msg = Msg([None, False, ""])  # all falsy

    # invoke
    win.consume_msg(msg)

    # Assertions: no markdown produced, no ObjectsTabsWindow constructed, evolving_tasks stays empty
    assert container.markdown_calls == []
    assert FakeObjectsTabsWindow.instances == []
    assert win.evolving_tasks == []


def test_evolving_code_factor_workspace_round_054(monkeypatch):
    """When first item is a FactorFBWorkspace, markdown called and ObjectsTabsWindow.consume_msg invoked; evolving_tasks updated."""
    setup_module_patch(monkeypatch)
    container = FakeContainer()
    win = web.EvolvingWindow(container)

    class Msg:
        tag = "prefix evolving code"

        def __init__(self, content):
            self.content = content

    # prepare content with one factor workspace and one falsy item that will be filtered out
    fw1 = FakeFactorWorkspace("factor_a")
    fw2 = FakeFactorWorkspace("factor_b")
    msg = Msg([fw1, fw2, None])

    # call
    win.consume_msg(msg)

    # Should have recorded markdown call for factor codes
    assert container.markdown_calls == ["**Factor Codes**"]

    # ObjectsTabsWindow should have been constructed and consumed the message
    assert len(FakeObjectsTabsWindow.instances) == 1
    inst = FakeObjectsTabsWindow.instances[0]
    assert inst.consumed is True

    # inner_class passed should be the WorkspaceWindow patched into the module
    assert inst.inner_class is web.WorkspaceWindow

    # mapper should be callable and when applied to items should return factor_name
    assert callable(inst.mapper)
    assert inst.mapper(fw1) == "factor_a"
    assert inst.mapper(fw2) == "factor_b"

    # evolving_tasks should be set to the list of factor names
    assert win.evolving_tasks == ["factor_a", "factor_b"]


def test_evolving_code_model_workspace_round_054(monkeypatch):
    """When first item is a ModelFBWorkspace, markdown called and ObjectsTabsWindow.consume_msg invoked; evolving_tasks updated with names."""
    setup_module_patch(monkeypatch)
    container = FakeContainer()
    win = web.EvolvingWindow(container)

    class Msg:
        tag = "x evolving code"

        def __init__(self, content):
            self.content = content

    mw1 = FakeModelWorkspace("model_X")
    mw2 = FakeModelWorkspace("model_Y")
    msg = Msg([mw1, mw2])

    win.consume_msg(msg)

    assert container.markdown_calls == ["**Model Codes**"]
    assert len(FakeObjectsTabsWindow.instances) == 1
    inst = FakeObjectsTabsWindow.instances[0]
    assert inst.inner_class is web.WorkspaceWindow

    # mapper should return .target_task.name for model workspace
    assert callable(inst.mapper)
    assert inst.mapper(mw1) == "model_X"
    assert inst.mapper(mw2) == "model_Y"

    assert win.evolving_tasks == ["model_X", "model_Y"]


def test_evolving_feedback_factor_and_model_round_054(monkeypatch):
    """Test both FactorSingleFeedback and ModelSingleFeedback branches under evolving feedback tag; ensure proper markdown and tab_names usage."""
    setup_module_patch(monkeypatch)
    container = FakeContainer()
    win = web.EvolvingWindow(container)

    # preset evolving_tasks to ensure tab_names forwarded
    win.evolving_tasks = ["t1", "t2"]

    class Msg:
        def __init__(self, tag, content):
            self.tag = tag
            self.content = content

    # Factor feedback branch
    ffb = FakeFactorFeedback()
    msg1 = Msg("something evolving feedback", [ffb])
    win.consume_msg(msg1)

    # first markdown call should be for factor feedbacks (unicode magnifying glass)
    assert container.markdown_calls[-1] == "**Factor Feedbacks🔍**"

    # ObjectsTabsWindow used with FactorFeedbackWindow and tab_names equal to evolving_tasks
    inst = FakeObjectsTabsWindow.instances[-1]
    assert inst.inner_class is web.FactorFeedbackWindow
    assert inst.tab_names == win.evolving_tasks
    assert inst.consumed is True

    # Model feedback branch
    mfb = FakeModelFeedback()
    msg2 = Msg("other evolving feedback", [mfb])
    win.consume_msg(msg2)

    # markdown for model feedbacks appended
    assert container.markdown_calls[-1] == "**Model Feedbacks🔍**"

    inst2 = FakeObjectsTabsWindow.instances[-1]
    assert inst2.inner_class is web.ModelFeedbackWindow
    assert inst2.tab_names == win.evolving_tasks
    assert inst2.consumed is True
