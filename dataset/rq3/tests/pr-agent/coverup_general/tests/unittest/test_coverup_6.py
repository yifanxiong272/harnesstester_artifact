# file: pr_agent/servers/github_action_runner.py:33-182
# asked: {"lines": [47, 48, 50, 51, 55, 60, 65, 72, 73, 74, 82, 83, 89, 91, 92, 94, 95, 96, 97, 98, 99, 101, 102, 103, 104, 106, 107, 108, 122, 125, 128, 139, 143, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 161, 162, 163, 164, 165, 166, 167, 169, 171, 172, 173, 174, 175, 176, 177, 178, 182], "branches": [[46, 47], [49, 50], [54, 55], [59, 60], [64, 65], [79, 86], [88, 89], [94, 95], [94, 110], [96, 94], [96, 97], [97, 94], [97, 98], [98, 94], [98, 99], [101, 94], [101, 102], [110, 146], [116, 143], [118, 0], [121, 122], [124, 125], [127, 128], [136, 138], [138, 139], [140, 0], [146, 0], [146, 147], [148, 0], [148, 149], [151, 152], [151, 157], [152, 153], [152, 157], [157, 0], [157, 158], [161, 162], [161, 164], [164, 165], [164, 169], [171, 0], [171, 172], [175, 176], [175, 182]]}
# gained: {"lines": [47, 48, 50, 51, 55, 60, 72, 73, 74, 89, 91, 92, 94, 95, 96, 97, 98, 99, 101, 102, 103, 104, 106, 122, 125, 128, 139, 143, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 161, 162, 163, 164, 165, 166, 167, 169, 171, 172, 173, 174, 175, 176, 177, 178, 182], "branches": [[46, 47], [49, 50], [54, 55], [59, 60], [79, 86], [88, 89], [94, 95], [94, 110], [96, 94], [96, 97], [97, 98], [98, 99], [101, 102], [110, 146], [116, 143], [121, 122], [124, 125], [127, 128], [138, 139], [146, 147], [148, 149], [151, 152], [151, 157], [152, 153], [157, 158], [161, 162], [161, 164], [164, 165], [164, 169], [171, 172], [175, 176], [175, 182]]}

import asyncio
import json
import os
import types
import pytest

import pr_agent.servers.github_action_runner as garun


# Create a fake class that mimics dynaconf.utils.boxing.DynaBox by name and module
class DynaBox:
    def __init__(self, extra_instructions=None):
        self.extra_instructions = extra_instructions


# Force the class to appear as from dynaconf.utils.boxing module so
# str(type(instance)) == "<class 'dynaconf.utils.boxing.DynaBox'>"
DynaBox.__module__ = "dynaconf.utils.boxing"


class FakeSettings:
    def __init__(self, response_language="en-us"):
        # store sets here for assertion
        self._store = {}
        # keys that will be returned when iterating
        self._keys = ["pr_description", "pr_code_suggestions", "pr_reviewer", "other"]
        # mapping for .get(key)
        self._mapping = {
            # use the fake DynaBox so the runner's type check matches
            "pr_description": DynaBox(extra_instructions="orig"),
            "pr_code_suggestions": DynaBox(extra_instructions=None),
            "pr_reviewer": DynaBox(extra_instructions=""),
            "other": "notabox",
        }
        # config object with .get and attributes used in code
        self.config = types.SimpleNamespace(
            get=lambda k, d=None: response_language if k == "response_language" else d,
            enable_custom_labels=False,
            is_auto_command=False,
        )
        # pr_description attribute expected to have final_update_message
        self.pr_description = types.SimpleNamespace(final_update_message=True)

    def __iter__(self):
        return iter(self._keys)

    def get(self, key, default=None):
        return self._mapping.get(key, default)

    def set(self, key, value):
        self._store[key] = value


@pytest.mark.asyncio
async def test_missing_event_name(monkeypatch, capsys):
    # No GITHUB_EVENT_NAME set should cause early return with printed message
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    # ensure other envs are not required for this branch
    await garun.run_action()
    captured = capsys.readouterr()
    assert "GITHUB_EVENT_NAME not set" in captured.out


@pytest.mark.asyncio
async def test_missing_event_path_and_token(monkeypatch, tmp_path, capsys):
    # If GITHUB_EVENT_NAME set but GITHUB_EVENT_PATH missing -> early return
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
    await garun.run_action()
    out = capsys.readouterr().out
    assert "GITHUB_EVENT_PATH not set" in out

    # Now create a file (valid JSON) but no token to trigger GITHUB_TOKEN not set
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps({"action": "opened"}))
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_file))
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    await garun.run_action()
    out = capsys.readouterr().out
    assert "GITHUB_TOKEN not set" in out


