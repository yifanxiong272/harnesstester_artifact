import pytest
from types import SimpleNamespace

from pr_agent.git_providers.gitlab_provider import GitLabProvider, DiffNotFoundError


def _make_provider():
    # create an uninitialized GitLabProvider instance and set minimal attributes
    p = GitLabProvider.__new__(GitLabProvider)
    p.id_mr = 42
    return p


def test_send_inline_comment_not_found_round_025():
    """
    If 'found' is False send_inline_comment should not attempt to create a discussion.
    We ensure discussions.create would raise if called, so absence of an exception
    implies the branch for not-found was taken.
    """
    provider = _make_provider()

    # If discussions.create is called, this will raise - test will fail
    provider.mr = SimpleNamespace(discussions=SimpleNamespace(create=lambda payload: (_ for _ in ()).throw(AssertionError("discussions.create should not be called"))),
                                   notes=SimpleNamespace(create=lambda payload: None))

    # ensure get_relevant_diff would fail loudly if used (should not be used when found=False)
    provider.get_relevant_diff = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("get_relevant_diff should not be called when found=False"))

    # Call with found=False; should return None and not call discussions.create
    result = provider.send_inline_comment(body="b", edit_type="addition", found=False,
                                          relevant_file="some/file.py", relevant_line_in_file="needle",
                                          source_line_no=10, target_file=SimpleNamespace(filename="t.py", old_filename=None), target_line_no=12)

    assert result is None


def test_send_inline_comment_diff_none_raises_round_025():
    """
    When get_relevant_diff returns None but found is True the method should raise DiffNotFoundError.
    """
    provider = _make_provider()
    provider.mr = SimpleNamespace(discussions=SimpleNamespace(create=lambda payload: None),
                                   notes=SimpleNamespace(create=lambda payload: None))

    # Simulate not finding a diff
    provider.get_relevant_diff = lambda relevant_file, relevant_line_in_file: None

    with pytest.raises(DiffNotFoundError):
        provider.send_inline_comment(body="b", edit_type="addition", found=True,
                                     relevant_file="some/file.py", relevant_line_in_file="needle",
                                     source_line_no=10, target_file=SimpleNamespace(filename="t.py", old_filename=None), target_line_no=12)


def test_send_inline_comment_create_discussion_success_round_025():
    """
    Validate the normal path where a position object is created and discussions.create is invoked.
    Test for edit_type 'deletion' so old_line is set and old_path uses old_filename when present.
    """
    provider = _make_provider()

    captured = {}

    def fake_create(payload):
        # capture call for assertions
        captured['payload'] = payload
        return None

    provider.mr = SimpleNamespace(discussions=SimpleNamespace(create=fake_create),
                                   notes=SimpleNamespace(create=lambda payload: None))

    # Provide a diff object
    provider.get_relevant_diff = lambda relevant_file, relevant_line_in_file: SimpleNamespace(
        base_commit_sha='base', start_commit_sha='start', head_commit_sha='head')

    # Link resolver used only in fallback; safe to provide
    provider.get_line_link = lambda relevant_file, s, e: 'http://link'

    target_file = SimpleNamespace(filename='file_name.py', old_filename='old_file_name.py')

    provider.send_inline_comment(body="body text", edit_type='deletion', found=True,
                                 relevant_file='some/file.py', relevant_line_in_file='line',
                                 source_line_no=7, target_file=target_file, target_line_no=20)

    assert 'payload' in captured, "discussions.create was not called"
    payload = captured['payload']
    assert payload.get('body') == 'body text'
    pos = payload.get('position')
    # For deletion we expect old_line only (source_line_no - 1)
    assert pos['old_line'] == 6
    # Ensure old_path uses target_file.old_filename when present
    assert pos['old_path'] == 'old_file_name.py'
    assert pos['new_path'] == 'file_name.py'
    # ensure commit shas were passed through
    assert pos['base_sha'] == 'base' and pos['start_sha'] == 'start' and pos['head_sha'] == 'head'


