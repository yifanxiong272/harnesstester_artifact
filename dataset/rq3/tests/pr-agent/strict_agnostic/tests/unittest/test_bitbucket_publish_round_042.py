import types
import pytest
from pr_agent.git_providers.bitbucket_provider import BitbucketProvider


def test_publish_code_suggestions_with_diff_and_multi_line_round_042():
    """When an original_suggestion is provided and relevant_lines_end > relevant_lines_start,
    the method should build a multi-line post_parameters entry containing a diff in the body
    and call publish_inline_comments with the constructed list. The method should return True
    when publish_inline_comments does not raise.
    """
    recorded = {}

    def publish_inline_comments(arg):
        # record the argument for assertions
        recorded['arg'] = arg

    dummy = types.SimpleNamespace(publish_inline_comments=publish_inline_comments)

    # original_suggestion with a small change to produce a diff
    original = {
        'existing_code': 'line1\nline2\nline3\n',
        'improved_code': 'line1\nCHANGED_LINE\nline3\n'
    }

    suggestion_body = 'Please change this:\n```suggestion\nold\n```'
    suggestion = {
        'body': suggestion_body,
        'original_suggestion': original,
        'relevant_file': 'some/file.py',
        'relevant_lines_start': 10,
        'relevant_lines_end': 12,
    }

    result = BitbucketProvider.publish_code_suggestions(dummy, [suggestion])

    assert result is True
    # publish_inline_comments should be called exactly once with a list containing one dict
    assert 'arg' in recorded
    posts = recorded['arg']
    assert isinstance(posts, list) and len(posts) == 1
    post = posts[0]
    # verify multi-line comment parameter keys
    assert post['path'] == 'some/file.py'
    assert post['start_line'] == 10
    assert post['line'] == 12
    # the body should include a diff fence
    assert '```diff' in post['body']


def test_publish_code_suggestions_single_line_and_publish_exception_round_042():
    """When relevant_lines_end == relevant_lines_start the API expects a single-line comment
    structure. If publish_inline_comments raises, the method should return False and not raise.
    """

    def publish_inline_comments_raises(arg):
        raise RuntimeError("publish failed")

    dummy = types.SimpleNamespace(publish_inline_comments=publish_inline_comments_raises)

    suggestion = {
        'body': 'single line suggestion',
        'relevant_file': 'file.py',
        'relevant_lines_start': 5,
        'relevant_lines_end': 5,
    }

    result = BitbucketProvider.publish_code_suggestions(dummy, [suggestion])

    assert result is False


def test_publish_code_suggestions_skips_bad_suggestions_round_042():
    """Ensure suggestions that trigger internal continue branches are skipped and do not
    contribute to the post_parameters_list. Cases covered:
      - missing/None relevant_lines_start
      - relevant_lines_end < relevant_lines_start
      - original_suggestion that raises inside diff generation
    The method should still call publish_inline_comments with an empty list and return True.
    """
    recorded = {}

    def publish_inline_comments(arg):
        recorded['arg'] = arg

    dummy = types.SimpleNamespace(publish_inline_comments=publish_inline_comments)

    # 1) missing relevant_lines_start (None) -> triggers "if not relevant_lines_start or ..." -> continue
    s1 = {
        'body': 'b1',
        'relevant_file': 'a.py',
        'relevant_lines_start': None,
        'relevant_lines_end': None,
    }

    # 2) relevant_lines_end < relevant_lines_start -> continue
    s2 = {
        'body': 'b2',
        'relevant_file': 'b.py',
        'relevant_lines_start': 10,
        'relevant_lines_end': 5,
    }

    # 3) original_suggestion that will raise when .rstrip() is called (existing_code is None)
    s3 = {
        'body': 'b3',
        'original_suggestion': {'existing_code': None, 'improved_code': 'x'},
        'relevant_file': 'c.py',
        'relevant_lines_start': 1,
        'relevant_lines_end': 2,
    }

    result = BitbucketProvider.publish_code_suggestions(dummy, [s1, s2, s3])

    assert result is True
    # publish_inline_comments should be called with an empty list because all suggestions were skipped
    assert 'arg' in recorded
    assert recorded['arg'] == []
