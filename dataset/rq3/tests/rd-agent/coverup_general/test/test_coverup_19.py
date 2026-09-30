# file: rdagent/log/ui/web.py:366-438
# asked: {"lines": [366, 368, 370, 371, 373, 376, 378, 379, 380, 381, 382, 384, 385, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 400, 401, 402, 405, 406, 407, 409, 411, 412, 413, 414, 416, 418, 420, 421, 422, 424, 426, 427, 428, 430, 434, 435, 436, 438], "branches": [[368, 370], [368, 373], [370, 371], [370, 373], [376, 378], [376, 382], [378, 379], [378, 380], [380, 381], [380, 438], [382, 384], [382, 385], [385, 387], [385, 388], [388, 389], [388, 390], [390, 391], [390, 392], [392, 393], [392, 434], [394, 395], [394, 396], [396, 397], [396, 400], [400, 401], [400, 405], [405, 406], [405, 412], [412, 413], [412, 420], [420, 421], [420, 426], [426, 427], [426, 438], [434, 435], [434, 436]]}
# gained: {"lines": [366, 368, 370, 371, 373, 376, 378, 379, 380, 381, 382, 384, 385, 387, 388, 389, 390, 391, 392, 393, 394, 396, 397, 398, 400, 401, 402, 405, 406, 407, 409, 411, 412, 413, 414, 416, 418, 420, 421, 422, 424, 426, 427, 428, 430, 434, 436, 438], "branches": [[368, 370], [370, 371], [370, 373], [376, 378], [376, 382], [378, 379], [378, 380], [380, 381], [382, 384], [382, 385], [385, 387], [385, 388], [388, 389], [388, 390], [390, 391], [390, 392], [392, 393], [392, 434], [394, 396], [396, 397], [396, 400], [400, 401], [400, 405], [405, 406], [405, 412], [412, 413], [412, 420], [420, 421], [420, 426], [426, 427], [426, 438], [434, 436]]}

import datetime
import types

import pytest

import rdagent.log.ui.web as web
from rdagent.log.base import Message


class FakeContainer:
    def __init__(self, name="root"):
        self.name = name
        self.header_calls = []
        self.expanders = {}
        self.code_calls = []

    def header(self, txt, divider=False):
        self.header_calls.append((txt, divider))

    def expander(self, name):
        # return a distinct fake expander per name
        if name not in self.expanders:
            self.expanders[name] = FakeContainer(name=name)
        return self.expanders[name]

    def code(self, txt, language="log"):
        self.code_calls.append((txt, language))


class FakeWindow:
    def __init__(self, container, *args, **kwargs):
        self.container = container
        self.args = args
        self.kwargs = kwargs
        self.consume_calls = []

    def consume_msg(self, msg):
        self.consume_calls.append(msg)


class FakeLLMWindow(FakeWindow):
    def __init__(self, container, session_name: str = "common"):
        super().__init__(container, session_name=session_name)
        self.session_name = session_name


class FakeObjectsTabsWindow(FakeWindow):
    def __init__(self, container, inner_class=web.StWindow, mapper=lambda x: str(x), tab_names=None, **kwargs):
        # match signature used in code (some calls use named args)
        super().__init__(container, inner_class, mapper, tab_names, **kwargs)
        self.inner_class = inner_class
        self.mapper = mapper
        self.tab_names = tab_names


@pytest.fixture(autouse=True)
def preserve_module_state():
    # save originals and restore after each test
    originals = {}
    names = [
        "LLMWindow",
        "HypothesisWindow",
        "HypothesisFeedbackWindow",
        "QlibFactorExpWindow",
        "QlibModelExpWindow",
        "ObjectsTabsWindow",
        "FactorTaskWindow",
        "ModelTaskWindow",
        "WorkspaceWindow",
        "FactorFeedbackWindow",
        "ModelFeedbackWindow",
        "StWindow",
        # class names used for isinstance checks
        "Hypothesis",
        "HypothesisFeedback",
        "QlibFactorExperiment",
        "QlibModelExperiment",
        "FactorTask",
        "ModelTask",
        "FactorFBWorkspace",
        "ModelFBWorkspace",
        "FactorSingleFeedback",
        "ModelSingleFeedback",
    ]
    for n in names:
        originals[n] = getattr(web, n)
    try:
        yield
    finally:
        for n, v in originals.items():
            setattr(web, n, v)


def make_message(tag, content):
    # use timezone-aware timestamp to avoid issues in formatting
    now = datetime.datetime.now(datetime.timezone.utc)
    return Message(
        tag=tag,
        level="INFO",
        timestamp=now,
        caller=None,
        pid_trace=None,
        content=content,
    )


