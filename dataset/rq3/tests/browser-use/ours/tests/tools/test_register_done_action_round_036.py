import asyncio
import json
import logging
from types import SimpleNamespace
from pathlib import Path

import pytest

from browser_use.tools import service as service_mod
from browser_use.tools.service import Tools


class FakeRegistry:
    def __init__(self):
        self.last = None

    def action(self, description, param_model=None):
        # returns a decorator that stores the decorated function for later inspection
        def decorator(func):
            self.last = func
            return func

        return decorator


class FakeFileSystem:
    def __init__(self, available: dict[str, str], base: str = "/base"):
        # available: mapping filename -> content
        self.available = available
        self._base = Path(base)

    def display_file(self, file_name: str) -> str:
        # returns content or empty string to simulate not found
        return self.available.get(file_name, "")

    def get_dir(self) -> Path:
        return self._base


class FakeParamsStructured:
    def __init__(self, data_dict: dict, success: bool, files_to_display: list[str] | None = None):
        class DataHolder:
            def __init__(self, d):
                self._d = d

            def model_dump(self, mode: str = "json"):
                # mimic pydantic model_dump(mode='json') returning a Python structure
                assert mode == "json"
                return self._d

        self.data = DataHolder(data_dict)
        self.success = success
        self.files_to_display = files_to_display or []


class FakeParamsDone:
    def __init__(self, text: str, success: bool, files_to_display: list[str] | None = None):
        self.text = text
        self.success = success
        self.files_to_display = files_to_display or []


@pytest.fixture(autouse=True)
def patch_action_result(monkeypatch):
    # Patch the ActionResult used inside the module under test to a simple container
    def make_action_result(**kwargs):
        return SimpleNamespace(**kwargs)

    monkeypatch.setattr(service_mod, "ActionResult", make_action_result)
    yield


def test_structured_output_done_round_036():
    """Structured output path: ensure JSON extraction, file attachments from file_system and browser_session downloads (deduped)."""
    registry = FakeRegistry()
    tools = object.__new__(Tools)
    tools.registry = registry
    # ensure attribute exists; for structured path _register_done_action will overwrite it
    tools.display_files_in_done_text = True

    # Register the done action for structured output
    tools._register_done_action(output_model=object, display_files_in_done_text=True)
    assert registry.last is not None, "registry should have captured the structured done function"

    # Prepare params: one found file and one missing
    params = FakeParamsStructured(data_dict={"k": "v"}, success=True, files_to_display=["found.txt", "missing.txt"])
    fs = FakeFileSystem({"found.txt": "CONTENT"}, base="/base")
    # session downloads include one duplicate and one new path
    browser_session = SimpleNamespace(downloaded_files=["/downloads/x.txt", str(Path("/base") / "found.txt")])

    result = asyncio.run(registry.last(params, fs, browser_session))

    assert result.is_done is True
    assert result.success is True
    # extracted_content should be a JSON string of the dumped dict
    assert result.extracted_content == json.dumps({"k": "v"}, ensure_ascii=False)
    # attachments: first the file system resolved path, then the new download (duplicate skipped)
    assert result.attachments == [str(Path("/base") / "found.txt"), "/downloads/x.txt"]
    assert "Task completed. Success Status: True" in result.long_term_memory


def test_done_action_with_attachments_long_text_round_036():
    """DoneAction path: when files are found and text is long, user_message should include attachments and memory notes length."""
    registry = FakeRegistry()
    tools = object.__new__(Tools)
    tools.registry = registry
    # ensure display_files_in_done_text True to trigger file_msg branch
    tools.display_files_in_done_text = True

    tools._register_done_action(output_model=None, display_files_in_done_text=True)
    assert registry.last is not None, "registry should have captured the non-structured done function"

    long_text = "x" * 150  # longer than 100 to hit the "more characters" branch
    params = FakeParamsDone(text=long_text, success=False, files_to_display=["f1.txt"])
    fs = FakeFileSystem({"f1.txt": "LINE1\nLINE2"}, base="/base")

    result = asyncio.run(registry.last(params, fs))

    assert result.is_done is True
    assert result.success is False
    # the long_term_memory must indicate how many extra characters beyond 100
    assert "more characters" in result.long_term_memory
    assert "50" in result.long_term_memory  # 150 - 100 => 50 more characters
    # extracted_content should contain the original text plus Attachments block
    assert "Attachments:" in result.extracted_content
    assert "f1.txt" in result.extracted_content
    # attachments should be converted to full path strings
    assert result.attachments == [str(Path("/base") / "f1.txt")]


def test_done_action_warn_no_files_round_036(caplog):
    """DoneAction path: when display_files_in_done_text is True but no files found, a warning should be logged and attachments empty."""
    caplog.set_level(logging.WARNING)

    registry = FakeRegistry()
    tools = object.__new__(Tools)
    tools.registry = registry
    tools.display_files_in_done_text = True

    tools._register_done_action(output_model=None, display_files_in_done_text=True)
    assert registry.last is not None

    params = FakeParamsDone(text="short text", success=True, files_to_display=["missing.txt"])
    # file system returns no content for the requested file
    fs = FakeFileSystem({}, base="/base")

    result = asyncio.run(registry.last(params, fs))

    # No attachments should be present
    assert result.attachments == []
    # original text should be preserved in extracted_content
    assert "short text" in result.extracted_content
    # confirm warning was emitted
    messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any("Agent wanted to display files but none were found" in str(m) for m in messages)
