# file: aider/coders/search_replace.py:260-326
# asked: {"lines": [261, 264, 266, 267, 270, 271, 272, 273, 274, 276, 277, 278, 279, 281, 282, 283, 285, 287, 288, 289, 291, 292, 294, 295, 296, 297, 298, 299, 304, 305, 307, 309, 311, 313, 315, 318, 319, 323, 324, 326], "branches": [[270, 271], [270, 276], [287, 288], [287, 304], [291, 292], [291, 294], [294, 295], [294, 304], [304, 305], [304, 307], [313, 315], [313, 323], [323, 324], [323, 326]]}
# gained: {"lines": [261, 264, 266, 267, 270, 271, 272, 273, 274, 276, 277, 278, 279, 281, 282, 283, 285, 287, 304, 305, 307, 309, 311, 313, 323, 324, 326], "branches": [[270, 271], [270, 276], [287, 304], [304, 305], [304, 307], [313, 323], [323, 324], [323, 326]]}

import pytest

import importlib


def setup_dummy_dmp(recorded_instances, apply_result=None):
    """
    Return a Dummy diff_match_patch class factory that appends created instances
    to recorded_instances list. apply_result can be provided to control the
    return value of patch_apply: a tuple (new_text, success_list). If not
    provided, patch_apply will replace the stored search_text with replace_text
    once in the original_text.
    """

    class DummyPatch:
        def __init__(self, start1, diffs):
            self.start1 = start1
            self.diffs = diffs

    class DummyDMP:
        def __init__(self):
            # record instance
            recorded_instances.append(self)
            # default attributes that the real dmp has
            self.Diff_Timeout = None
            self.Match_Threshold = None
            self.Match_Distance = None
            self.Match_MaxBits = None
            self.Patch_Margin = None
            # internal storage for diff_main arguments
            self._search = None
            self._replace = None

        def diff_main(self, search_text, replace_text, _none):
            # store for patch_apply
            self._search = search_text
            self._replace = replace_text
            # produce a simple diff list (op, text)
            return [(0, search_text), (1, replace_text)]

        def diff_cleanupSemantic(self, diff):
            # pretend to cleanup; no-op
            pass

        def diff_cleanupEfficiency(self, diff):
            # no-op
            pass

        def patch_make(self, search_text, diff):
            # return a list with one DummyPatch; start1 will be 0
            return [DummyPatch(0, diff)]

        def patch_toText(self, patches):
            return "DUMMY_PATCH_TEXT"

        def diff_prettyHtml(self, diff):
            return "<html>diff</html>"

        def patch_apply(self, patches, original_text):
            # If apply_result provided, use it
            if apply_result is not None:
                return apply_result
            # otherwise do a simple replace of first occurrence and success True
            if self._search is None:
                return original_text, [True]
            new_text = original_text.replace(self._search, self._replace, 1)
            # success True if replacement changed the text, else False
            success = new_text != original_text
            return new_text, [success]

    return DummyDMP


def test_dmp_apply_remap_true_success(monkeypatch):
    # Import module under test
    sr = importlib.import_module("aider.coders.search_replace")

    recorded_instances = []
    # create DummyDMP that will behave normally (success)
    DummyDMP = setup_dummy_dmp(recorded_instances)

    # monkeypatch the diff_match_patch class in module
    monkeypatch.setattr(sr, "diff_match_patch", DummyDMP)

    # Track whether map_patches called and what it received
    map_called = {}

    def fake_map_patches(texts, patches, debug):
        # record call
        map_called["called"] = True
        map_called["texts"] = texts
        map_called["patches"] = patches
        map_called["debug"] = debug
        # return the patches unchanged
        return patches

    monkeypatch.setattr(sr, "map_patches", fake_map_patches)

    # Prepare texts
    search_text = "hello"
    replace_text = "HELLO"
    original_text = "hello world"

    # Call with remap True (default)
    result = sr.dmp_apply((search_text, replace_text, original_text), remap=True)

    # Assertions: result should be the replaced text
    assert result == "HELLO world"

    # Ensure map_patches was called
    assert map_called.get("called", False) is True
    assert map_called["texts"] == (search_text, replace_text, original_text)
    # recorded instance should exist
    assert recorded_instances, "DummyDMP instance not created"
    inst = recorded_instances[-1]
    # remap True sets these specific attributes
    assert inst.Match_Threshold == 0.95
    assert inst.Match_Distance == 500
    assert inst.Match_MaxBits == 128
    assert inst.Patch_Margin == 32


def test_dmp_apply_remap_false_all_success_false_returns_none(monkeypatch):
    # Import module under test
    sr = importlib.import_module("aider.coders.search_replace")

    recorded_instances = []
    # create DummyDMP configured to return success list containing a False
    apply_result = ("irrelevant", [True, False])
    DummyDMP = setup_dummy_dmp(recorded_instances, apply_result=apply_result)

    # monkeypatch the diff_match_patch class in module
    monkeypatch.setattr(sr, "diff_match_patch", DummyDMP)

    # Ensure map_patches is NOT called when remap=False by making it raise if invoked
    def raise_if_called(*args, **kwargs):
        raise AssertionError("map_patches should not be called when remap=False")

    monkeypatch.setattr(sr, "map_patches", raise_if_called)

    # Prepare texts
    search_text = "foo"
    replace_text = "bar"
    original_text = "something with foo inside"

    # Call with remap False
    result = sr.dmp_apply((search_text, replace_text, original_text), remap=False)

    # Since patch_apply returned a success list containing False, function should return None
    assert result is None

    # recorded instance should exist and reflect the remap=False attribute settings
    assert recorded_instances, "DummyDMP instance not created"
    inst = recorded_instances[-1]
    assert inst.Match_Threshold == 0.5
    assert inst.Match_Distance == 100000
    assert inst.Match_MaxBits == 32
    assert inst.Patch_Margin == 8