def test_header_and_stwindow_consume(monkeypatch):
    """
    Test that when tag is longer than current_tag and not ending with 'llm_messages',
    the container.header is called and the default StWindow.consume_msg is invoked.
    """
    fake_container = FakeContainer()
    # Replace StWindow with FakeWindow to capture consume_msg
    monkeypatch.setattr(web, "StWindow", FakeWindow)
    # enable common logs so non-special content is consumed
    sw = web.SimpleTraceWindow(container=fake_container, show_common_logs=True)
    # current_tag is '', so new tag 'task.sub' is longer
    msg = make_message("task.sub", "some common content")
    sw.consume_msg(msg)

    # header should be called with "task ➡ sub"
    assert fake_container.header_calls, "header should be called"
    assert fake_container.header_calls[0][0] == "task ➡ sub"
    # current_win should be an instance of FakeWindow and have consumed the message
    assert isinstance(sw.current_win, FakeWindow)
    assert sw.current_win.consume_calls == [msg]


def test_llm_early_return_when_hidden(monkeypatch):
    """
    When tag endswith 'llm_messages' and show_llm is False, the function returns early,
    no header and no consume should happen.
    """
    fake_container = FakeContainer()
    monkeypatch.setattr(web, "StWindow", FakeWindow)
    sw = web.SimpleTraceWindow(container=fake_container, show_llm=False)
    msg = make_message("session.llm_messages", "llm content")
    sw.consume_msg(msg)

    # header should not be called (llm messages skip header)
    assert fake_container.header_calls == []
    # current_win should remain the initial FakeWindow and should not have been called
    assert isinstance(sw.current_win, FakeWindow)
    assert sw.current_win.consume_calls == []


def test_llm_window_created_and_consumed(monkeypatch):
    """
    When show_llm is True and tag endswith 'llm_messages', LLMWindow should be instantiated
    and its consume_msg should be called.
    """
    fake_container = FakeContainer()
    # monkeypatch LLMWindow to our fake
    monkeypatch.setattr(web, "LLMWindow", FakeLLMWindow)
    sw = web.SimpleTraceWindow(container=fake_container, show_llm=True)
    msg = make_message("session.llm_messages", "llm content 2")
    sw.consume_msg(msg)

    # current_win should be a FakeLLMWindow and should have consumed the message
    assert isinstance(sw.current_win, FakeLLMWindow)
    assert sw.current_win.consume_calls == [msg]


@pytest.mark.parametrize(
    "content_attr_name,window_attr_name",
    [
        ("Hypothesis", "HypothesisWindow"),
        ("HypothesisFeedback", "HypothesisFeedbackWindow"),
        ("QlibFactorExperiment", "QlibFactorExpWindow"),
        ("QlibModelExperiment", "QlibModelExpWindow"),
    ],
)
def test_single_object_windows(monkeypatch, content_attr_name, window_attr_name):
    """
    For single object contents, the corresponding window should be created and consume_msg called.
    This test parametrizes multiple content/window pairs.
    """
    fake_container = FakeContainer()
    # Create dummy content class and instance
    DummyContent = type(f"Dummy{content_attr_name}", (), {})  # simple class
    dummy_instance = DummyContent()
    # Monkeypatch the content class in module so isinstance checks work
    monkeypatch.setattr(web, content_attr_name, DummyContent)
    # Monkeypatch corresponding window class to FakeWindow
    monkeypatch.setattr(web, window_attr_name, FakeWindow)
    sw = web.SimpleTraceWindow(container=fake_container)
    tag = f"some.{content_attr_name.lower()}"
    msg = make_message(tag, dummy_instance)
    sw.consume_msg(msg)

    # Ensure current window is the FakeWindow we installed and it consumed the message
    assert isinstance(sw.current_win, FakeWindow)
    assert sw.current_win.consume_calls == [msg]


