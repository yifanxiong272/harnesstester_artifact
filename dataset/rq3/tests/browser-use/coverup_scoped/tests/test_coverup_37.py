# file: browser_use/cli.py:705-765
# asked: {"lines": [705, 708, 709, 712, 713, 714, 715, 716, 717, 718, 721, 722, 723, 724, 725, 726, 728, 729, 730, 734, 735, 736, 737, 738, 739, 740, 744, 745, 746, 747, 748, 749, 750, 751, 755, 756, 757, 758, 759, 760, 761, 765], "branches": [[723, 724], [723, 728], [724, 725], [724, 726], [747, 748], [747, 749]]}
# gained: {"lines": [705, 708, 709, 712, 713, 714, 715, 716, 717, 718, 721, 722, 723, 724, 725, 729, 730, 734, 735, 736, 739, 740, 744, 745, 746, 750, 751, 755, 756, 757, 758, 759, 760, 761, 765], "branches": [[723, 724], [724, 725]]}

import types
import pytest
from types import SimpleNamespace

import browser_use.cli as cli
from browser_use.telemetry import CLITelemetryEvent
from browser_use.utils import get_browser_use_version


def test_on_mount_noncritical_exceptions(monkeypatch):
    # Prepare app with some command history and llm info
    app = cli.BrowserUseApp(config={"command_history": ["one", "two"]})
    app.llm = SimpleNamespace(model="gpt-test-model", provider="test-provider")
    app.browser_session = None  # ensure event bus listener is not invoked

    # setup_richlog_logging: succeed
    monkeypatch.setattr(app, "setup_richlog_logging", lambda: None)

    # Make READLINE_AVAILABLE True and provide a _add_history that raises (to exercise the except branch)
    called_history = {"count": 0}

    def fake_add_history(item):
        called_history["count"] += 1
        raise ValueError("history add failed")

    monkeypatch.setattr(cli, "READLINE_AVAILABLE", True)
    monkeypatch.setattr(cli, "_add_history", fake_add_history)

    # Make query_one raise to exercise input focus except branch
    def fake_query_one(selector, widget_type):
        raise RuntimeError("no widget")

    monkeypatch.setattr(app, "query_one", fake_query_one)

    # Make setup_cdp_logger raise to exercise that except branch
    def fake_setup_cdp_logger():
        raise RuntimeError("cdp failed")

    monkeypatch.setattr(app, "setup_cdp_logger", fake_setup_cdp_logger)

    # Capture telemetry events
    captured = []

    def fake_capture(ev):
        captured.append(ev)

    app._telemetry = SimpleNamespace(capture=fake_capture)

    # Run on_mount; should not raise despite non-critical exceptions
    app.on_mount()

    # Assertions: history attempted, telemetry captured with expected contents
    assert called_history["count"] >= 1
    assert len(captured) == 1
    ev = captured[0]
    assert isinstance(ev, CLITelemetryEvent)
    assert ev.action == "start"
    assert ev.mode == "interactive"
    assert ev.version == get_browser_use_version()
    # llm info should be present
    assert ev.model == "gpt-test-model"
    assert ev.model_provider == "test-provider"


def test_on_mount_richlog_failure_raises(monkeypatch):
    # Prepare app
    app = cli.BrowserUseApp(config={})

    # Make setup_richlog_logging raise to trigger RuntimeError branch
    def raising_setup():
        raise RuntimeError("boom")

    monkeypatch.setattr(app, "setup_richlog_logging", raising_setup)

    # Ensure READLINE_AVAILABLE False so history block is skipped (not necessary but keeps isolation)
    monkeypatch.setattr(cli, "READLINE_AVAILABLE", False)

    # Capture telemetry to ensure not called
    captured = []
    app._telemetry = SimpleNamespace(capture=lambda ev: captured.append(ev))

    with pytest.raises(RuntimeError) as excinfo:
        app.on_mount()

    assert "Failed to set up RichLog logging" in str(excinfo.value)
    # telemetry should not have been captured due to early failure
    assert captured == []
