# file: openhands/runtime/utils/edit.py:247-408
# asked: {"lines": [248, 250, 251, 253, 254, 257, 258, 260, 261, 262, 263, 264, 266, 267, 268, 269, 270, 271, 273, 274, 275, 278, 279, 281, 282, 284, 285, 286, 289, 290, 291, 293, 294, 296, 297, 298, 299, 300, 301, 303, 304, 305, 307, 308, 309, 310, 313, 314, 315, 316, 317, 318, 319, 323, 324, 327, 330, 333, 334, 335, 336, 337, 338, 342, 343, 344, 345, 346, 348, 349, 351, 352, 353, 354, 355, 356, 358, 359, 361, 363, 364, 365, 367, 368, 369, 372, 373, 376, 377, 378, 379, 381, 382, 385, 386, 387, 388, 390, 391, 392, 393, 394, 395, 396, 399, 400, 401, 402, 403, 404, 405, 407, 408], "branches": [[249, 253], [249, 273], [260, 261], [260, 262], [262, 263], [262, 266], [273, 274], [273, 278], [285, 286], [285, 289], [289, 290], [289, 323], [293, 294], [293, 313], [303, 304], [303, 313], [324, 327], [324, 330], [334, 335], [334, 363], [351, 352], [351, 358], [367, 368], [367, 376], [385, 386], [385, 399], [390, 391], [390, 399]]}
# gained: {"lines": [248, 250, 251, 253, 254, 257, 258, 260, 261, 262, 266, 267, 268, 269, 270, 271, 273, 274, 275, 278, 279, 281, 282, 284, 285, 286, 289, 290, 291, 293, 294, 296, 297, 298, 299, 300, 301, 303, 304, 305, 307, 308, 309, 310, 313, 314, 315, 316, 317, 318, 319, 323, 324, 327, 333, 334, 335, 336, 337, 338, 342, 343, 344, 345, 346, 348, 349, 351, 352, 353, 354, 355, 356, 358, 359, 361, 363, 364, 365, 367, 368, 369, 372, 373, 376, 377, 378, 379, 381, 382, 385, 386, 387, 388, 390, 391, 392, 393, 394, 395, 396], "branches": [[249, 253], [249, 273], [260, 261], [260, 262], [262, 266], [273, 274], [273, 278], [285, 286], [285, 289], [289, 290], [289, 323], [293, 294], [303, 304], [303, 313], [324, 327], [334, 335], [334, 363], [351, 352], [351, 358], [367, 368], [367, 376], [385, 386], [390, 391]]}

import types
import pytest
import importlib

# Import the module under test
edit_mod = importlib.import_module("openhands.runtime.utils.edit")


class DummyChunk:
    def __init__(self, lr0, lr1, sim, vis_text="VIS"):
        self.line_range = (lr0, lr1)
        self.normalized_lcs = sim
        self._vis = vis_text

    def visualize(self):
        return self._vis


class DummyLLM:
    def __init__(self, metrics=None):
        if metrics is None:
            metrics = {"dummy": 1}
        self.metrics = metrics


# Define distinct observation classes so isinstance checks don't collide
class TestErrorObs:
    def __init__(self, content=""):
        self.content = content
        self.llm_metrics = None

    def __repr__(self):
        return f"<ErrorObs content={self.content!r} metrics={self.llm_metrics!r}>"


class TestFileReadObs:
    def __init__(self, content=""):
        self.content = content
        self.llm_metrics = None

    def __repr__(self):
        return f"<FileReadObs content={self.content!r} metrics={self.llm_metrics!r}>"


class TestFileWriteObs:
    def __init__(self, path="", content=""):
        self.path = path
        self.content = content
        self.llm_metrics = None

    def __repr__(self):
        return f"<FileWriteObs path={self.path!r} content={self.content!r} metrics={self.llm_metrics!r}>"


class TestFileEditObs:
    def __init__(self, content="", path="", prev_exist=False, old_content="", new_content=""):
        self.content = content
        self.path = path
        self.prev_exist = prev_exist
        self.old_content = old_content
        self.new_content = new_content
        self.llm_metrics = None

    def __repr__(self):
        return f"<FileEditObs path={self.path!r} prev={self.prev_exist} old_len={len(self.old_content)} new_len={len(self.new_content)}>"


