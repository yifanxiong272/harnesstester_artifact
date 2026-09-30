# file: rdagent/log/ui/app.py:550-585
# asked: {"lines": [550, 551, 552, 553, 554, 556, 557, 558, 561, 562, 563, 564, 565, 566, 567, 570, 571, 573, 575, 576, 577, 578, 579, 582, 583, 584, 585], "branches": [[554, 556], [554, 573], [556, 557], [556, 561], [557, 558], [557, 561], [561, 562], [561, 570], [570, 0], [570, 571], [573, 0], [573, 575], [577, 578], [577, 582], [578, 579], [578, 582], [583, 0], [583, 584]]}
# gained: {"lines": [550, 551, 552, 553, 554, 556, 557, 558, 561, 562, 563, 564, 565, 566, 567, 570, 571, 573, 575, 576, 577, 578, 579, 582, 583, 584, 585], "branches": [[554, 556], [554, 573], [556, 557], [557, 558], [557, 561], [561, 562], [570, 571], [573, 575], [577, 578], [578, 579], [578, 582], [583, 584]]}

import importlib
import types
import sys
import argparse
import pytest


class FakeColumn:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeStreamlit:
    def __init__(self):
        self.image_calls = []
        self.markdown_calls = []
        self.subheader_calls = []
        self.columns_args = []
        self.container_called = False

    def container(self, border=None):
        self.container_called = True

        class Ctx:
            def __enter__(inner_self):
                return inner_self

            def __exit__(inner_self, exc_type, exc, tb):
                return False

        return Ctx()

    def subheader(self, title, divider=None, anchor=None):
        self.subheader_calls.append({"title": title, "divider": divider, "anchor": anchor})

    def image(self, content, use_container_width=True):
        self.image_calls.append({"content": content, "use_container_width": use_container_width})

    def markdown(self, txt):
        self.markdown_calls.append(txt)

    def columns(self, args):
        self.columns_args.append(args)
        return FakeColumn(), FakeColumn()


class Msg:
    def __init__(self, content):
        self.content = content


def make_hypothesis(hypothesis, reason):
    class H:
        def __init__(self, hypothesis, reason):
            self.hypothesis = hypothesis
            self.reason = reason

    return H(hypothesis, reason)


def make_qlib_experiment(sub_tasks):
    class E:
        def __init__(self, sub_tasks):
            self.sub_tasks = sub_tasks

    return E(sub_tasks)


def import_app_with_safe_argparse(monkeypatch):
    # Ensure argparse.ArgumentParser.parse_args won't call sys.exit during import
    monkeypatch.setattr(
        argparse.ArgumentParser,
        "parse_args",
        lambda self: types.SimpleNamespace(log_dir=None, debug=False),
        raising=False,
    )
    # Remove module if previously imported to ensure clean import
    mod_name = "rdagent.log.ui.app"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    return importlib.import_module(mod_name)


def cleanup_app_module():
    mod_name = "rdagent.log.ui.app"
    if mod_name in sys.modules:
        del sys.modules[mod_name]


def test_research_window_similar_scenarios(monkeypatch):
    app = import_app_with_safe_argparse(monkeypatch)
    try:
        fake_st = FakeStreamlit()
        # Patch the st object in the module
        monkeypatch.setattr(app, "st", fake_st)

        # Ensure round name exists in module and set to 1
        monkeypatch.setattr(app, "round", 1, raising=False)

        # Create a dummy scenario type and set SIMILAR_SCENARIOS to it
        class SimilarScenario:
            pass

        monkeypatch.setattr(app, "SIMILAR_SCENARIOS", SimilarScenario, raising=False)
        # Set state to a simple object with attributes scenario and msgs
        state = types.SimpleNamespace()
        state.scenario = SimilarScenario()  # instance matches isinstance check

        # Prepare messages: load_pdf_screenshot should have >=2 items to trigger min(2, len)
        pdf_items = [Msg(content="img_content_1"), Msg(content="img_content_2"), Msg(content="img_content_3")]
        hypothesis_obj = make_hypothesis("TestHyp", "Because testing")
        experiment_tasks = ["taskA", "taskB"]
        msgs = {
            1: {
                "load_pdf_screenshot": pdf_items,
                "hypothesis generation": [Msg(content=hypothesis_obj)],
                "experiment generation": [Msg(content=experiment_tasks)],
            }
        }
        state.msgs = msgs

        # Patch the session state in module
        monkeypatch.setattr(app, "state", state, raising=False)

        # Spy for tasks_window
        called = {}

        def fake_tasks_window(arg):
            called["arg"] = arg

        monkeypatch.setattr(app, "tasks_window", fake_tasks_window, raising=False)

        # Call the function under test
        app.research_window()

        # Assertions: container entered, subheader called with the SIMILAR_SCENARIOS title
        assert fake_st.container_called is True
        assert any("Research🔍" in c["title"] for c in fake_st.subheader_calls)
        # Images: min(2,len(pdf_items)) => 2 images
        assert len(fake_st.image_calls) == 2
        assert fake_st.image_calls[0]["content"] == "img_content_1"
        assert fake_st.image_calls[1]["content"] == "img_content_2"
        # Hypothesis markdown calls: one for header and one for content
        assert any("Hypothesis💡" in m for m in fake_st.markdown_calls)
        assert any("TestHyp" in m and "Because testing" in m for m in fake_st.markdown_calls)
        # tasks_window called with experiment_tasks
        assert called.get("arg") == experiment_tasks
    finally:
        cleanup_app_module()


def test_research_window_general_model_scenario(monkeypatch):
    app = import_app_with_safe_argparse(monkeypatch)
    try:
        fake_st = FakeStreamlit()
        monkeypatch.setattr(app, "st", fake_st)

        # Create a dummy GeneralModelScenario class and set in module
        class DummyGeneralModelScenario:
            pass

        monkeypatch.setattr(app, "GeneralModelScenario", DummyGeneralModelScenario, raising=False)

        # Set state with scenario instance of GeneralModelScenario and msgs[0] entries
        state = types.SimpleNamespace()
        state.scenario = DummyGeneralModelScenario()
        pdf_items = [Msg(content="pdf_img_1"), Msg(content="pdf_img_2")]
        qlib_exp = make_qlib_experiment(sub_tasks=["sub1", "sub2", "sub3"])
        msgs = {
            0: {
                "pdf_image": pdf_items,
                "load_experiment": [Msg(content=qlib_exp)],
            }
        }
        state.msgs = msgs
        monkeypatch.setattr(app, "state", state, raising=False)

        called = {}

        def fake_tasks_window(arg):
            called["arg"] = arg

        monkeypatch.setattr(app, "tasks_window", fake_tasks_window, raising=False)

        # Call function
        app.research_window()

        # Assertions: subheader called with reader title (not SIMILAR_SCENARIOS)
        assert any("Research🔍" in c["title"] for c in fake_st.subheader_calls)
        # All pdf images should be rendered (len(pdf_items))
        assert len(fake_st.image_calls) == len(pdf_items)
        assert [c["content"] for c in fake_st.image_calls] == ["pdf_img_1", "pdf_img_2"]
        # tasks_window called with qlib_exp.sub_tasks
        assert called.get("arg") == ["sub1", "sub2", "sub3"]
    finally:
        cleanup_app_module()