@pytest.mark.asyncio
async def test_json_decode_error_and_openai_settings(monkeypatch, tmp_path, capsys):
    # Provide envs but invalid JSON to trigger JSONDecodeError branch
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{ notvalid json }")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(bad_file))
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    # Ensure OPENAI_KEY not set branch is triggered
    monkeypatch.delenv("OPENAI_KEY", raising=False)
    monkeypatch.delenv("OPENAI_ORG", raising=False)

    await garun.run_action()
    out = capsys.readouterr().out
    assert "Failed to parse JSON" in out or "OPENAI_KEY not set" in out


@pytest.mark.asyncio
async def test_apply_repo_settings_language_and_auto_actions(monkeypatch, tmp_path):
    # Set up a valid pull_request event with html_url and url to exercise apply_repo_settings
    payload = {
        "action": "opened",
        "pull_request": {"html_url": "https://example.com/pr/1", "url": "https://api.example.com/pr/1"},
    }
    event_file = tmp_path / "event2.json"
    event_file.write_text(json.dumps(payload))

    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_file))
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    # set OPENAI values to hit set branches
    monkeypatch.setenv("OPENAI_KEY", "openai-key")
    monkeypatch.setenv("OPENAI_ORG", "openai-org")

    fake_settings = FakeSettings(response_language="fr-FR")
    monkeypatch.setattr(garun, "get_settings", lambda: fake_settings)

    # patch apply_repo_settings to set enable_custom_labels and ensure it's called
    called = {"applied": False}

    def fake_apply_repo_settings(url):
        called["applied"] = True
        # simulate toggling the setting
        fake_settings.config.enable_custom_labels = True

    monkeypatch.setattr(garun, "apply_repo_settings", fake_apply_repo_settings)

    # For get_setting_or_env return None so auto actions run and ENABLE_OUTPUT becomes None
    monkeypatch.setattr(garun, "get_setting_or_env", lambda k, d=None: None)

    # Patch is_true so None leads to running tools
    monkeypatch.setattr(garun, "is_true", lambda v: False)

    # Patch tool runs to record invocation
    ran = {"desc": False, "rev": False, "code": False}

    class DummyTool:
        def __init__(self, url):
            self.url = url

        async def run(self):
            # set flags based on class identity
            if isinstance(self, PRDescStub):
                ran["desc"] = True
            elif isinstance(self, PRRevStub):
                ran["rev"] = True
            elif isinstance(self, PRCodeStub):
                ran["code"] = True

    class PRDescStub(DummyTool):
        pass

    class PRRevStub(DummyTool):
        pass

    class PRCodeStub(DummyTool):
        pass

    monkeypatch.setattr(garun, "PRDescription", PRDescStub)
    monkeypatch.setattr(garun, "PRReviewer", PRRevStub)
    monkeypatch.setattr(garun, "PRCodeSuggestions", PRCodeStub)

    # Run action
    await garun.run_action()

    # Assertions
    assert called["applied"] is True
    # When get_setting_or_env returns None, ENABLE_OUTPUT stored should be None
    assert fake_settings._store.get("GITHUB_ACTION_CONFIG.ENABLE_OUTPUT") is None
    # Ensure language-specific text was added to extra_instructions for pr_description etc.
    assert "locale code" in str(fake_settings.get("pr_description").extra_instructions)
    # Ensure auto flags triggered runs
    assert ran["desc"] is True and ran["rev"] is True and ran["code"] is True
    # Ensure is_auto_command and final_update_message updated
    assert fake_settings.config.is_auto_command is True
    assert fake_settings.pr_description.final_update_message is False


