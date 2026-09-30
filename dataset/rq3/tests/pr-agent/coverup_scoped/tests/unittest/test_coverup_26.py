# file: pr_agent/git_providers/github_provider.py:646-678
# asked: {"lines": [647, 648, 649, 651, 652, 653, 655, 656, 657, 658, 659, 660, 661, 662, 663, 664, 666, 667, 669, 670, 671, 672, 673, 675, 676, 677, 678], "branches": [[651, 652], [651, 675], [656, 657], [656, 671], [660, 661], [660, 662], [662, 663], [662, 664], [664, 656], [664, 666], [671, 651], [671, 672]]}
# gained: {"lines": [647, 648, 649, 651, 652, 653, 655, 656, 657, 658, 659, 660, 661, 662, 663, 664, 666, 667, 669, 670, 671, 672, 673, 675, 676, 677, 678], "branches": [[651, 652], [651, 675], [656, 657], [656, 671], [660, 661], [660, 662], [662, 663], [664, 656], [664, 666], [671, 651], [671, 672]]}

import pytest
from types import SimpleNamespace

from pr_agent.git_providers.github_provider import GithubProvider

def make_mock_requester(calls_recorder, existing_comments=None, raise_on_get=False):
    class MockRequester:
        def requestJsonAndCheck(self, method, url, input=None):
            calls_recorder.setdefault('calls', []).append({'method': method, 'url': url, 'input': input})
            if method == 'GET':
                if raise_on_get:
                    raise Exception("Simulated GET failure")
                return None, (existing_comments or [])
            elif method == 'PATCH':
                calls_recorder['patch'] = {'url': url, 'input': input}
                return None, {'patched': True}
            elif method == 'POST':
                calls_recorder['post'] = {'url': url, 'input': input}
                return None, {'posted': True}
            else:
                raise ValueError("Unexpected method")
    return MockRequester()

class DummySettings:
    def __init__(self, mapping=None):
        self._map = mapping or {}
        # Provide attributes expected by _get_github_client
        self.github = SimpleNamespace(user_token="dummy-token", private_key="dummy-key", app_id="42")
    def get(self, key, default=None):
        return self._map.get(key, default)

def setup_provider_for_tests(monkeypatch):
    # Prepare dummy settings before instantiating GithubProvider to avoid init-time errors
    dummy = DummySettings({
        "GITHUB.DEPLOYMENT_TYPE": "user",
        "GITHUB.APP_NAME": "OurAppName",
        "GITHUB.BASE_URL": "https://api.github.com"
    })
    monkeypatch.setattr("pr_agent.git_providers.github_provider.get_settings", lambda: dummy)
    provider = GithubProvider()  # now safe: get_settings is patched
    # Make sure other attributes used by publish_file_comments exist
    provider.limit_output_characters = lambda body, max_chars: body
    provider.max_comment_chars = 65000
    provider.base_url = "https://api.github.com"
    provider.repo = "owner/repo"
    provider.last_commit_id = SimpleNamespace(sha="deadbeef")
    return provider

def test_publish_file_comments_app_patch_and_post(monkeypatch):
    calls = {}
    existing_comments = [
        {
            'id': 111,
            'subject_type': 'file',
            'path': 'a/b/file1.py',
            'user': {'login': 'ourappname-bot'}
        }
    ]
    mock_requester = make_mock_requester(calls, existing_comments=existing_comments)
    provider = setup_provider_for_tests(monkeypatch)
    provider.pr = SimpleNamespace(url="https://api.github.com/repos/owner/repo/pulls/1", _requester=mock_requester)
    # Force deployment_type to 'app' for this test to exercise that branch
    provider.deployment_type = 'app'
    provider.github_user_id = None

    file_comments = [
        {'path': 'a/b/file1.py', 'body': 'update this line', 'position': 10},
        {'path': 'a/b/new_file2.py', 'body': 'add new comment', 'position': 5},
    ]

    result = provider.publish_file_comments(file_comments)
    assert result is True

    methods = [c['method'] for c in calls.get('calls', [])]
    assert 'GET' in methods
    assert 'PATCH' in methods
    assert 'POST' in methods

    assert str(calls['patch']['url']).endswith("/repos/owner/repo/pulls/comments/111")
    assert calls['patch']['input'] == {"body": 'update this line'}

    assert calls['post']['input']['path'] == 'a/b/new_file2.py'
    assert calls['post']['input']['body'] == 'add new comment'
    assert calls['post']['input']['commit_id'] == provider.last_commit_id.sha

def test_publish_file_comments_user_deployment_patch(monkeypatch):
    calls = {}
    existing_comments = [
        {
            'id': 222,
            'subject_type': 'file',
            'path': 'src/module.py',
            'user': {'login': 'some-username'}
        }
    ]
    mock_requester = make_mock_requester(calls, existing_comments=existing_comments)
    provider = setup_provider_for_tests(monkeypatch)
    provider.pr = SimpleNamespace(url="https://api.github.com/repos/owner/repo/pulls/2", _requester=mock_requester)
    provider.deployment_type = 'user'
    provider.github_user_id = 'some-username'

    file_comments = [
        {'path': 'src/module.py', 'body': 'please change', 'position': 3}
    ]

    result = provider.publish_file_comments(file_comments)
    assert result is True
    assert 'patch' in calls
    assert calls['patch']['input'] == {"body": 'please change'}
    assert calls['patch']['url'].endswith("/repos/owner/repo/pulls/comments/222")

def test_publish_file_comments_get_raises_logs_and_returns_false(monkeypatch):
    calls = {}
    mock_requester = make_mock_requester(calls, existing_comments=None, raise_on_get=True)
    provider = setup_provider_for_tests(monkeypatch)
    provider.pr = SimpleNamespace(url="https://api.github.com/repos/owner/repo/pulls/3", _requester=mock_requester)
    provider.deployment_type = 'app'
    provider.github_user_id = None

    logged = {}
    class DummyLogger:
        def error(self, msg):
            logged['msg'] = msg

    monkeypatch.setattr("pr_agent.git_providers.github_provider.get_logger", lambda: DummyLogger())

    result = provider.publish_file_comments([{'path': 'x', 'body': 'y'}])
    assert result is False
    assert 'Failed to publish diffview file summary' in logged.get('msg', '')
