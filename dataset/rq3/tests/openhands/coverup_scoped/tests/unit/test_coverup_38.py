# file: openhands/resolver/send_pull_request.py:461-605
# asked: {"lines": [509, 511, 512, 513, 514, 516, 517, 518, 519, 521, 523, 524, 525, 526, 528, 530, 531, 532, 533, 536, 550, 551, 584, 585, 586, 587, 601, 602, 603], "branches": [[488, 498], [504, 509], [509, 511], [509, 516], [516, 517], [516, 523], [523, 524], [523, 530], [530, 531], [530, 536], [549, 550], [557, 591], [560, 591], [568, 591], [591, 595], [595, 605]]}
# gained: {"lines": [509, 511, 512, 513, 514, 516, 517, 518, 519, 521, 523, 530, 536, 550, 551, 584, 585, 586, 587, 601, 602, 603], "branches": [[504, 509], [509, 511], [509, 516], [516, 517], [516, 523], [523, 530], [530, 536], [549, 550], [557, 591], [591, 595], [595, 605]]}

import io
import json
from types import SimpleNamespace

import pytest

from openhands.integrations.service_types import ProviderType
from openhands.resolver.send_pull_request import update_existing_pull_request
import openhands.resolver.send_pull_request as send_pull_request


class FakeHandler:
    def __init__(self):
        self.sent_comments = []
        self.replies = []
        self.auth_url = "https://auth/"
        self.pr_url = "https://pr/123"

    def get_authorize_url(self):
        return self.auth_url

    def get_pull_url(self, number):
        return self.pr_url

    def send_comment_msg(self, number, message):
        self.sent_comments.append((number, message))

    def reply_to_comment(self, number, comment_id, message):
        self.replies.append((number, comment_id, message))


class SimpleResult:
    def __init__(self, returncode=0, stderr=""):
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = ""


class FakeIssue:
    def __init__(self, owner, repo, head_branch, number, thread_ids=None):
        self.owner = owner
        self.repo = repo
        self.head_branch = head_branch
        self.number = number
        self.thread_ids = thread_ids or []


def test_azure_devops_branch_success(monkeypatch, tmp_path):
    # Prepare fake issue for Azure DevOps where owner is "org/project"
    issue = FakeIssue(owner="org/project", repo="myrepo", head_branch="feature-branch", number=42)

    fake_handler = FakeHandler()

    # Monkeypatch ServiceContextIssue to return our fake handler regardless of args
    monkeypatch.setattr(send_pull_request, "ServiceContextIssue", lambda *args, **kwargs: fake_handler)

    # Capture subprocess.run call and return success
    captured = {}

    def fake_run(cmd, shell, capture_output, text):
        captured["cmd"] = cmd
        return SimpleResult(returncode=0)

    monkeypatch.setattr(send_pull_request.subprocess, "run", fake_run)

    # Run function
    pr_url = update_existing_pull_request(
        issue=issue,
        token="token",
        username=None,
        platform=ProviderType.AZURE_DEVOPS,
        patch_dir=str(tmp_path / "patches"),
        llm_config=None,
        comment_message=None,
        additional_message=None,
        base_domain=None,
    )

    # Assertions
    assert pr_url == fake_handler.pr_url
    # Ensure push command constructed contains authorize url and owner/repo and branch
    assert fake_handler.get_authorize_url() in captured["cmd"]
    assert f"{issue.owner}/{issue.repo}.git" in captured["cmd"]
    assert issue.head_branch in captured["cmd"]


def test_push_failure_logs_and_raises(monkeypatch, tmp_path):
    issue = FakeIssue(owner="owner", repo="repo", head_branch="b", number=1)

    fake_handler = FakeHandler()
    monkeypatch.setattr(send_pull_request, "ServiceContextIssue", lambda *a, **k: fake_handler)

    # Fake subprocess.run returns non-zero to trigger error path
    def fake_run_fail(cmd, shell, capture_output, text):
        return SimpleResult(returncode=1, stderr="some git error")

    monkeypatch.setattr(send_pull_request.subprocess, "run", fake_run_fail)

    # Capture logger.error calls
    errors = []

    def fake_logger_error(msg):
        errors.append(msg)

    monkeypatch.setattr(send_pull_request.logger, "error", fake_logger_error)

    with pytest.raises(RuntimeError):
        update_existing_pull_request(
            issue=issue,
            token="t",
            username=None,
            platform=ProviderType.GITHUB,
            patch_dir=str(tmp_path),
            llm_config=None,
            comment_message=None,
            additional_message=None,
            base_domain=None,
        )

    assert any("some git error" in e for e in errors)


