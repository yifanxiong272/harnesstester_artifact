from rdagent.log.server import debug_app
import json


def _make_body():
    # deterministic two-element list exercising repeated-id appends
    return [{"id": "trace-1", "msg": "first"}, {"id": "trace-1", "msg": "second"}]


def test_probe_001():
    """Probe: POST a JSON array to receive_msgs and assert HTTP 200 and ordered state mutation.

    This test follows the boundary plan: it runs inside the module's Flask request
    context so request.get_json() returns the prepared array. It clears the
    module-level msgs_for_frontend to ensure a known starting state, posts the
    array, calls the public entrypoint receive_msgs(), and then asserts the
    observable invariant (200 response and ordered messages appended).
    """
    mod = debug_app

    # Deterministic setup: clear module state
    mod.msgs_for_frontend.clear()

    body = _make_body()
    payload = json.dumps(body)

    # Activation condition: run inside the module's Flask app request context
    with mod.app.test_request_context("/receive", method="POST", data=payload, content_type="application/json"):
        resp = mod.receive_msgs()

    # normalize return shape: expect (Response, status) as in the target code
    if isinstance(resp, tuple):
        response_obj, status = resp
        # If first element is a Flask Response, extract json if needed
        try:
            response_json = response_obj.get_json()
        except Exception:
            response_json = None
    else:
        response_obj = resp
        status = getattr(response_obj, "status_code", None)
        try:
            response_json = response_obj.get_json()
        except Exception:
            response_json = None

    # Primary oracle: must be HTTP 200 and the two messages appended in order
    assert status == 200, (
        f"Expected HTTP 200 from receive_msgs for JSON array input, got {status}. Response body: {response_json}"
    )

    # The module-level dict should now contain the two messages in order for 'trace-1'
    actual_tail = mod.msgs_for_frontend["trace-1"][-2:]
    assert actual_tail == ["first", "second"], (
        f"Expected msgs_for_frontend['trace-1'] to end with ['first','second'], got {actual_tail}"
    )
