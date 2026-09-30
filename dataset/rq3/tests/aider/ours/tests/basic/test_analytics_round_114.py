import json
import types
import aider.analytics as analytics
from aider.analytics import Analytics


def test_event_with_main_model_and_numeric_and_strings_round_114(tmp_path, monkeypatch):
    # Create an Analytics instance without running __init__ to avoid side effects
    a = object.__new__(Analytics)
    a.user_id = "user-123"

    # Dummy Mixpanel that records calls
    recorded = {}

    class DummyMP:
        def track(self, user_id, event_name, properties):
            recorded["track"] = (user_id, event_name, properties)

    # Dummy PostHog that records calls
    class DummyPH:
        def capture(self, event_name, distinct_id=None, properties=None):
            recorded["capture"] = (event_name, distinct_id, properties)

    a.mp = DummyMP()
    a.ph = DummyPH()
    # logfile path - will be written to
    logfile = tmp_path / "analytics.log"
    a.logfile = str(logfile)

    # Patch redact to deterministic output and time to fixed value
    monkeypatch.setattr(analytics.Analytics, "_redact_model_name", lambda self, m: f"redacted-{m}")
    monkeypatch.setattr(analytics.time, "time", lambda: 1234567890)

    # Main model with attributes used by event
    class MainModel:
        def __str__(self):
            return "mainstr"

        weak_model = "weakstr"
        editor_model = "editorstr"

    main_model = MainModel()

    # Call event with numeric and non-numeric kwargs to hit both branches
    a.event("evt", main_model, count=7, info={"a": 1})

    # Verify Mixpanel track was invoked and properties preserved/converted correctly
    assert "track" in recorded
    user_id, event_name, props = recorded["track"]
    assert user_id == "user-123"
    assert event_name == "evt"

    # main_model, weak_model, editor_model should have been redacted
    assert props["main_model"] == "redacted-mainstr"
    assert props["weak_model"] == "redacted-weakstr"
    assert props["editor_model"] == "redacted-editorstr"

    # Numeric value should remain numeric
    assert isinstance(props["count"], (int, float)) and props["count"] == 7

    # Non-numeric value should be converted to a string representation
    assert isinstance(props["info"], str) and "a" in props["info"]

    # Verify PostHog capture was invoked with the same properties
    assert "capture" in recorded
    ph_event, ph_distinct, ph_props = recorded["capture"]
    assert ph_event == "evt"
    assert ph_distinct == "user-123"
    assert ph_props["count"] == 7

    # Verify logfile was written and contains expected fields (including deterministic time)
    with open(a.logfile, "r") as f:
        line = f.readline().strip()
    entry = json.loads(line)
    assert entry["event"] == "evt"
    assert entry["user_id"] == "user-123"
    assert entry["time"] == 1234567890
    # properties persisted to file should include same numeric and redacted values
    file_props = entry["properties"]
    assert file_props["main_model"] == "redacted-mainstr"
    assert file_props["count"] == 7


def test_event_mixpanel_exception_disables_mp_and_logfile_oserror_round_114(monkeypatch):
    # Create Analytics instance without __init__ to control attributes
    a = object.__new__(Analytics)
    a.user_id = "u2"

    # Mixpanel tracker that raises MixpanelException to trigger the except branch
    class BadMP:
        def track(self, *args, **kwargs):
            raise analytics.MixpanelException("boom")

    a.mp = BadMP()
    a.ph = None
    a.logfile = "will_fail.log"

    # Ensure time is deterministic even if logfile write fails
    monkeypatch.setattr(analytics.time, "time", lambda: 999)

    # Replace module-level open with one that raises OSError to hit the logfile-exception branch
    def open_raises(*args, **kwargs):
        raise OSError("disk error")

    monkeypatch.setattr(analytics, "open", open_raises)

    # Call event and ensure it does not raise; Mixpanel exception should disable mp
    a.event("evt2", None, foo="bar")
    assert a.mp is None

    # Even though open raised, function should complete silently (OSError is swallowed)