def test_comment_and_llm_and_reply_success(monkeypatch, tmp_path):
    # This test exercises:
    # - additional_message JSON parsing
    # - building comment_message from explanations
    # - LLM summarization path
    # - sending comment_message
    # - replying to thread IDs
    explanations = ["Fixed typo", "Updated import"]
    additional_message = json.dumps(explanations)
    issue = FakeIssue(owner="owner", repo="repo", head_branch="b", number=5, thread_ids=["t1", "t2"])

    fake_handler = FakeHandler()
    monkeypatch.setattr(send_pull_request, "ServiceContextIssue", lambda *a, **k: fake_handler)

    # Subprocess.run success
    monkeypatch.setattr(send_pull_request.subprocess, "run", lambda *a, **k: SimpleResult(returncode=0))

    # Mock jinja2.Template to ignore file contents and render a deterministic prompt
    class FakeTemplate:
        def __init__(self, text):
            self.text = text

        def render(self, **kwargs):
            # The template would get comment_message; we return something LLM will use
            return "Rendered PROMPT with: " + kwargs.get("comment_message", "")

    monkeypatch.setattr(send_pull_request.jinja2, "Template", FakeTemplate)

    # Provide a fake file read for the template open call
    monkeypatch.setattr("builtins.open", lambda *a, **k: io.StringIO("template content"))

    # Fake LLM that returns a response with nested message content
    class FakeLLM:
        def __init__(self, cfg, service_id=None):
            self.cfg = cfg
            self.service_id = service_id

        def completion(self, messages):
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="LLM summarized content\n"))])

    monkeypatch.setattr(send_pull_request, "LLM", FakeLLM)

    pr_url = update_existing_pull_request(
        issue=issue,
        token="tok",
        username="user",
        platform=ProviderType.GITLAB,
        patch_dir=str(tmp_path),
        llm_config=object(),  # non-None triggers LLM usage
        comment_message=None,
        additional_message=additional_message,
        base_domain=None,
    )

    # Verify PR url returned
    assert pr_url == fake_handler.pr_url

    # Ensure comment was sent and content equals LLM summarized content (stripped)
    assert len(fake_handler.sent_comments) == 1
    sent_number, sent_msg = fake_handler.sent_comments[0]
    assert sent_number == issue.number
    assert "LLM summarized content" in sent_msg

    # Ensure replies sent for each thread id
    assert len(fake_handler.replies) == len(explanations)
    for i, reply in enumerate(fake_handler.replies):
        num, cid, content = reply
        assert num == issue.number
        assert cid == issue.thread_ids[i]
        assert content == explanations[i]


def test_additional_message_json_decode_failure_for_comment_and_reply(monkeypatch, tmp_path):
    # This test ensures JSON decoding errors trigger fallback messages and proper send_comment_msg calls
    bad_additional = "not a json"
    issue = FakeIssue(owner="owner", repo="repo", head_branch="b", number=7, thread_ids=["tid"])

    fake_handler = FakeHandler()
    monkeypatch.setattr(send_pull_request, "ServiceContextIssue", lambda *a, **k: fake_handler)

    monkeypatch.setattr(send_pull_request.subprocess, "run", lambda *a, **k: SimpleResult(returncode=0))

    # Ensure jinja2.Template and open are present though not used because JSON parse will fail before LLM
    monkeypatch.setattr(send_pull_request.jinja2, "Template", lambda txt: SimpleNamespace(render=lambda **kw: "prompt"))
    monkeypatch.setattr("builtins.open", lambda *a, **k: io.StringIO("template content"))

    pr_url = update_existing_pull_request(
        issue=issue,
        token="tok",
        username=None,
        platform=ProviderType.BITBUCKET,
        patch_dir=str(tmp_path),
        llm_config=None,  # LLM not used because JSON decoding fails
        comment_message=None,
        additional_message=bad_additional,
        base_domain=None,
    )

    # Two send_comment_msg calls expected:
    # 1) from the comment_message fallback when parsing fails
    # 2) from the reply-to-threads fallback when parsing fails
    assert len(fake_handler.sent_comments) == 2
    first_num, first_msg = fake_handler.sent_comments[0]
    second_num, second_msg = fake_handler.sent_comments[1]

    assert first_num == issue.number
    assert "failed to parse or summarize" in first_msg or "failed to parse" in first_msg
    assert second_num == issue.number
    assert "Error occurred when replying to threads" in second_msg

    # Return value should equal handler.get_pull_url
    assert pr_url == fake_handler.pr_url


def test_unsupported_platform_raises_value_error(monkeypatch, tmp_path):
    # Passing a platform value that doesn't match any ProviderType branch should raise ValueError
    issue = FakeIssue(owner="o", repo="r", head_branch="b", number=9)
    # Ensure subprocess.run won't be called, but patch it anyway
    monkeypatch.setattr(send_pull_request.subprocess, "run", lambda *a, **k: SimpleResult(returncode=0))

    with pytest.raises(ValueError):
        update_existing_pull_request(
            issue=issue,
            token="t",
            username=None,
            platform="UNSUPPORTED_PLATFORM",
            patch_dir=str(tmp_path),
            llm_config=None,
            comment_message=None,
            additional_message=None,
            base_domain=None,
        )