def test_list_object_tabs_and_evolving_tasks(monkeypatch):
    """
    Test list-based flows:
    - FactorTask list -> ObjectsTabsWindow with FactorTaskWindow
    - ModelTask list -> ObjectsTabsWindow with ModelTaskWindow
    - FactorFBWorkspace list -> ObjectsTabsWindow + evolving_tasks set
    - ModelFBWorkspace list -> ObjectsTabsWindow + evolving_tasks set
    - FactorSingleFeedback and ModelSingleFeedback -> ObjectsTabsWindow with tab_names from evolving_tasks
    - list of unknown -> common logs branch when show_common_logs True
    """
    fake_container = FakeContainer()
    # Patch ObjectsTabsWindow to our fake to capture parameters and consumption
    monkeypatch.setattr(web, "ObjectsTabsWindow", FakeObjectsTabsWindow)
    monkeypatch.setattr(web, "FactorTaskWindow", FakeWindow)
    monkeypatch.setattr(web, "ModelTaskWindow", FakeWindow)
    monkeypatch.setattr(web, "WorkspaceWindow", FakeWindow)
    monkeypatch.setattr(web, "FactorFeedbackWindow", FakeWindow)
    monkeypatch.setattr(web, "ModelFeedbackWindow", FakeWindow)

    # 1) FactorTask list
    DummyFactorTask = type("DummyFactorTask", (), {"factor_name": "fac1"})
    monkeypatch.setattr(web, "FactorTask", DummyFactorTask)
    ft_instance = DummyFactorTask()
    sw1 = web.SimpleTraceWindow(container=fake_container)
    msg1 = make_message("tag.tasks", [ft_instance])
    sw1.consume_msg(msg1)
    # Should create ObjectsTabsWindow
    assert isinstance(sw1.current_win, FakeObjectsTabsWindow)
    # inner_class should be FactorTaskWindow (we passed FakeWindow), confirm via stored inner_class
    assert sw1.current_win.inner_class is web.FactorTaskWindow

    # 2) ModelTask list
    DummyModelTask = type("DummyModelTask", (), {"name": "model1"})
    monkeypatch.setattr(web, "ModelTask", DummyModelTask)
    mt_instance = DummyModelTask()
    sw2 = web.SimpleTraceWindow(container=fake_container)
    msg2 = make_message("tag.tasks", [mt_instance])
    sw2.consume_msg(msg2)
    assert isinstance(sw2.current_win, FakeObjectsTabsWindow)
    assert sw2.current_win.inner_class is web.ModelTaskWindow

    # 3) FactorFBWorkspace list -> sets evolving_tasks to factor_name list
    # Create target_task with factor_name attribute
    TargetFactorTask = type("TargetFactorTask", (), {"factor_name": "fA"})
    FBW = type("DummyFactorFBWorkspace", (), {"target_task": TargetFactorTask()})
    monkeypatch.setattr(web, "FactorFBWorkspace", FBW)
    fbw1 = FBW()
    sw3 = web.SimpleTraceWindow(container=fake_container)
    msg3 = make_message("tag.fbw", [fbw1])
    sw3.consume_msg(msg3)
    assert isinstance(sw3.current_win, FakeObjectsTabsWindow)
    # evolving_tasks must equal list of target_task.factor_name
    assert sw3.evolving_tasks == [fbw1.target_task.factor_name]

    # 4) ModelFBWorkspace list -> sets evolving_tasks to name list
    TargetModelTask = type("TargetModelTask", (), {"name": "mA"})
    MBW = type("DummyModelFBWorkspace", (), {"target_task": TargetModelTask()})
    monkeypatch.setattr(web, "ModelFBWorkspace", MBW)
    mbw1 = MBW()
    sw4 = web.SimpleTraceWindow(container=fake_container)
    msg4 = make_message("tag.mbw", [mbw1])
    sw4.consume_msg(msg4)
    assert isinstance(sw4.current_win, FakeObjectsTabsWindow)
    assert sw4.evolving_tasks == [mbw1.target_task.name]

    # 5) FactorSingleFeedback uses existing evolving_tasks as tab_names
    FSF = type("DummyFactorSingleFeedback", (), {})
    monkeypatch.setattr(web, "FactorSingleFeedback", FSF)
    fsf1 = FSF()
    sw5 = web.SimpleTraceWindow(container=fake_container)
    # pre-populate evolving_tasks
    sw5.evolving_tasks = ["t1", "t2"]
    msg5 = make_message("tag.feedbacks", [fsf1])
    sw5.consume_msg(msg5)
    assert isinstance(sw5.current_win, FakeObjectsTabsWindow)
    assert sw5.current_win.tab_names == ["t1", "t2"]

    # 6) ModelSingleFeedback uses existing evolving_tasks as tab_names
    MSF = type("DummyModelSingleFeedback", (), {})
    monkeypatch.setattr(web, "ModelSingleFeedback", MSF)
    msf1 = MSF()
    sw6 = web.SimpleTraceWindow(container=fake_container)
    sw6.evolving_tasks = ["a", "b", "c"]
    msg6 = make_message("tag.mfeedbacks", [msf1])
    sw6.consume_msg(msg6)
    assert isinstance(sw6.current_win, FakeObjectsTabsWindow)
    assert sw6.current_win.tab_names == ["a", "b", "c"]

    # 7) Unknown list -> common logs branch when show_common_logs True
    sw7 = web.SimpleTraceWindow(container=fake_container, show_common_logs=True)
    msg7 = make_message("tag.unknown", ["x", "y"])
    sw7.consume_msg(msg7)
    # Now container.code should have been called by the original StWindow.consume_msg
    assert fake_container.code_calls, "StWindow.consume_msg should call container.code for common logs"
    # current_win should be an instance of the original StWindow class
    assert isinstance(sw7.current_win, web.StWindow)