# Create a FakeRuntime that does NOT inherit from the mixin to avoid abstract methods
class FakeRuntime:
    def __init__(self):
        # attributes that llm_based_edit expects
        self.config = types.SimpleNamespace(
            sandbox=types.SimpleNamespace(enable_auto_lint=True),
            get_llm_config=lambda name: types.SimpleNamespace(caching_prompt=False),
        )
        self.draft_editor_llm = DummyLLM(metrics={"calls": 0})
        self.MAX_LINES_TO_EDIT = 300

        # controllable behaviors
        self.next_read_obs = None
        self.next_write_obs = None
        self.next_lint_error = None
        self.correct_edit_return = None
        self.last_written = None
        self.validate_return = None

    # methods used by the mixin's llm_based_edit
    def read(self, action):
        return self.next_read_obs

    def write(self, action):
        # record write and return preconfigured observation
        self.last_written = getattr(action, "content", None)
        return self.next_write_obs

    def _validate_range(self, start, end, total_lines):
        return self.validate_return

    def _get_lint_error(self, suffix, old_content, new_content, filepath, diff):
        return self.next_lint_error

    def correct_edit(self, file_content, error_obs, retry_num=0):
        return self.correct_edit_return

    def check_retry_num(self, retry_num: int) -> bool:
        return True


@pytest.fixture(autouse=True)
def patch_obs_and_utils(monkeypatch):
    """
    Monkeypatch the module-level observation classes and utility functions
    to controllable test doubles so we don't depend on external constructors.
    """
    monkeypatch.setattr(edit_mod, "ErrorObservation", TestErrorObs)
    monkeypatch.setattr(edit_mod, "FileReadObservation", TestFileReadObs)
    monkeypatch.setattr(edit_mod, "FileWriteObservation", TestFileWriteObs)
    monkeypatch.setattr(edit_mod, "FileEditObservation", TestFileEditObs)

    # Patch get_diff to a deterministic function
    def fake_get_diff(a, b, path):
        return f"DIFF:{len(a)}->{len(b)}@{path}"

    monkeypatch.setattr(edit_mod, "get_diff", fake_get_diff)

    # Set default get_new_file_contents to simple replacer
    def fake_get_new_file_contents(llm, content_to_edit, draft):
        # default behavior: return draft as new content for the test unless overridden by monkeypatch
        return draft

    monkeypatch.setattr(edit_mod, "get_new_file_contents", fake_get_new_file_contents)

    # Provide default chunk matcher
    def fake_topk(text, query, k, max_chunk_size):
        # return a couple of DummyChunk objects
        return [DummyChunk(1, 3, 0.5, vis_text="chunk1"), DummyChunk(10, 15, 0.4, vis_text="chunk2")]

    monkeypatch.setattr(edit_mod, "get_top_k_chunk_matches", fake_topk)

    yield


def make_action(path="f.txt", content="", start=-1, end=-1):
    return types.SimpleNamespace(path=path, content=content, start=start, end=end)


def call_llm_edit(rt, action, retry_num=0):
    # call the unbound method with our plain FakeRuntime instance
    return edit_mod.FileEditRuntimeMixin.llm_based_edit(rt, action, retry_num)


def test_create_file_when_not_found_success(monkeypatch):
    rt = FakeRuntime()
    # read returns ErrorObservation with 'File not found' message
    rt.next_read_obs = TestErrorObs("File not found: something")
    # write returns FileWriteObservation -> success
    rt.next_write_obs = TestFileWriteObs(path="f.txt", content="new\ncontent")
    action = make_action(path="f.txt", content="new\ncontent", start=-1, end=-1)

    res = call_llm_edit(rt, action)

    # returned should be a FileEditObservation-like object
    assert isinstance(res, TestFileEditObs)
    assert res.prev_exist is False
    assert res.old_content == ""
    assert res.new_content == action.content
    assert "DIFF" in res.content


def test_create_file_when_not_found_write_error(monkeypatch):
    rt = FakeRuntime()
    rt.next_read_obs = TestErrorObs("file not found (case insensitive)")
    # write returns an ErrorObservation -> should be returned directly
    rt.next_write_obs = TestErrorObs("disk full")
    action = make_action(path="g.txt", content="hello", start=-1, end=-1)

    res = call_llm_edit(rt, action)
    assert isinstance(res, TestErrorObs)
    assert res.content == "disk full"


def test_read_returns_unexpected_type_raises(monkeypatch):
    rt = FakeRuntime()
    # read returns a FileWriteObservation (i.e., wrong type for read)
    rt.next_read_obs = TestFileWriteObs(path="x", content="x")
    action = make_action(path="x", content="irrelevant", start=-1, end=-1)
    with pytest.raises(ValueError):
        call_llm_edit(rt, action)


