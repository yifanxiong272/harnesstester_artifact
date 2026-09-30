# file: aider/onboarding.py:214-383
# asked: {"lines": [217, 218, 219, 220, 221, 223, 224, 225, 226, 227, 229, 230, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 247, 250, 251, 252, 257, 258, 259, 260, 262, 264, 266, 268, 269, 270, 271, 273, 274, 277, 278, 279, 280, 281, 282, 284, 285, 288, 289, 290, 291, 292, 295, 296, 297, 298, 299, 302, 303, 304, 305, 306, 307, 309, 311, 312, 313, 315, 316, 317, 319, 320, 321, 322, 325, 326, 327, 328, 329, 330, 331, 333, 336, 338, 339, 341, 342, 343, 344, 346, 347, 348, 349, 351, 352, 355, 357, 359, 362, 363, 364, 365, 366, 367, 369, 370, 372, 373, 374, 375, 376, 378, 379, 381, 382, 383], "branches": [[218, 219], [218, 223], [233, 234], [233, 257], [235, 236], [235, 250], [273, 274], [273, 278], [288, 289], [288, 295], [295, 296], [295, 302], [338, 339], [338, 341], [341, 342], [341, 346], [346, 347], [346, 351], [357, 359], [357, 381]]}
# gained: {"lines": [217, 218, 219, 220, 221, 223, 224, 225, 226, 227, 229, 230, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 247, 262, 266, 268, 269, 270, 271, 273, 274, 277, 278, 279, 280, 281, 282, 284, 285, 288, 295, 296, 297, 298, 299, 302, 303, 304, 305, 306, 307, 309, 311, 312, 313, 315, 316, 317, 319, 320, 325, 326, 327, 336, 338, 341, 346, 351, 352, 355, 357, 359, 362, 363, 364, 365, 366, 367, 369, 370, 372, 373, 374, 375, 376, 378, 379, 381, 382, 383], "branches": [[218, 219], [218, 223], [233, 234], [235, 236], [273, 274], [273, 278], [288, 295], [295, 296], [295, 302], [338, 341], [341, 346], [346, 351], [357, 359], [357, 381]]}

import io as _io
import os
import types

import pytest

import aider.onboarding as onboarding


class DummyIO:
    def __init__(self):
        self.outputs = []
        self.errors = []
        self.warnings = []

    def tool_output(self, *args, **kwargs):
        self.outputs.append((args, kwargs))

    def tool_error(self, *args):
        self.errors.append(args)

    def tool_warning(self, *args):
        self.warnings.append(args)


class DummyAnalytics:
    def __init__(self):
        self.events = []

    def event(self, name, **kwargs):
        self.events.append((name, kwargs))


def _make_fake_tcp_server(code_in_callback=None, path_other=None):
    class FakeTCPServer:
        def __init__(self, server_address, RequestHandlerClass):
            self.RequestHandlerClass = RequestHandlerClass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def handle_request(self):
            HandlerClass = self.RequestHandlerClass
            handler = object.__new__(HandlerClass)

            if path_other is not None:
                handler.path = path_other
            elif code_in_callback is not None:
                handler.path = f"/callback/aider?code={code_in_callback}"
            else:
                handler.path = "/callback/aider"

            handler.wfile = _io.BytesIO()

            def send_response(this, code):
                this._last_status = code

            def send_header(this, k, v):
                if not hasattr(this, "_headers"):
                    this._headers = []
                this._headers.append((k, v))

            def end_headers(this):
                this._ended = True

            handler.send_response = types.MethodType(send_response, handler)
            handler.send_header = types.MethodType(send_header, handler)
            handler.end_headers = types.MethodType(end_headers, handler)

            HandlerClass.do_GET(handler)

    return FakeTCPServer


