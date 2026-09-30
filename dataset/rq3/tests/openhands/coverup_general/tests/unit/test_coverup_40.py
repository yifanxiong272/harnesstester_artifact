# file: openhands/runtime/browser/utils.py:41-104
# asked: {"lines": [43, 44, 45, 48, 49, 51, 53, 54, 55, 57, 61, 62, 66, 67, 68, 69, 71, 72, 73, 75, 79, 80, 82, 85, 86, 87, 89, 90, 92, 93, 94, 96, 99, 100, 101, 102, 104], "branches": [[43, 44], [43, 89], [48, 49], [48, 51], [53, 54], [53, 61], [71, 72], [71, 79], [89, 90], [89, 104], [92, 93], [92, 99]]}
# gained: {"lines": [43, 44, 45, 48, 49, 51, 53, 54, 55, 57, 61, 62, 66, 67, 68, 69, 71, 72, 73, 75, 85, 86, 87, 89, 90, 92, 93, 94, 96, 99, 100, 101, 102, 104], "branches": [[43, 44], [43, 89], [48, 49], [48, 51], [53, 54], [53, 61], [71, 72], [89, 90], [89, 104], [92, 93]]}

import pytest
from types import SimpleNamespace

import openhands.runtime.browser.utils as utils
from openhands.runtime.browser.utils import get_agent_obs_text
from openhands.core.schema import ActionType


def make_obs(**kwargs):
    # Provide sensible defaults for all attributes referenced by get_agent_obs_text
    defaults = dict(
        trigger_by_action=None,
        url="http://example.com",
        focused_element_bid="bid123",
        screenshot_path="",
        error=False,
        last_browser_action_error="",
        axtree_object=None,
        extra_element_properties=None,
        filter_visible_only=False,
        content="",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_browse_interactive_complete_non_error_shows_full_tree(monkeypatch):
    # Arrange: interactive browse, no error, screenshot present, complete tree (filter_visible_only=False)
    obs = make_obs(
        trigger_by_action=ActionType.BROWSE_INTERACTIVE,
        screenshot_path="/tmp/shot.png",
        error=False,
        last_browser_action_error="",
        filter_visible_only=False,
    )

    # Patch get_axtree_str to return a predictable string
    def fake_get_axtree_str(axtree_object, extra_element_properties, filter_visible_only):
        assert filter_visible_only is False
        return "AXTREE_TXT_LINE_1\nAXTREE_TXT_LINE_2"

    monkeypatch.setattr(utils, "get_axtree_str", fake_get_axtree_str)

    # Act
    text = get_agent_obs_text(obs)

    # Assert key parts are present
    assert "[Current URL: http://example.com]" in text
    assert "[Focused element bid: bid123]" in text
    assert "[Screenshot saved to: /tmp/shot.png]" in text
    assert "[Action executed successfully.]" in text
    assert "Accessibility tree of the COMPLETE webpage" in text
    assert "============== BEGIN accessibility tree ==============" in text
    assert "AXTREE_TXT_LINE_1" in text
    assert "AXTREE_TXT_LINE_2" in text


def test_browse_interactive_error_and_axtree_exception(monkeypatch):
    # Arrange: interactive browse, error occurred when executing last action, visible-only filter True
    obs = make_obs(
        trigger_by_action=ActionType.BROWSE_INTERACTIVE,
        screenshot_path="",  # no screenshot
        error=True,
        last_browser_action_error="something went wrong",
        filter_visible_only=True,
    )

    # Patch get_axtree_str to raise an exception to hit the except branch
    def raising_get_axtree_str(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(utils, "get_axtree_str", raising_get_axtree_str)

    # Act
    text = get_agent_obs_text(obs)

    # Assert error message and exception handling are present
    assert "[Current URL: http://example.com]" in text
    assert "[Focused element bid: bid123]" in text
    # No screenshot line should be present
    assert "Screenshot saved to:" not in text
    assert "The following error occurred when executing the last action:" in text
    assert "something went wrong" in text
    # Since get_axtree_str raised, the exception message should be appended
    assert "Error encountered when processing the accessibility tree" in text
    assert "boom" in text


def test_browse_shows_content_and_visit_error():
    # Arrange: non-interactive browse (ActionType.BROWSE), with an error when trying to visit
    obs = make_obs(
        trigger_by_action=ActionType.BROWSE,
        url="http://example.org",
        error=True,
        last_browser_action_error="visit failed",
        content="Hello from the page!",
    )

    # Act
    text = get_agent_obs_text(obs)

    # Assert error message and content are present
    assert "[Current URL: http://example.org]" in text
    assert "The following error occurred when trying to visit the URL:" in text
    assert "visit failed" in text
    assert "============== BEGIN webpage content ==============" in text
    assert "Hello from the page!" in text
    assert "============== END webpage content ==============" in text


def test_invalid_trigger_raises_value_error():
    obs = make_obs(trigger_by_action="NOT_A_VALID_ACTION")
    with pytest.raises(ValueError) as excinfo:
        get_agent_obs_text(obs)
    assert "Invalid trigger_by_action" in str(excinfo.value)
