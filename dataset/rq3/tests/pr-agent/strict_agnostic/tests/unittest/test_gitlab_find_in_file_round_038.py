import re
from pr_agent.git_providers.gitlab_provider import GitLabProvider


class DummyFile:
    def __init__(self, patch):
        self.patch = patch

    def __repr__(self):
        return f"<DummyFile patch={self.patch!r}>"


def _make_provider():
    # Create instance without calling __init__ to avoid external side effects
    p = object.__new__(GitLabProvider)
    # Accept common hunk header formats like: @@ -10,1 +20,1 @@ optional
    p.RE_HUNK_HEADER = re.compile(r"^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@(.*)")
    return p


def test_find_in_file_context_round_038():
    """
    Case: well-formed hunk header followed by a context line that contains the
    relevant text. Expect the provider to match the header, increment the
    source/target counters for the context line, mark found True and return
    the edit type provided by injected get_edit_type.
    """
    provider = _make_provider()

    # get_edit_type should be invoked with the matched line; return a sentinel
    provider.get_edit_type = lambda line: "CTX"

    # Header sets start_old=10, start_new=20. A single context line follows.
    patch = "@@ -10,1 +20,1 @@\n context foo\n"
    f = DummyFile(patch)

    edit_type, found, source_line_no, target_file, target_line_no = (
        provider.find_in_file(f, "context foo")
    )

    # Assertions deterministic and observable
    assert edit_type == "CTX"
    assert found is True
    # start_old was 10 and a context line increments source_line_no by 1
    assert source_line_no == 11
    # target_file is the same object we passed
    assert target_file is f
    # start_new was 20 and a context line increments target_line_no by 1
    assert target_line_no == 21


def test_find_in_file_plus_prefixed_relevant_round_038():
    """
    Case: the provided relevant_line_in_file begins with '+' (model artifact)
    but the patch contains the original context line (leading space). The
    code's special branch should detect this scenario and mark found True and
    call get_edit_type.
    """
    provider = _make_provider()
    provider.get_edit_type = lambda line: "SPECIAL"

    # Header sets start_old=1, start_new=5. The context line (leading space)
    # contains the relevant text without the '+' prefix.
    patch = "@@ -1,1 +5,1 @@\n added line\n"
    f = DummyFile(patch)

    edit_type, found, source_line_no, target_file, target_line_no = (
        provider.find_in_file(f, "+added line")
    )

    assert edit_type == "SPECIAL"
    assert found is True
    # start_old 1 -> incremented by context line -> 2
    assert source_line_no == 2
    assert target_file is f
    # start_new 5 -> incremented by context line -> 6
    assert target_line_no == 6


def test_find_in_file_no_match_and_line_counters_round_038():
    """
    Case: header-looking line that does NOT match the provider's RE_HUNK_HEADER
    (exercises the `if not match: continue` branch) and subsequent '-' and
    '+' and ' ' lines. No relevant line present -> found should be False and
    returned edit_type should remain default 'context'. Also verifies the
    source/target counters updated from zero when no header matched.
    """
    provider = _make_provider()
    # This test doesn't expect get_edit_type to be called; provide a function
    # that would fail loudly if called unexpectedly.
    provider.get_edit_type = lambda line: (_ for _ in ()).throw(AssertionError("get_edit_type should not be called"))

    # First line starts with @@ but does not match the RE_HUNK_HEADER -> continue
    # Then we have a removed line, an added line, and a context line. None contain
    # the searched text.
    patch = "@@ invalid header @@\n-removed line\n+added line\n context none\n"
    f = DummyFile(patch)

    edit_type, found, source_line_no, target_file, target_line_no = (
        provider.find_in_file(f, "something not present")
    )

    # No match was found anywhere in the patch
    assert found is False
    # Default edit_type is 'context' as set at start of the method
    assert edit_type == "context"
    # We started counters at 0; '-' -> source_line_no+=1 (1), '+' -> target_line_no+=1 (1),
    # ' ' -> both +=1 -> final source_line_no,target_line_no == 2
    assert source_line_no == 2
    assert target_line_no == 2
    assert target_file is f
