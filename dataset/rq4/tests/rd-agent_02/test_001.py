def test_probe_001():
    import json
    from collections import defaultdict
    import rdagent.log.server.debug_app as debug_app

    # Deterministic setup: ensure testing mode and a fresh msgs mapping
    debug_app.app.testing = True
    debug_app.msgs_for_frontend = defaultdict(list)

    payload = [{"id": "A", "msg": {"tag": "t"}}]

    client = debug_app.app.test_client()
    resp = client.post("/receive", json=payload)

    # Observable HTTP success is expected by the invariant
    assert resp.status_code == 200, (
        "Expected HTTP 200 but got {}. Response body: {}".format(
            resp.status_code, resp.get_data(as_text=True)
        )
    )
    assert resp.get_json() == {"status": "success"}

    # Primary behavioral oracle: the posted message must be appended under id 'A'
    assert debug_app.msgs_for_frontend["A"] == [{"tag": "t"}], (
        "msgs_for_frontend contents unexpected: {}".format(dict(debug_app.msgs_for_frontend))
    )
