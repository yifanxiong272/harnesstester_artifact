import pytest

import aider.coders.search_replace as sr


def test_dmp_apply_remap_success_round_011(monkeypatch):
    # Container to capture the FakeDMP instance created inside dmp_apply
    created = {}

    class FakeDMP:
        def __init__(self):
            # default values (will be overwritten by dmp_apply)
            self.Diff_Timeout = None
            self.Match_Threshold = None
            self.Match_Distance = None
            self.Match_MaxBits = None
            self.Patch_Margin = None
            created['inst'] = self

        def diff_main(self, a, b, c):
            # return a plausible diff structure
            return [(0, 'X')]

        def diff_cleanupSemantic(self, diff):
            # no-op cleanup
            diff.append(('semantic',))

        def diff_cleanupEfficiency(self, diff):
            # no-op
            pass

        def patch_make(self, search_text, diff):
            # produce a simple patches structure acceptable by other fake methods
            return [{'start1': 0, 'diffs': diff}]

        def diff_prettyHtml(self, diff):
            return '<html>diff</html>'

        def patch_toText(self, patches):
            # return deterministic textual representation
            return 'PATCH_TEXT'

        def patch_apply(self, patches, original_text):
            # simulate successful application
            return ('NEW_TEXT', [True])

    # ensure sr.diff_match_patch resolves to our FakeDMP factory
    monkeypatch.setattr(sr, 'diff_match_patch', lambda: FakeDMP())

    # track that map_patches is invoked and that it receives expected args
    map_called = {'called': False, 'args': None}

    def fake_map_patches(texts, patches, debug):
        map_called['called'] = True
        map_called['args'] = (texts, patches, debug)
        # return patches unchanged
        return patches

    monkeypatch.setattr(sr, 'map_patches', fake_map_patches)

    search_text = 'alpha'
    replace_text = 'ALPHA'
    original_text = 'some alpha text'

    result = sr.dmp_apply((search_text, replace_text, original_text), remap=True)

    # Assert the function returned the transformed text from our fake
    assert result == 'NEW_TEXT'

    # Ensure the FakeDMP instance had its attributes set for remap=True branch
    inst = created.get('inst')
    assert inst is not None
    assert inst.Diff_Timeout == 5
    assert inst.Match_Threshold == 0.95
    assert inst.Match_Distance == 500
    assert inst.Match_MaxBits == 128
    assert inst.Patch_Margin == 32

    # Ensure map_patches was called exactly and received debug=False
    assert map_called['called'] is True
    passed_texts, passed_patches, passed_debug = map_called['args']
    assert passed_texts == (search_text, replace_text, original_text)
    assert passed_debug is False


def test_dmp_apply_no_remap_partial_failure_round_011(monkeypatch):
    # Capture instance to assert attribute assignments
    created = {}

    class FakeDMP2:
        def __init__(self):
            self.Diff_Timeout = None
            self.Match_Threshold = None
            self.Match_Distance = None
            self.Match_MaxBits = None
            self.Patch_Margin = None
            created['inst'] = self

        def diff_main(self, a, b, c):
            return [(1, 'Y')]

        def diff_cleanupSemantic(self, diff):
            pass

        def diff_cleanupEfficiency(self, diff):
            pass

        def patch_make(self, search_text, diff):
            return [{'start1': 0, 'diffs': diff}]

        def patch_toText(self, patches):
            return 'PATCH_TEXT_2'

        def patch_apply(self, patches, original_text):
            # simulate partial failure (one False in success list)
            return ('SHOULD_NOT_BE_RETURNED', [True, False])

    monkeypatch.setattr(sr, 'diff_match_patch', lambda: FakeDMP2())

    # If map_patches is called in this branch, that's unexpected; fail the test
    def should_not_be_called(*args, **kwargs):
        raise AssertionError('map_patches should not be called when remap=False')

    monkeypatch.setattr(sr, 'map_patches', should_not_be_called)

    search_text = 'beta'
    replace_text = 'BETA'
    original_text = 'some beta text'

    result = sr.dmp_apply((search_text, replace_text, original_text), remap=False)

    # Because patch_apply returned a success list containing False, dmp_apply should return None
    assert result is None

    # Ensure the FakeDMP2 instance had attributes set for remap=False branch
    inst = created.get('inst')
    assert inst is not None
    assert inst.Diff_Timeout == 5
    assert inst.Match_Threshold == 0.5
    assert inst.Match_Distance == 100_000
    assert inst.Match_MaxBits == 32
    assert inst.Patch_Margin == 8
