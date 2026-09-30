import re
import pandas as pd
import types
from types import SimpleNamespace
from pathlib import Path
import pytest

from rdagent.log.ui import utils as ui_utils

# Helpers used in tests
class FakeMessage:
    def __init__(self, tag, content):
        self.tag = tag
        self.content = content


class FakeFileStorage:
    """
    A minimal fake replacement for FileStorage used by get_score_stat.
    It is configured with lists for specific query keys: 'trace',
    'mle:<loop_id>' and 'direct:<loop_id>'. iter_msg inspects
    tag or pattern arguments and yields the configured messages.
    """

    def __init__(self, mapping):
        # mapping is a dict with keys like 'trace', 'mle:7', 'direct:7'
        self._mapping = mapping

    def iter_msg(self, tag=None, pattern=None):
        if tag == "trace":
            for m in self._mapping.get("trace", []):
                yield m
            return
        if tag is not None and tag.startswith("Loop_") and tag.endswith(".running.mle_score"):
            # extract loop id
            m = re.search(r"Loop_(\d+)", tag)
            if m:
                lid = m.group(1)
                for i in self._mapping.get(f"mle:{lid}", []):
                    yield i
            return
        if pattern is not None and pattern.startswith("Loop_") and "direct_exp_gen" in pattern:
            m = re.search(r"Loop_(\d+)", pattern)
            if m:
                lid = m.group(1)
                for i in self._mapping.get(f"direct:{lid}", []):
                    yield i
            return
        # default: yield nothing
        return
        yield


def make_final_trace(hist_pairs, idx2loop_id=None):
    """Create a simple final_trace object having hist and optional idx2loop_id."""
    final = SimpleNamespace()
    final.hist = hist_pairs
    if idx2loop_id is not None:
        final.idx2loop_id = idx2loop_id
    return final


def make_exp_with_result(value):
    # exp.result should be something pd.DataFrame(pd.Series(...)) can handle
    s = pd.Series([value], index=["ensemble"])
    exp = SimpleNamespace(result=s)
    return exp


def make_fb(decision_value):
    return SimpleNamespace(decision=decision_value)


def install_fake(monkeypatch, mapping):
    """Patch ui_utils.FileStorage and ui_utils.extract_json to deterministic fakes.
    mapping is passed into FakeFileStorage to control iter_msg outputs.
    The extract_json is implemented to map specific sentinel contents to return dicts.
    """

    def fake_fs_constructor(path):
        return FakeFileStorage(mapping)

    def fake_extract_json(obj):
        # obj is the message.content passed by test; we expect it to be a sentinel string
        # or a simple dict. Support both.
        if isinstance(obj, dict) and "_mle" in obj:
            return obj["_mle"]
        if isinstance(obj, str) and obj.startswith("mle_"):
            # mle_<loopid>_<case>
            parts = obj.split("_")
            # examples created in tests below
            if parts[-1] == "score_none":
                return {"is_lower_better": True, "score": None}
            if parts[-1] == "score_09":
                return {"is_lower_better": False, "score": 0.9}
        # default, return empty dict
        return {}

    monkeypatch.setattr(ui_utils, "FileStorage", fake_fs_constructor)
    monkeypatch.setattr(ui_utils, "extract_json", fake_extract_json)


def test_get_score_stat_empty_trace_round_020(monkeypatch, tmp_path):
    # When no trace messages are present, function should return four Nones
    mapping = {"trace": []}
    install_fake(monkeypatch, mapping)

    res = ui_utils.get_score_stat(tmp_path, sota_loop_id=1)
    assert res == (None, None, None, None)


def test_get_score_stat_merge_after_round_020(monkeypatch, tmp_path):
    # This scenario: final_trace has one loop, idx2loop_id is absent -> loop id parsed via tag.
    # The loop is a merge loop (direct_exp_gen contains a merge uri), decision is True.
    # mle_score has a numeric score and is_lower_better == False -> improvements computed via max

    # Prepare exp and fb
    exp = make_exp_with_result(0.7)
    fb = make_fb(True)
    final_trace = make_final_trace([(exp, fb)])

    # Provide trace messages list (all_trace). The code uses all_trace[-1].content -> final_trace
    # and later uses all_trace[loop_index].tag to regex-extract loop_id.
    trace_msg0 = FakeMessage(tag="Loop_7/trace", content=final_trace)
    # iter_msg(pattern=...) for direct_exp_gen: include a message whose content provides a 'uri' containing merge
    direct_msg = FakeMessage(tag="Loop_7/direct", content={"uri": "scenarios.data_science.proposal.exp_gen.merge.something"})
    # mle_score message content will be a sentinel string that fake_extract_json recognizes
    mle_msg = FakeMessage(tag="Loop_7.mle", content="mle_7_score_09")

    mapping = {
        "trace": [trace_msg0],
        "direct:7": [direct_msg],
        "mle:7": [mle_msg],
    }

    install_fake(monkeypatch, mapping)

    # Call with sota_loop_id matching loop id 7 so submit_is_merge becomes True
    valid_improve, test_improve, submit_is_merge, merge_sota_rate = ui_utils.get_score_stat(tmp_path, sota_loop_id=7)

    assert submit_is_merge is True
    assert valid_improve is True  # valid_before_merge empty, valid_after_merge present -> improvement
    assert test_improve is True   # test_before empty, test_after present and higher -> improvement
    assert merge_sota_rate == 1.0


def test_get_score_stat_no_merge_with_idx2_round_020(monkeypatch, tmp_path):
    # This scenario: final_trace has idx2loop_id mapping provided.
    # The loop is NOT a merge (direct_exp_gen yields nothing). decision True.
    # mle_score has score None and is_lower_better True -> no improvements and merge rate 0

    exp = make_exp_with_result(0.4)
    fb = make_fb(True)
    final_trace = make_final_trace([(exp, fb)], idx2loop_id={0: 100})

    trace_msg0 = FakeMessage(tag="Loop_100/trace", content=final_trace)
    # No direct messages -> not a merge
    # mle_score message with score None
    mle_msg = FakeMessage(tag="Loop_100.mle", content="mle_100_score_none")

    mapping = {
        "trace": [trace_msg0],
        # no direct:100 entry -> no merges
        "mle:100": [mle_msg],
    }

    install_fake(monkeypatch, mapping)

    valid_improve, test_improve, submit_is_merge, merge_sota_rate = ui_utils.get_score_stat(tmp_path, sota_loop_id=999)

    # sota_loop_id does not match 100, so submit_is_merge stays False
    assert submit_is_merge is False
    # No after-merge entries exist in either list -> no improvements
    assert valid_improve is False
    assert test_improve is False
    # No merge loops recorded -> rate 0
    assert merge_sota_rate == 0
