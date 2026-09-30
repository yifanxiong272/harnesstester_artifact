import importlib
from aider.coders import udiff_coder as udiff_mod
from aider.coders.udiff_coder import apply_partial_hunk


def test_apply_partial_hunk_empty_contexts_round_050(monkeypatch):
    """When there are no preceding/following context lines, the function should
    call directly_apply_hunk once with changes as the combined payload and
    return the truthy result from that call.
    """
    calls = []

    def fake_directly_apply_hunk(content_arg, combined):
        # record calls for assertions
        calls.append((list(content_arg), list(combined)))
        # deterministic match: return a sentinel when the combined equals the changes
        if combined == ['+new']:
            return 'OK'
        return None

    monkeypatch.setattr(udiff_mod, 'directly_apply_hunk', fake_directly_apply_hunk)

    result = apply_partial_hunk(['orig-line'], [], ['+new'], [])

    assert result == 'OK'
    # ensure we actually invoked the patched directly_apply_hunk with expected combined
    assert calls, "directly_apply_hunk was not called"
    assert calls[0][1] == ['+new']


def test_apply_partial_hunk_use_prec_true_round_050(monkeypatch):
    """Force a branch where use_prec is truthy so this_prec is a non-empty slice
    and ensure the call using that this_prec + changes + this_foll triggers a return.
    """
    calls = []

    def fake_directly_apply_hunk(content_arg, combined):
        calls.append((list(content_arg), list(combined)))
        # We expect one combination to be ['p2', 'C'] (preceding_context[-1:] + changes)
        if combined == ['p2', 'C']:
            return 'MATCHED'
        return None

    monkeypatch.setattr(udiff_mod, 'directly_apply_hunk', fake_directly_apply_hunk)

    result = apply_partial_hunk(['orig'], ['p1', 'p2'], ['C'], ['f1'])

    assert result == 'MATCHED'
    # Confirm that at least one recorded call used the expected preceding slice
    assert any(call[1] == ['p2', 'C'] for call in calls), "expected combined payload not seen"


def test_apply_partial_hunk_no_match_round_050(monkeypatch):
    """If directly_apply_hunk never returns a truthy value, apply_partial_hunk should
    exhaust all combinations and return None.
    """
    calls = []

    def fake_directly_apply_hunk(content_arg, combined):
        # Always return falsy; record calls so we know the function iterated
        calls.append(list(combined))
        return None

    monkeypatch.setattr(udiff_mod, 'directly_apply_hunk', fake_directly_apply_hunk)

    result = apply_partial_hunk(['orig'], ['a'], ['x'], ['b'])

    assert result is None
    # The function should have attempted at least one combination
    assert len(calls) >= 1