@pytest.mark.asyncio
async def test_skip_action_and_issue_comment_branches(monkeypatch, tmp_path):
    # Test skip action: action not in pr_actions
    payload_skip = {"action": "somenonlisted", "pull_request": {"html_url": None, "url": None}}
    event_file = tmp_path / "event_skip.json"
    event_file.write_text(json.dumps(payload_skip))

    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_file))
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    fake_settings = FakeSettings()
    monkeypatch.setattr(garun, "get_settings", lambda: fake_settings)
    logs = {"info": []}
    monkeypatch.setattr(garun, "get_logger", lambda: types.SimpleNamespace(info=lambda m: logs["info"].append(m), error=lambda m: logs.setdefault("error", []).append(m)))

    await garun.run_action()
    assert any("Skipping action" in s for s in logs["info"])

    # Now test 'issue_comment' where issue contains pull_request (is_pr True) and provider.add_eyes_reaction is used
    payload_comment_pr = {
        "action": "created",
        "comment": {"body": " please do something ", "id": 999},
        "issue": {"pull_request": {"url": "https://api.example.com/pr/1"}, "url": "https://api.example.com/issue/1"},
    }
    event_file2 = tmp_path / "event_comment_pr.json"
    event_file2.write_text(json.dumps(payload_comment_pr))
    monkeypatch.setenv("GITHUB_EVENT_NAME", "issue_comment")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_file2))

    # stub provider factory to return object with add_eyes_reaction
    added = {"called": False, "args": None}

    class Provider:
        def __init__(self, pr_url=None):
            self.pr_url = pr_url

        def add_eyes_reaction(self, comment_id, disable_eyes=False):
            added["called"] = True
            added["args"] = (comment_id, disable_eyes)
            return "ok"

    monkeypatch.setattr(garun, "get_git_provider", lambda: (lambda pr_url=None: Provider(pr_url=pr_url)))

    # stub PRAgent.handle_request to ensure notify is called
    called_agent = {"handled": False, "args": None}

    class FakePRAgent:
        async def handle_request(self, url, body, notify=None):
            called_agent["handled"] = True
            called_agent["args"] = (url, body, notify)
            # call notify to exercise provider.add_eyes_reaction path
            if notify:
                notify()

    monkeypatch.setattr(garun, "PRAgent", lambda: FakePRAgent())

    await garun.run_action()
    assert added["called"] is True
    assert added["args"][0] == 999
    # disable_eyes should be False for issue.pull_request path
    assert added["args"][1] is False
    assert called_agent["handled"] is True

    # Now test pull_request_review_comment where handle_line_comments raises -> triggers error and return
    payload_review = {
        "action": "created",
        "comment": {"body": "/ask something", "id": 5},
        "issue": {"url": "https://api.example.com/issue/2"},
    }
    event_file3 = tmp_path / "event_review.json"
    event_file3.write_text(json.dumps(payload_review))
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request_review_comment")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_file3))

    # make handle_line_comments raise
    def raise_handle_line_comments(event_payload, comment_body):
        raise RuntimeError("boom")

    monkeypatch.setattr(garun, "handle_line_comments", raise_handle_line_comments)
    # capture logger.error
    errors = []

    monkeypatch.setattr(garun, "get_logger", lambda: types.SimpleNamespace(info=lambda m: None, error=lambda m: errors.append(m)))
    await garun.run_action()
    assert any("Failed to handle line comments" in e for e in errors)

    # Finally test comment with comment.pull_request_url present path (disable_eyes True)
    payload_comment_pr_url = {
        "action": "edited",
        "comment": {"body": "somebody", "id": 321, "pull_request_url": "https://api.example.com/pr/2"},
        "issue": {"url": "https://api.example.com/issue/3"},
    }
    event_file4 = tmp_path / "event_comment_pr_url.json"
    event_file4.write_text(json.dumps(payload_comment_pr_url))
    monkeypatch.setenv("GITHUB_EVENT_NAME", "issue_comment")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_file4))

    added2 = {"called": False, "args": None}

    class Provider2:
        def __init__(self, pr_url=None):
            self.pr_url = pr_url

        def add_eyes_reaction(self, comment_id, disable_eyes=False):
            added2["called"] = True
            added2["args"] = (comment_id, disable_eyes)
            return "ok2"

    monkeypatch.setattr(garun, "get_git_provider", lambda: (lambda pr_url=None: Provider2(pr_url=pr_url)))
    monkeypatch.setattr(garun, "PRAgent", lambda: FakePRAgent())

    await garun.run_action()
    assert added2["called"] is True
    assert added2["args"][0] == 321
    # since pull_request_url path sets disable_eyes True
    assert added2["args"][1] is True


@pytest.mark.asyncio
async def test_issue_comment_non_pr(monkeypatch, tmp_path):
    # issue comment not a PR and no pull_request_url: should call PRAgent.handle_request without notify
    payload = {
        "action": "created",
        "comment": {"body": "do something", "id": 77},
        "issue": {"url": "https://api.example.com/issue/77"},
    }
    event_file = tmp_path / "event_nonpr.json"
    event_file.write_text(json.dumps(payload))
    monkeypatch.setenv("GITHUB_EVENT_NAME", "issue_comment")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_file))
    monkeypatch.setenv("GITHUB_TOKEN", "tk")

    # stub get_git_provider to ensure not used
    monkeypatch.setattr(garun, "get_git_provider", lambda: (lambda pr_url=None: None))

    handled = {"called": False, "args": None}

    class FakePRAgent2:
        async def handle_request(self, url, body, notify=None):
            handled["called"] = True
            handled["args"] = (url, body, notify)

    monkeypatch.setattr(garun, "PRAgent", lambda: FakePRAgent2())
    # ensure logger present
    monkeypatch.setattr(garun, "get_settings", lambda: FakeSettings())
    await garun.run_action()
    assert handled["called"] is True
    assert handled["args"][2] is None
