# file: rdagent/log/ui/web.py:485-524
# asked: {"lines": [485, 486, 487, 488, 490, 491, 492, 493, 494, 495, 496, 497, 498, 499, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518, 519, 520, 521, 522, 523, 524], "branches": [[491, 492], [491, 510], [492, 0], [492, 493], [494, 495], [494, 496], [496, 497], [496, 504], [504, 0], [504, 505], [510, 0], [510, 511], [511, 0], [511, 512], [513, 514], [513, 515], [515, 516], [515, 520], [520, 0], [520, 521]]}
# gained: {"lines": [485, 486, 487, 488, 490, 491, 492, 493, 494, 495, 496, 497, 498, 499, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 515, 516, 517, 518, 519, 520, 521, 522, 523, 524], "branches": [[491, 492], [491, 510], [492, 493], [494, 495], [494, 496], [496, 497], [496, 504], [504, 505], [510, 511], [511, 512], [513, 515], [515, 516], [515, 520], [520, 521]]}

import importlib
import types
import pytest

def make_dummy_ws(name_attr):
    class DummyTarget:
        def __init__(self, name):
            setattr(self, name_attr, name)

    class DummyWorkspace:
        def __init__(self, name):
            self.target_task = DummyTarget(name)

    return DummyWorkspace

class DummyMsg:
    def __init__(self, tag, content):
        self.tag = tag
        self.content = content

def test_evolving_window_factor_flow_and_empty_filter(monkeypatch):
    web = importlib.import_module("rdagent.log.ui.web")

    # Replace ObjectsTabsWindow with a dummy that records construction args and consume_msg calls
    recorded = {}

    class DummyObjectsTabsWindow:
        def __init__(self, container_arg, inner_class=None, mapper=None, tab_names=None):
            recorded['container_arg'] = container_arg
            recorded['inner_class'] = inner_class
            recorded['mapper'] = mapper
            recorded['tab_names'] = tab_names
            recorded['constructed'] = recorded.get('constructed', 0) + 1

        def consume_msg(self, msg):
            recorded['consumed_msg'] = msg

    monkeypatch.setattr(web, "ObjectsTabsWindow", DummyObjectsTabsWindow)

    # Dummy windows/classes for parameters (not used by DummyObjectsTabsWindow but present)
    monkeypatch.setattr(web, "WorkspaceWindow", object)
    monkeypatch.setattr(web, "FactorFeedbackWindow", object)
    monkeypatch.setattr(web, "ModelFeedbackWindow", object)

    # Monkeypatch the workspace and feedback types used in isinstance checks
    FactorFBWorkspace = make_dummy_ws("factor_name")
    FactorSingleFeedback = type("FactorSingleFeedback", (), {})  # simple class
    monkeypatch.setattr(web, "FactorFBWorkspace", FactorFBWorkspace)
    monkeypatch.setattr(web, "FactorSingleFeedback", FactorSingleFeedback)

    # Create a fake container that records markdown calls and provides container()
    class FakeContainer:
        def __init__(self):
            self.markdowns = []
            self.cont_called = 0

        def markdown(self, text):
            self.markdowns.append(text)

        def container(self):
            self.cont_called += 1
            return "inner_container"

    fake_container = FakeContainer()

    # Import EvolvingWindow
    EvolvingWindow = getattr(web, "EvolvingWindow")

    ew = EvolvingWindow(fake_container)

    # 1) Test empty-filter behavior: content list of falsy values -> should return early and not call ObjectsTabsWindow
    msg_empty = DummyMsg("something evolving code", [None, False, ""])
    ew.consume_msg(msg_empty)
    # No markdown should have been added
    assert fake_container.markdowns == []

    # 2) Test factor workspace flow
    ws1 = FactorFBWorkspace("f_one")
    ws2 = FactorFBWorkspace("f_two")
    msg_factor = DummyMsg("prefix evolving code", [ws1, ws2])
    ew.consume_msg(msg_factor)

    # Should have added the Factor Codes markdown
    assert "**Factor Codes**" in fake_container.markdowns
    # ObjectsTabsWindow should have been constructed and consume_msg called with the message
    assert recorded.get('constructed', 0) >= 1
    assert recorded.get('consumed_msg') is msg_factor
    # evolving_tasks should be populated from target_task.factor_name
    assert ew.evolving_tasks == ["f_one", "f_two"]

    # 3) Now test factor feedback flow: provide FactorSingleFeedback instances
    fb1 = FactorSingleFeedback()
    fb2 = FactorSingleFeedback()
    msg_feedback = DummyMsg("something evolving feedback", [fb1, fb2])
    ew.consume_msg(msg_feedback)

    # Should have added Factor Feedbacks markdown
    assert any("Factor Feedbacks" in m for m in fake_container.markdowns)
    # When constructing ObjectsTabsWindow for feedback, tab_names should be the evolving_tasks recorded earlier
    assert recorded.get('tab_names') == ["f_one", "f_two"]
    # consume_msg should have been called with this feedback message
    assert recorded.get('consumed_msg') is msg_feedback

