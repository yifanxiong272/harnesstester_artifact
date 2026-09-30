# file: pr_agent/tools/pr_help_message.py:96-270
# asked: {"lines": [97, 98, 99, 101, 102, 103, 104, 106, 107, 110, 112, 113, 114, 115, 118, 120, 121, 122, 123, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 136, 137, 138, 140, 141, 142, 143, 144, 145, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 161, 162, 163, 164, 165, 166, 167, 168, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 183, 187, 188, 190, 192, 193, 194, 195, 197, 198, 199, 200, 201, 202, 203, 204, 206, 207, 208, 209, 210, 211, 212, 213, 214, 216, 217, 218, 219, 220, 221, 222, 223, 224, 226, 227, 228, 229, 230, 231, 232, 233, 234, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 249, 250, 251, 252, 253, 254, 255, 256, 258, 260, 261, 262, 263, 264, 266, 267, 268, 269, 270], "branches": [[98, 99], [98, 192], [101, 102], [101, 110], [102, 103], [102, 106], [126, 127], [126, 133], [137, 138], [137, 140], [142, 143], [142, 145], [150, 151], [150, 158], [152, 153], [152, 157], [161, 162], [161, 171], [163, 164], [163, 168], [172, 173], [172, 187], [177, 178], [177, 187], [179, 180], [179, 183], [187, 188], [187, 190], [192, 193], [192, 197], [249, 250], [249, 256], [251, 252], [251, 253], [256, 258], [256, 260], [261, 262], [261, 263], [266, 267], [266, 270]]}
# gained: {"lines": [97, 98, 99, 101, 102, 103, 104, 107, 110, 112, 113, 114, 115, 118, 120, 121, 122, 123, 125, 126, 127, 128, 129, 130, 133, 134, 136, 137, 138, 140, 141, 142, 143, 144, 145, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 161, 162, 163, 164, 165, 166, 167, 168, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 183, 187, 188, 192, 197, 198, 199, 200, 201, 202, 203, 204, 206, 207, 208, 209, 210, 211, 212, 213, 214, 216, 217, 218, 219, 220, 221, 222, 223, 224, 226, 227, 228, 229, 230, 231, 232, 233, 234, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 249, 250, 251, 252, 253, 254, 255, 256, 258, 266, 267, 268, 269, 270], "branches": [[98, 99], [98, 192], [101, 102], [101, 110], [102, 103], [126, 127], [126, 133], [137, 138], [137, 140], [142, 143], [150, 151], [150, 158], [152, 153], [161, 162], [161, 171], [163, 164], [172, 173], [177, 178], [177, 187], [179, 180], [179, 183], [187, 188], [192, 197], [249, 250], [249, 256], [251, 252], [251, 253], [256, 258], [266, 267]]}

import asyncio
import os
from pathlib import Path
import pytest

import pr_agent.tools.pr_help_message as phm


class DummyTokenHandler:
    def __init__(self, a, vars, system_prompt, user_prompt):
        self.vars = vars

    def count_tokens(self, text):
        return 999999