def test_append_with_auto_lint_none_writes_and_returns_edit(monkeypatch):
    rt = FakeRuntime()
    original = "line1\nline2"
    rt.next_read_obs = TestFileReadObs(original)
    # enable auto lint True by default in FakeRuntime.config.sandbox
    rt.next_lint_error = None
    # set write to succeed
    rt.next_write_obs = TestFileWriteObs(path="f.txt", content="line1\nline2\nNEW")
    action = make_action(path="f.txt", content="NEW", start=-1, end=-1)

    res = call_llm_edit(rt, action)

    assert isinstance(res, TestFileEditObs)
    assert res.prev_exist is True
    assert res.old_content == original
    assert res.new_content.endswith("NEW")
    # ensure that the runtime recorded the written content
    assert rt.last_written == res.new_content


def test_append_with_auto_lint_error_triggers_correct_edit(monkeypatch):
    rt = FakeRuntime()
    original = "a\nb"
    rt.next_read_obs = TestFileReadObs(original)
    # lint returns an error observation
    rt.next_lint_error = TestErrorObs("lint failed")
    # write should be called with updated content (we simulate success)
    rt.next_write_obs = TestFileWriteObs(path="f.txt", content="a\nb\nC")
    # correct_edit should be returned by llm_based_edit
    sentinel = TestFileEditObs(content="CORRECTED", path="f.txt", prev_exist=True, old_content=original, new_content="a\nb\nC")
    rt.correct_edit_return = sentinel
    action = make_action(path="f.txt", content="C", start=-1, end=-1)

    res = call_llm_edit(rt, action)
    assert res is sentinel


def test_range_validation_error_returned(monkeypatch):
    rt = FakeRuntime()
    original = "x\ny\nz"
    rt.next_read_obs = TestFileReadObs(original)
    # make _validate_range return an ErrorObservation
    rt.validate_return = TestErrorObs("invalid range")
    action = make_action(path="f.txt", content="something", start=10, end=20)
    res = call_llm_edit(rt, action)
    assert isinstance(res, TestErrorObs)
    assert res.content == "invalid range"


def test_too_long_range_returns_error_with_chunks(monkeypatch):
    rt = FakeRuntime()
    # generate original content with many lines
    many = "\n".join(f"line{i}" for i in range(1, 401))
    rt.next_read_obs = TestFileReadObs(many)
    # choose a range exceeding MAX_LINES_TO_EDIT
    action = make_action(path="big.txt", content="some edit", start=1, end=350)
    res = call_llm_edit(rt, action)
    assert isinstance(res, TestErrorObs)
    # ensure hinting text is in error message
    assert "Consider using `open_file`" in res.content
    # chunk snippets should be present from fake_topk
    assert "chunk1" in res.content or "chunk2" in res.content


def test_get_new_file_contents_none_sets_llm_metrics(monkeypatch):
    rt = FakeRuntime()
    original = "one\ntwo\nthree"
    rt.next_read_obs = TestFileReadObs(original)
    # monkeypatch module get_new_file_contents to return None
    monkeypatch.setattr(edit_mod, "get_new_file_contents", lambda llm, a, b: None)
    # set draft editor metrics
    rt.draft_editor_llm = DummyLLM(metrics={"editor_calls": 42})
    action = make_action(path="m.txt", content="replace middle", start=2, end=2)
    res = call_llm_edit(rt, action)
    assert isinstance(res, TestErrorObs)
    # ensure llm_metrics set on returned error
    assert res.llm_metrics == {"editor_calls": 42}


def test_middle_edit_with_lint_error_calls_correct_edit_and_sets_metrics(monkeypatch):
    rt = FakeRuntime()
    original = "A\nB\nC\nD"
    rt.next_read_obs = TestFileReadObs(original)
    # new content produced by editor
    monkeypatch.setattr(edit_mod, "get_new_file_contents", lambda llm, a, b: "A\nX\nC\nD")
    # lint error is returned
    lint_err = TestErrorObs("lint fail")
    rt.next_lint_error = lint_err
    # ensure correct_edit returns sentinel
    sentinel = TestFileEditObs(content="CORR", path="m", prev_exist=True, old_content=original, new_content="A\nX\nC\nD")
    rt.correct_edit_return = sentinel
    rt.draft_editor_llm = DummyLLM(metrics={"calls": 7})
    action = make_action(path="m", content="make B->X", start=2, end=2)
    res = call_llm_edit(rt, action)
    # expect correct_edit_return to be forwarded
    assert res is sentinel
    # lint error should have had llm_metrics attached before being passed to correct_edit
    assert lint_err.llm_metrics == {"calls": 7}
