# file: backend/server/app.py:198-224
# asked: {"lines": [200, 201, 202, 204, 205, 206, 207, 208, 209, 211, 212, 213, 214, 215, 216, 217, 220, 221, 222, 223, 224], "branches": [[208, 209], [208, 211]]}
# gained: {"lines": [200, 201, 202, 204, 205, 206, 207, 208, 209, 211, 212, 213, 214, 215, 216, 217, 220, 221, 222, 223, 224], "branches": [[208, 209]]}

import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException


def _load_app_module():
    # Find the app.py file in the repository (search upward from this test file)
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "gpt-researcher" / "backend" / "server" / "app.py"
        if candidate.exists():
            path = candidate
            break
    else:
        raise FileNotFoundError("Could not find gpt-researcher/backend/server/app.py")

    spec = importlib.util.spec_from_file_location("tested_app_module", str(path))
    module = importlib.util.module_from_spec(spec)
    # Ensure module is importable under a stable name for monkeypatching
    sys.modules["tested_app_module"] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_create_or_update_report_uses_existing_timestamp_and_defaults(monkeypatch):
    module = _load_app_module()
    func = getattr(module, "create_or_update_report")

    # Prepare deterministic time: now_ms = 1000 * 1 = 1000
    class DummyTime:
        @staticmethod
        def time():
            return 1.0

    monkeypatch.setattr(module, "time", DummyTime)

    # Prepare a dummy existing report with a higher timestamp than now_ms
    existing_report = {"id": "r1", "timestamp": 9999999}

    async def dummy_get_report(rid):
        assert rid == "r1"
        return existing_report

    # Capture what upsert_report is called with
    upsert_calls = []

    async def dummy_upsert_report(rid, report):
        upsert_calls.append((rid, report))
        # simulate async completion
        return None

    dummy_report_store = type("R", (), {"get_report": staticmethod(lambda rid: dummy_get_report(rid)),
                                        "upsert_report": staticmethod(lambda rid, report: dummy_upsert_report(rid, report))})
    # monkeypatch report_store in module
    monkeypatch.setattr(module, "report_store", dummy_report_store)

    # Create a fake request whose json() returns a dict without timestamp (to force now_ms use)
    class FakeRequest:
        def __init__(self, payload):
            self._payload = payload

        async def json(self):
            return self._payload

    payload = {
        "id": "r1",
        "question": "Q?",
        "answer": "A!",
        # omit orderedData and chatMessages to test defaulting to empty lists
    }
    request = FakeRequest(payload)

    result = await func(request)

    # Verify return value
    assert result == {"success": True, "id": "r1"}

    # Verify upsert was called exactly once with the merged report
    assert len(upsert_calls) == 1
    rid, report = upsert_calls[0]
    assert rid == "r1"
    # timestamp should be max(now_ms, existing.timestamp) -> existing timestamp (9999999)
    assert report["timestamp"] == existing_report["timestamp"]
    assert report["id"] == "r1"
    assert report["question"] == "Q?"
    assert report["answer"] == "A!"
    # defaults:
    assert report["orderedData"] == []
    assert report["chatMessages"] == []


@pytest.mark.asyncio
async def test_create_or_update_report_logs_and_raises_on_exception(monkeypatch):
    module = _load_app_module()
    func = getattr(module, "create_or_update_report")

    # Make request.json raise an exception to trigger the except block
    class BadRequest:
        async def json(self):
            raise RuntimeError("boom!")

    # Replace logger with a dummy that captures error calls
    logged = []

    class DummyLogger:
        @staticmethod
        def error(msg):
            logged.append(msg)

    monkeypatch.setattr(module, "logger", DummyLogger)

    # Call function and assert HTTPException is raised with status 500 and that logger.error was called
    with pytest.raises(HTTPException) as excinfo:
        await func(BadRequest())

    assert excinfo.value.status_code == 500
    # The detail should include the original exception message
    assert "boom!" in excinfo.value.detail

    # Ensure logger.error was called and the message contains our prefix text
    assert any("Error processing report creation" in m for m in logged)