class FakeConfig(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get(self, key, default=None):
        return dict.get(self, key, default)


class FakePrompts:
    def __init__(self):
        self.system = "system"
        self.user = "user"


class FakeSettings:
    def __init__(self, openai_key=None, publish_output=True, model="mymodel", disable_checkboxes=False):
        self._map = {}
        if openai_key is not None:
            self._map['openai.key'] = openai_key
        self.pr_help_prompts = FakePrompts()
        self.config = FakeConfig(publish_output=publish_output, model=model, disable_checkboxes=disable_checkboxes)

    def get(self, key, default=None):
        return self._map.get(key, default)

    @property
    def pr_help(self):
        return {'some': 'cfg'}


class SimpleProvider:
    def __init__(self):
        self.published = []
        self.pr_url = "http://example/pr"

    def publish_comment(self, text):
        self.published.append(text)

    def is_supported(self, feature):
        return False


@pytest.mark.asyncio
async def test_openai_missing_publish(monkeypatch):
    # Setup: ensure parse_args returns a question
    monkeypatch.setattr(phm.PRHelpMessage, "parse_args", lambda self, args: "Some question")
    # Replace TokenHandler so __init__ works
    monkeypatch.setattr(phm, "TokenHandler", DummyTokenHandler)
    # Fake settings with no openai key and publish_output True
    fake_settings = FakeSettings(openai_key=None, publish_output=True)
    monkeypatch.setattr(phm, "get_settings", lambda: fake_settings)
    # Fake git provider
    provider = SimpleProvider()
    monkeypatch.setattr(phm, "get_git_provider_with_context", lambda pr_url: provider)

    inst = phm.PRHelpMessage("http://pr", args="args")
    result = await inst.run()
    # It should publish a comment telling about missing OpenAI key
    assert any("requires an OpenAI API key" in c for c in provider.published)
    assert result in (None, "")


@pytest.mark.asyncio
async def test_docs_processing_and_response_string(monkeypatch, tmp_path):
    # Create fake md files
    md1 = tmp_path / "docs1.md"
    md1.write_text("# Title\nContent here")
    md2 = tmp_path / "overview.md"
    md2.write_text("overview content")

    def fake_glob(self, pattern):
        return [md1, md2]

    monkeypatch.setattr(phm.Path, "glob", fake_glob)
    # parse_args returns question
    monkeypatch.setattr(phm.PRHelpMessage, "parse_args", lambda self, args: "What is this repo about?")
    monkeypatch.setattr(phm, "TokenHandler", DummyTokenHandler)
    # ensure MAX_TOKENS contains our model
    monkeypatch.setattr(phm, "MAX_TOKENS", {"mymodel": 10})
    # clip_tokens replacement
    monkeypatch.setattr(phm, "clip_tokens", lambda text, limit: "CLIPPED_CONTENT")
    # load_yaml returns the raw response (string)
    monkeypatch.setattr(phm, "load_yaml", lambda r: r)
    # retry returns a string that load_yaml will return as-is
    async def fake_retry(fn, model_type=None):
        return "UNPARSABLE YAML STRING ANSWER"

    monkeypatch.setattr(phm, "retry_with_fallback_models", fake_retry)
    # Fake settings: openai key present, publish_output True
    fake_settings = FakeSettings(openai_key="key", publish_output=True, model="mymodel")
    monkeypatch.setattr(phm, "get_settings", lambda: fake_settings)
    # Hook TokenHandler.count_tokens to return huge number to trigger clipping branch
    def big_count(self, text):
        return 1000000

    monkeypatch.setattr(DummyTokenHandler, "count_tokens", big_count)
    # Git provider to capture published content
    provider = SimpleProvider()
    monkeypatch.setattr(phm, "get_git_provider_with_context", lambda pr_url: provider)

    inst = phm.PRHelpMessage("http://pr", args="args")
    result = await inst.run()
    assert any("UNPARSABLE YAML STRING ANSWER" in text for text in provider.published)
    assert result in (None, "")


@pytest.mark.asyncio
async def test_response_dict_no_relevant_sections(monkeypatch):
    # Setup basic environment similar to previous test
    monkeypatch.setattr(phm.PRHelpMessage, "parse_args", lambda self, args: "Q")
    monkeypatch.setattr(phm, "TokenHandler", DummyTokenHandler)
    monkeypatch.setattr(phm.Path, "glob", lambda self, p: [])
    # retry returns YAML dict
    async def fake_retry(fn, model_type=None):
        return {"response": None, "relevant_sections": []}

    monkeypatch.setattr(phm, "retry_with_fallback_models", fake_retry)
    # load_yaml returns as-is (a dict)
    monkeypatch.setattr(phm, "load_yaml", lambda r: r)
    fake_settings = FakeSettings(openai_key="k", publish_output=True, model="mymodel")
    monkeypatch.setattr(phm, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(phm, "MAX_TOKENS", {"mymodel": 1000})
    provider = SimpleProvider()
    monkeypatch.setattr(phm, "get_git_provider_with_context", lambda pr_url: provider)

    inst = phm.PRHelpMessage("http://pr", args="args")
    res = await inst.run()
    # Should publish a "Could not find relevant information" message
    assert any("Could not find relevant information" in p for p in provider.published)
    assert res in (None, "")


@pytest.mark.asyncio
async def test_response_with_relevant_sections_and_publish(monkeypatch):
    monkeypatch.setattr(phm.Path, "glob", lambda self, p: [])
    monkeypatch.setattr(phm.PRHelpMessage, "parse_args", lambda self, args: "Q2")
    monkeypatch.setattr(phm, "TokenHandler", DummyTokenHandler)

    async def fake_retry(fn, model_type=None):
        return {"response": "This is the answer", "relevant_sections": [
            {"file_name": "path/to/doc1.md", "relevant_section_header_string": "Header One"},
            {"file_name": "another/doc2.md", "relevant_section_header_string": ""}
        ]}

    monkeypatch.setattr(phm, "retry_with_fallback_models", fake_retry)
    monkeypatch.setattr(phm, "load_yaml", lambda r: r)
    monkeypatch.setattr(phm, "MAX_TOKENS", {"mymodel": 2000})
    monkeypatch.setattr(phm, "clip_tokens", lambda text, lim: text)
    monkeypatch.setattr(phm.PRHelpMessage, "format_markdown_header", lambda self, h: h.replace(" ", "-").lower())
    fake_settings = FakeSettings(openai_key="k", publish_output=True, model="mymodel")
    monkeypatch.setattr(phm, "get_settings", lambda: fake_settings)
    provider = SimpleProvider()
    monkeypatch.setattr(phm, "get_git_provider_with_context", lambda pr_url: provider)

    inst = phm.PRHelpMessage("http://pr", args="args")
    res = await inst.run()
    published = provider.published[-1] if provider.published else ""
    assert "This is the answer" in published
    assert "path/to/doc1#header-one" in published
    assert "another/doc2" in published
    assert res in (None, "")


@pytest.mark.asyncio
async def test_pr_comment_github_and_bbdc_paths(monkeypatch):
    # Setup: question_str falsy to go into PR comment generation path
    monkeypatch.setattr(phm.PRHelpMessage, "parse_args", lambda self, args: None)
    monkeypatch.setattr(phm, "TokenHandler", DummyTokenHandler)
    fake_settings = FakeSettings(openai_key="k", publish_output=True, model="mymodel", disable_checkboxes=False)
    monkeypatch.setattr(phm, "get_settings", lambda: fake_settings)

    class FakeGitHub:
        pass

    class FakeBB:
        pass

    monkeypatch.setattr(phm, "GithubProvider", FakeGitHub)
    monkeypatch.setattr(phm, "BitbucketServerProvider", FakeBB)

    class GitHubProviderInstance(FakeGitHub):
        def __init__(self):
            self.published = []
            self.pr_url = "http://example/pr"

        def publish_comment(self, text):
            self.published.append(text)

        def is_supported(self, feature):
            return True

    gh = GitHubProviderInstance()
    monkeypatch.setattr(phm, "get_git_provider_with_context", lambda pr_url: gh)

    inst = phm.PRHelpMessage("http://pr", args=None)
    res = await inst.run()
    assert any("<table>" in text for text in gh.published)
    assert any("[DESCRIBE]" in text for text in gh.published)
    assert res in (None, "")

    class BBDProviderInstance(FakeBB):
        def __init__(self):
            self.published = []
            self.pr_url = "http://example/pr"

        def publish_comment(self, text):
            self.published.append(text)

        def is_supported(self, feature):
            return True

    bb = BBDProviderInstance()
    monkeypatch.setattr(phm, "get_git_provider_with_context", lambda pr_url: bb)
    monkeypatch.setattr(phm, "generate_bbdc_table", lambda tools, desc: "BB_TABLE")

    inst2 = phm.PRHelpMessage("http://pr", args=None)
    res2 = await inst2.run()
    assert any("BB_TABLE" in text for text in bb.published)
    assert res2 in (None, "")


@pytest.mark.asyncio
async def test_exception_handling_does_not_raise(monkeypatch):
    monkeypatch.setattr(phm.PRHelpMessage, "parse_args", lambda self, args: "Q")
    monkeypatch.setattr(phm, "TokenHandler", DummyTokenHandler)
    async def raising_retry(*args, **kwargs):
        raise RuntimeError("simulated failure")
    monkeypatch.setattr(phm, "retry_with_fallback_models", raising_retry)
    fake_settings = FakeSettings(openai_key="k", publish_output=False, model="mymodel")
    monkeypatch.setattr(phm, "get_settings", lambda: fake_settings)
    provider = SimpleProvider()
    monkeypatch.setattr(phm, "get_git_provider_with_context", lambda pr_url: provider)

    inst = phm.PRHelpMessage("http://pr", args="args")
    res = await inst.run()
    assert res in (None, "")
