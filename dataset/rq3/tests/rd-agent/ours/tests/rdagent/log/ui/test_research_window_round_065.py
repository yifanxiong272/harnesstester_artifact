import types
from types import SimpleNamespace
import argparse
from unittest.mock import patch

# Patch argparse.parse_args at import time to avoid consuming pytest CLI args
with patch.object(argparse.ArgumentParser, "parse_args", return_value=SimpleNamespace(log_dir=None, debug=False)):
    import rdagent.log.ui.app as app


class _Recorder:
    def __init__(self):
        self.calls = []

    def record(self, name, args, kwargs=None):
        if kwargs is None:
            kwargs = {}
        self.calls.append((name, args, kwargs))


class Msg:
    def __init__(self, content):
        self.content = content


def _make_stubs(recorder):
    class Ctx:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def container(**kwargs):
        recorder.record("container_enter", (kwargs,), {})
        return Ctx()

    def subheader(*args, **kwargs):
        recorder.record("subheader", args, kwargs)

    def image(*args, **kwargs):
        recorder.record("image", args, kwargs)

    def markdown(*args, **kwargs):
        recorder.record("markdown", args, kwargs)

    def columns(*args, **kwargs):
        recorder.record("columns", args, kwargs)
        # return two context managers to be used with `with`
        return (Ctx(), Ctx())

    return SimpleNamespace(
        container=container,
        subheader=subheader,
        image=image,
        markdown=markdown,
        columns=columns,
    )


def test_research_window_similar_scenario_round_065(monkeypatch):
    """
    Exercising the branch when state.scenario is in SIMILAR_SCENARIOS.
    - Provides load_pdf_screenshot with 3 items -> image called min(2,len(pim)) == 2 times
    - Provides hypothesis generation -> markdown called for title and body that include hypothesis text
    - Provides experiment generation -> tasks_window called with the provided content
    """
    recorder = _Recorder()
    st_stub = _make_stubs(recorder)

    # Dummy types to satisfy isinstance checks
    class DummySimilar:
        pass

    class DummyHypothesis:
        def __init__(self, hypothesis, reason):
            self.hypothesis = hypothesis
            self.reason = reason

    # Patch module symbols
    monkeypatch.setattr(app, "st", st_stub)
    # SIMILAR_SCENARIOS used as the second arg to isinstance; provide a tuple of types
    monkeypatch.setattr(app, "SIMILAR_SCENARIOS", (DummySimilar,))

    # Provide a round value used as key into state.msgs
    monkeypatch.setattr(app, "round", 0)

    # tasks_window should be patched to record calls
    def fake_tasks_window(tasks):
        recorder.record("tasks_window", (tasks,), {})

    monkeypatch.setattr(app, "tasks_window", fake_tasks_window)

    # Build messages for the 'round' key
    h = DummyHypothesis(hypothesis="It works", reason="Because tests say so")
    msgs_for_round = {
        "load_pdf_screenshot": [Msg("img-A"), Msg("img-B"), Msg("img-C")],
        "hypothesis generation": [Msg(h)],
        "experiment generation": [Msg("experiment-tasks")],
    }

    # Patch state with scenario instance and msgs mapping
    monkeypatch.setattr(app, "state", SimpleNamespace(scenario=DummySimilar(), msgs={0: msgs_for_round}))

    # Call the function under test
    app.research_window()

    # Assertions about recorder contents
    assert any(c[0] == "container_enter" for c in recorder.calls), "container not entered"
    assert any(c[0] == "subheader" for c in recorder.calls), "subheader not called"

    # image called exactly twice (min(2, len(pim)))
    image_calls = [c for c in recorder.calls if c[0] == "image"]
    assert len(image_calls) == 2, f"expected 2 image calls, got {len(image_calls)}"

    # markdown called for Hypothesis title and body; ensure body contains hypothesis text
    markdown_calls = [c for c in recorder.calls if c[0] == "markdown"]
    assert any("Hypothesis" in str(args[0]) or "Hypothesis" in str(args) for (_, args, _) in markdown_calls), "Hypothesis title markdown not found"

    # find a markdown body that contains both hypothesis and reason
    bodies = [args[0] for (_, args, _) in markdown_calls if args and isinstance(args[0], str)]
    assert any("It works" in b and "Because tests say so" in b for b in bodies), "Hypothesis body not rendered"

    # tasks_window must be invoked with the experiment content
    assert any(c[0] == "tasks_window" and c[1][0] == "experiment-tasks" for c in recorder.calls), "tasks_window not called with experiment-tasks"


def test_research_window_general_model_scenario_round_065(monkeypatch):
    """
    Exercising the GeneralModelScenario branch.
    - Column context managers are used
    - pdf_image list triggers image call for each item
    - load_experiment triggers tasks_window with me.sub_tasks
    """
    recorder = _Recorder()
    st_stub = _make_stubs(recorder)

    # Dummy GeneralModelScenario type and experiment
    class DummyGeneral:
        pass

    class DummyExperiment:
        def __init__(self, sub_tasks):
            self.sub_tasks = sub_tasks

    # Patch streamlit, GeneralModelScenario and tasks_window
    monkeypatch.setattr(app, "st", st_stub)
    monkeypatch.setattr(app, "GeneralModelScenario", DummyGeneral)

    def fake_tasks_window(tasks):
        recorder.record("tasks_window", (tasks,), {})

    monkeypatch.setattr(app, "tasks_window", fake_tasks_window)

    # Provide messages keyed at 0 as the function expects
    mem_experiment = DummyExperiment(sub_tasks=["sub1", "sub2"])
    msgs0 = {
        "pdf_image": [Msg("pdf-1"), Msg("pdf-2")],
        "load_experiment": [Msg(mem_experiment)],
    }

    monkeypatch.setattr(app, "state", SimpleNamespace(scenario=DummyGeneral(), msgs={0: msgs0}))

    # call under test
    app.research_window()

    # Confirm columns context was entered
    assert any(c[0] == "columns" for c in recorder.calls), "columns not used"

    # Each pdf_image entry should trigger an image call (2 entries -> 2 image calls)
    image_calls = [c for c in recorder.calls if c[0] == "image"]
    assert len(image_calls) == 2, f"expected 2 image calls for pdf_image, got {len(image_calls)}"

    # tasks_window should be called with the experiment's sub_tasks
    assert any(c[0] == "tasks_window" and c[1][0] == ["sub1", "sub2"] for c in recorder.calls), "tasks_window not called with experiment sub_tasks"