def test_evolving_window_model_flow_and_feedback(monkeypatch):
    web = importlib.import_module("rdagent.log.ui.web")

    # Prepare records for ObjectsTabsWindow usage
    rec = {}

    class DummyObjectsTabsWindow2:
        def __init__(self, container_arg, inner_class=None, mapper=None, tab_names=None):
            rec['container_arg'] = container_arg
            rec['inner_class'] = inner_class
            rec['mapper'] = mapper
            rec['tab_names'] = tab_names
            rec['constructed'] = rec.get('constructed', 0) + 1

        def consume_msg(self, msg):
            rec['consumed_msg'] = msg

    monkeypatch.setattr(web, "ObjectsTabsWindow", DummyObjectsTabsWindow2)
    monkeypatch.setattr(web, "WorkspaceWindow", object)
    monkeypatch.setattr(web, "FactorFeedbackWindow", object)
    monkeypatch.setattr(web, "ModelFeedbackWindow", object)

    # Monkeypatch model workspace and feedback classes
    ModelFBWorkspace = make_dummy_ws("name")
    ModelSingleFeedback = type("ModelSingleFeedback", (), {})
    monkeypatch.setattr(web, "ModelFBWorkspace", ModelFBWorkspace)
    monkeypatch.setattr(web, "ModelSingleFeedback", ModelSingleFeedback)

    # Fake container
    class FakeContainer2:
        def __init__(self):
            self.markdowns = []
        def markdown(self, text):
            self.markdowns.append(text)
        def container(self):
            return "inner"

    fake_container = FakeContainer2()
    EvolvingWindow = getattr(web, "EvolvingWindow")
    ew = EvolvingWindow(fake_container)

    # Model workspace message
    m1 = ModelFBWorkspace("mA")
    m2 = ModelFBWorkspace("mB")
    msg_code = DummyMsg("x evolving code", [m1, m2])
    ew.consume_msg(msg_code)

    # Check markdown and evolving_tasks set to target_task.name
    assert "**Model Codes**" in fake_container.markdowns
    assert ew.evolving_tasks == ["mA", "mB"]
    assert rec.get('consumed_msg') is msg_code

    # Model feedback message
    mf1 = ModelSingleFeedback()
    mf2 = ModelSingleFeedback()
    msg_feedback = DummyMsg("x evolving feedback", [mf1, mf2])
    ew.consume_msg(msg_feedback)

    # Should have Model Feedbacks markdown and ObjectsTabsWindow constructed with tab_names matching evolving_tasks
    assert any("Model Feedbacks" in m for m in fake_container.markdowns)
    assert rec.get('tab_names') == ["mA", "mB"]
    assert rec.get('consumed_msg') is msg_feedback