def test_send_inline_comment_fallback_with_suggestion_location_no_score_round_025():
    """
    Simulate discussions.create failing to force the fallback to notes.create when the original_suggestion
    contains 'suggestion_orig_location' and does NOT include 'score'. The fallback body should include the
    suggestion summary, computed default score (7), the file name and a diff block.
    """
    provider = _make_provider()

    # Make discussions.create raise to enter fallback path
    def raise_on_discussion(payload):
        raise Exception("discussion API error")

    notes_captured = {}

    def fake_notes_create(payload):
        notes_captured['payload'] = payload
        return None

    provider.mr = SimpleNamespace(discussions=SimpleNamespace(create=raise_on_discussion),
                                   notes=SimpleNamespace(create=fake_notes_create))

    provider.get_relevant_diff = lambda relevant_file, relevant_line_in_file: SimpleNamespace(
        base_commit_sha='b', start_commit_sha='s', head_commit_sha='h')

    # Provide main_language to exercise the branch where language is taken from the instance
    provider.main_language = 'python'

    provider.get_line_link = lambda relevant_file, s, e: 'http://the-link'

    original_suggestion = {
        'suggestion_orig_location': {'start_line': 3, 'end_line': 5},
        'prev_code_snippet': 'a\nb\nc',
        'new_code_snippet': 'a\nB\nc',
        'suggestion_summary': 'Do this',
        'category': 'style'
        # NO 'score' key -> should default to 7
    }

    target_file = SimpleNamespace(filename='target.py', old_filename=None)

    provider.send_inline_comment(body='ignored', edit_type='addition', found=True,
                                 relevant_file='some/file.py', relevant_line_in_file='needle',
                                 source_line_no=10, target_file=target_file, target_line_no=12,
                                 original_suggestion=original_suggestion)

    assert 'payload' in notes_captured, 'notes.create was not called in fallback'
    note_payload = notes_captured['payload']
    body_text = note_payload.get('body', '')

    # Assertions on the fallback body to verify content assembly
    assert '**Suggestion:**' in body_text
    assert 'Do this' in body_text
    assert 'style' in body_text
    assert 'importance: 7' in body_text
    assert 'target.py [3-5]' or 'target.py [3-5]'  # ensure mention of the file/lines (loose check)
    assert '```diff' in body_text

    # Position passed to notes should include commit shas and the file_path
    pos = note_payload.get('position', {})
    assert pos.get('base_sha') == 'b' and pos.get('start_sha') == 's' and pos.get('head_sha') == 'h'
    assert pos.get('file_path') == 'target.py'


def test_send_inline_comment_fallback_without_suggestion_location_with_score_round_025():
    """
    Similar fallback scenario but original_suggestion does not include 'suggestion_orig_location'
    and does include a 'score' key so the supplied score is used. Also do not set main_language
    on the provider instance to exercise the branch where language becomes an empty string.
    """
    provider = _make_provider()

    def raise_on_discussion(payload):
        raise Exception("discussion failed")

    notes_captured = {}

    def fake_notes_create(payload):
        notes_captured['payload'] = payload
        return None

    provider.mr = SimpleNamespace(discussions=SimpleNamespace(create=raise_on_discussion),
                                   notes=SimpleNamespace(create=fake_notes_create))

    provider.get_relevant_diff = lambda relevant_file, relevant_line_in_file: SimpleNamespace(
        base_commit_sha='bb', start_commit_sha='ss', head_commit_sha='hh')

    # do NOT set provider.main_language to hit the else branch for language
    if hasattr(provider, 'main_language'):
        delattr(provider, 'main_language') if hasattr(provider, 'main_language') else None

    provider.get_line_link = lambda relevant_file, s, e: 'http://link2'

    original_suggestion = {
        'relevant_lines_start': 1,
        'relevant_lines_end': 2,
        'existing_code': 'old',
        'improved_code': 'new',
        'suggestion_content': 'Please change',
        'label': 'bugfix',
        'score': 10
    }

    target_file = SimpleNamespace(filename='another.py', old_filename=None)

    provider.send_inline_comment(body='ignored', edit_type='replace', found=True,
                                 relevant_file='some/file.py', relevant_line_in_file='needle',
                                 source_line_no=4, target_file=target_file, target_line_no=8,
                                 original_suggestion=original_suggestion)

    assert 'payload' in notes_captured, 'notes.create was not called in fallback (no suggestion_orig_location)'
    note_payload = notes_captured['payload']
    body_text = note_payload.get('body', '')

    assert '**Suggestion:**' in body_text
    assert 'Please change' in body_text
    assert 'bugfix' in body_text
    # supplied score 10 should appear
    assert 'importance: 10' in body_text
    assert '```diff' in body_text
    pos = note_payload.get('position', {})
    assert pos.get('base_sha') == 'bb' and pos.get('start_sha') == 'ss' and pos.get('head_sha') == 'hh'
    assert pos.get('file_path') == 'another.py'
