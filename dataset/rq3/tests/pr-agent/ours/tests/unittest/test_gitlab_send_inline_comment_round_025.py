import pytest
from types import SimpleNamespace
from pr_agent.git_providers.gitlab_provider import GitLabProvider, DiffNotFoundError


def make_provider_stub():
    # Create instance without running __init__ to avoid external setup
    p = object.__new__(GitLabProvider)
    # minimal attributes that will be set per-test
    return p


def test_send_inline_comment_diff_none_round_025():
    """
    If get_relevant_diff returns None, send_inline_comment should raise DiffNotFoundError.
    Covers lines where diff is None and the DiffNotFoundError is raised.
    """
    provider = make_provider_stub()
    provider.id_mr = 42

    # Simulate not being able to find a diff
    provider.get_relevant_diff = lambda relevant_file, relevant_line_in_file: None

    target_file = SimpleNamespace(filename="file.py", old_filename=None)

    with pytest.raises(DiffNotFoundError):
        provider.send_inline_comment(
            body="body",
            edit_type="modification",
            found=True,
            relevant_file="some.py",
            relevant_line_in_file="10",
            source_line_no=5,
            target_file=target_file,
            target_line_no=7,
            original_suggestion=None,
        )


def test_send_inline_comment_fallback_suggestion_with_location_round_025():
    """
    Tests the fallback branch when discussions.create raises and original_suggestion contains
    'suggestion_orig_location'. Ensures notes.create is invoked with a body containing the
    suggestion summary and a diff code block, and that position contains the diff SHAs.
    This exercises the branch where 'score' is present and main_language exists.
    """
    provider = make_provider_stub()
    provider.id_mr = 99

    # Provide a diff-like object with commit SHAs
    diff = SimpleNamespace(base_commit_sha="base123", start_commit_sha="start123", head_commit_sha="head123")
    provider.get_relevant_diff = lambda relevant_file, relevant_line_in_file: diff

    # discussions.create will fail to trigger fallback
    def raise_on_create(_):
        raise Exception("simulated discussions.create failure")

    notes_payload = {}

    def notes_create(payload):
        # store payload for assertions
        notes_payload['payload'] = payload

    provider.mr = SimpleNamespace(discussions=SimpleNamespace(create=raise_on_create), notes=SimpleNamespace(create=notes_create))

    # Ensure get_line_link is deterministic
    provider.get_line_link = lambda relevant_file, start, end: f"http://gitlab/f/{relevant_file}#{start}-{end}"

    # target file with old filename present
    target_file = SimpleNamespace(filename="target.py", old_filename="old_target.py")

    # Provide fairly long snippets so difflib produces enough header/context lines
    old_code = "\n".join([f"old line {i}" for i in range(10)])
    new_code = "\n".join([f"new line {i}" for i in range(12)])

    original_suggestion = {
        'suggestion_orig_location': {'start_line': 2, 'end_line': 4},
        'prev_code_snippet': old_code,
        'new_code_snippet': new_code,
        'suggestion_summary': 'Please improve this part',
        'category': 'style',
        'score': 9,
    }

    # main_language present to exercise language branch
    provider.main_language = 'python'

    # Call with an edit_type that goes through the 'addition' branch
    provider.send_inline_comment(
        body="ignored body",
        edit_type="addition",
        found=True,
        relevant_file="some.py",
        relevant_line_in_file="2",
        source_line_no=3,
        target_file=target_file,
        target_line_no=8,
        original_suggestion=original_suggestion,
    )

    assert 'payload' in notes_payload, "notes.create was not invoked in fallback"
    payload = notes_payload['payload']

    # Position should include the SHAs from our diff object
    assert payload['position']['base_sha'] == diff.base_commit_sha
    assert payload['position']['start_sha'] == diff.start_commit_sha
    assert payload['position']['head_sha'] == diff.head_commit_sha
    assert payload['position']['file_path'] == target_file.filename

    # Body should include suggestion summary, category/score and a diff block
    body = payload['body']
    assert 'Please improve this part' in body
    assert '[style, importance: 9]' in body
    assert '```diff' in body and '```' in body


def test_send_inline_comment_fallback_without_location_and_no_score_round_025():
    """
    Tests the fallback branch when the original_suggestion does NOT include
    'suggestion_orig_location' and does not include 'score', and the provider
    lacks main_language. Verifies default score (7) and that language falls back to ''.
    """
    provider = make_provider_stub()
    provider.id_mr = 100

    diff = SimpleNamespace(base_commit_sha="b2", start_commit_sha="s2", head_commit_sha="h2")
    provider.get_relevant_diff = lambda relevant_file, relevant_line_in_file: diff

    def raise_on_create(_):
        raise Exception("simulated discussions.create failure")

    notes_payload = {}

    def notes_create(payload):
        notes_payload['payload'] = payload

    provider.mr = SimpleNamespace(discussions=SimpleNamespace(create=raise_on_create), notes=SimpleNamespace(create=notes_create))

    provider.get_line_link = lambda relevant_file, start, end: "http://example/link"

    target_file = SimpleNamespace(filename="another.py", old_filename=None)

    old_code = "\n".join([f"line old {i}" for i in range(8)])
    new_code = "\n".join([f"line new {i}" for i in range(9)])

    original_suggestion = {
        # no 'suggestion_orig_location' -> should go to the other fallback branch
        'relevant_lines_start': 1,
        'relevant_lines_end': 3,
        'existing_code': old_code,
        'improved_code': new_code,
        'suggestion_content': 'Refactor this block',
        'label': 'refactor',
        # intentionally no 'score' to hit default
    }

    # Ensure provider has no main_language attribute to hit language = '' branch
    if hasattr(provider, 'main_language'):
        delattr(provider, 'main_language')

    provider.send_inline_comment(
        body="unused",
        edit_type="modification",
        found=True,
        relevant_file="fileX.py",
        relevant_line_in_file="1",
        source_line_no=5,
        target_file=target_file,
        target_line_no=6,
        original_suggestion=original_suggestion,
    )

    assert 'payload' in notes_payload, "notes.create was not invoked for non-location suggestion"
    payload = notes_payload['payload']
    body = payload['body']

    # Should contain suggestion_content and default importance 7
    assert 'Refactor this block' in body
    assert '[refactor, importance: 7]' in body
    assert payload['position']['base_sha'] == diff.base_commit_sha
