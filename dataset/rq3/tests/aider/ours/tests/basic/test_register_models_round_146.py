import types
import pytest
import aider.main as main


class FakeIO:
    def __init__(self):
        self.outputs = []
        self.errors = []

    def tool_output(self, msg):
        # preserve call shape
        self.outputs.append(msg)

    def tool_error(self, msg):
        # preserve call shape
        self.errors.append(msg)


def test_register_models_files_loaded_verbose_round_146(monkeypatch):
    """When models.register_models returns files and verbose=True,
    expect loaded messages for each file and the searched list afterwards.
    """
    git_root = "/repo"
    model_settings_fname = "config.yml"
    io = FakeIO()

    # Patch generate_search_path_list to return predictable search paths
    monkeypatch.setattr(
        main,
        "generate_search_path_list",
        lambda default, gr, fname: ["pathA", "pathB"],
    )

    # Patch models.register_models to return a non-empty list
    monkeypatch.setattr(
        main.models,
        "register_models",
        lambda files: ["loaded1.yml", "loaded2.yml"],
    )

    result = main.register_models(git_root, model_settings_fname, io, verbose=True)

    assert result is None

    # Verify the exact sequence of tool_output calls
    assert io.outputs == [
        "Loaded model settings from:",
        "  - loaded1.yml",
        "  - loaded2.yml",
        "Searched for model settings files:",
        "  - pathA",
        "  - pathB",
    ]
    # No errors should have been reported
    assert io.errors == []


def test_register_models_no_files_loaded_verbose_round_146(monkeypatch):
    """When models.register_models returns an empty list and verbose=True,
    expect a 'No model settings files loaded' message and then the searched list.
    """
    git_root = "/repo"
    model_settings_fname = "config.yml"
    io = FakeIO()

    monkeypatch.setattr(
        main,
        "generate_search_path_list",
        lambda default, gr, fname: ["s1", "s2"],
    )

    monkeypatch.setattr(
        main.models,
        "register_models",
        lambda files: [],
    )

    result = main.register_models(git_root, model_settings_fname, io, verbose=True)

    assert result is None

    assert io.outputs == [
        "No model settings files loaded",
        "Searched for model settings files:",
        "  - s1",
        "  - s2",
    ]
    assert io.errors == []


def test_register_models_register_raises_round_146(monkeypatch):
    """If models.register_models raises, the exception should be caught,
    io.tool_error should be called with the error string, and the function should
    return 1. The post-try verbose block must not run.
    """
    git_root = "/repo"
    model_settings_fname = "config.yml"
    io = FakeIO()

    monkeypatch.setattr(
        main,
        "generate_search_path_list",
        lambda default, gr, fname: ["should_not_be_printed"],
    )

    def raiser(files):
        raise Exception("boom")

    monkeypatch.setattr(main.models, "register_models", raiser)

    result = main.register_models(git_root, model_settings_fname, io, verbose=True)

    assert result == 1

    # Expect the error message to include the exception text
    assert io.errors == ["Error loading aider model settings: boom"]

    # Because an exception was raised, no successful tool_output messages should be present
    assert io.outputs == []