def _install_common_mocks(monkeypatch, tmp_path, *, code="TESTCODE", api_key="API_KEY_ABC", make_save_fail=False, exchange_result_provided=True, exchange_result=None):
    """
    If exchange_result_provided is True, set exchange_code_for_key to return exchange_result.
    If exchange_result_provided is False, do not set exchange_code_for_key here (test may override).
    """
    monkeypatch.setattr(onboarding, "find_available_port", lambda: 9000)
    monkeypatch.setattr(onboarding, "generate_pkce_codes", lambda: ("verifier", "challenge"))
    monkeypatch.setattr(onboarding, "webbrowser", types.SimpleNamespace(open=lambda url: True))
    monkeypatch.setattr(onboarding.urls, "website", "https://aider.test")
    FakeTCPServer = _make_fake_tcp_server(code_in_callback=code)
    monkeypatch.setattr(onboarding.socketserver, "TCPServer", FakeTCPServer)
    if exchange_result_provided:
        monkeypatch.setattr(onboarding, "exchange_code_for_key", lambda auth_code, verifier, io: exchange_result if exchange_result is not None else api_key)
    # else: leave exchange_code_for_key untouched so test can override

    def fake_expanduser(p):
        return str(tmp_path)

    monkeypatch.setattr(onboarding.os.path, "expanduser", fake_expanduser)

    if make_save_fail:
        def fail_makedirs(path, exist_ok=False):
            raise Exception("disk full")
        monkeypatch.setattr(onboarding.os, "makedirs", fail_makedirs)

    return DummyIO(), DummyAnalytics()


def _joined_args(args_tuple):
    return " ".join(str(a) for a in args_tuple)


def test_no_port_available(monkeypatch):
    monkeypatch.setattr(onboarding, "find_available_port", lambda: None)
    io = DummyIO()
    analytics = DummyAnalytics()
    res = onboarding.start_openrouter_oauth_flow(io, analytics)
    assert res is None
    assert len(io.errors) == 2
    first = _joined_args(io.errors[0])
    second = _joined_args(io.errors[1])
    assert "Could not find an available port" in first
    assert "Please ensure a port" in second


def test_server_start_failure(monkeypatch):
    monkeypatch.setattr(onboarding, "find_available_port", lambda: 9001)

    class BadServer:
        def __init__(self, addr, handler):
            pass

        def __enter__(self):
            raise RuntimeError("bind failed")

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(onboarding.socketserver, "TCPServer", BadServer)
    io = DummyIO()
    analytics = DummyAnalytics()
    res = onboarding.start_openrouter_oauth_flow(io, analytics)
    assert res is None
    assert any("Failed to start or run temporary server" in _joined_args(e) for e in io.errors)


def test_successful_flow_saves_file(tmp_path, monkeypatch):
    io, analytics = _install_common_mocks(monkeypatch, tmp_path, code="GOODCODE", api_key="MYAPIKEY", exchange_result_provided=True, exchange_result="MYAPIKEY")

    res = onboarding.start_openrouter_oauth_flow(io, analytics)
    assert res == "MYAPIKEY"
    assert os.environ.get("OPENROUTER_API_KEY") == "MYAPIKEY"

    key_file = tmp_path / "oauth-keys.env"
    assert key_file.exists()
    content = key_file.read_text(encoding="utf-8")
    assert 'OPENROUTER_API_KEY="MYAPIKEY"' in content

    assert any(ev[0] == "oauth_flow_success" for ev in analytics.events)
    os.environ.pop("OPENROUTER_API_KEY", None)


def test_save_failure_returns_key_and_records_event(tmp_path, monkeypatch):
    io, analytics = _install_common_mocks(monkeypatch, tmp_path, code="SAVEFAILCODE", api_key="KEY123", make_save_fail=True, exchange_result_provided=True, exchange_result="KEY123")

    res = onboarding.start_openrouter_oauth_flow(io, analytics)
    assert res == "KEY123"
    assert os.environ.get("OPENROUTER_API_KEY") == "KEY123"
    assert any(ev[0] == "oauth_flow_save_failed" for ev in analytics.events)
    assert any("Successfully obtained key, but failed to save it" in _joined_args(err) or "disk full" in _joined_args(err) for err in io.errors)
    os.environ.pop("OPENROUTER_API_KEY", None)


def test_exchange_code_failure_reports_code_exchange_failed(tmp_path, monkeypatch):
    # Install mocks but do NOT set exchange_code_for_key in helper; override to return None
    io, analytics = _install_common_mocks(monkeypatch, tmp_path, code="BAD_EXCHANGE", api_key="SHOULDNOTBESET", exchange_result_provided=False)

    # Now force exchange_code_for_key to return None to simulate exchange failure
    monkeypatch.setattr(onboarding, "exchange_code_for_key", lambda auth_code, verifier, io: None)

    res = onboarding.start_openrouter_oauth_flow(io, analytics)
    assert res is None
    assert any(ev[0] == "oauth_flow_failed" and ev[1].get("reason") == "code_exchange_failed" for ev in analytics.events)
