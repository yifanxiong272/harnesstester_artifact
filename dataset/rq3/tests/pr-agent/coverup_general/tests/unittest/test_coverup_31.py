# file: pr_agent/tools/pr_help_docs.py:494-534
# asked: {"lines": [495, 497, 498, 499, 501, 502, 503, 504, 505, 507, 509, 510, 511, 513, 514, 515, 516, 518, 519, 520, 521, 522, 523, 526, 527, 528, 529, 530, 531, 532, 533, 534], "branches": [[503, 504], [503, 507], [514, 515], [514, 518], [528, 529], [528, 531]]}
# gained: {"lines": [495, 497, 498, 499, 501, 502, 503, 504, 505, 507, 509, 510, 511, 513, 514, 515, 516, 518, 519, 520, 521, 522, 523, 526, 527, 528, 531, 532, 533, 534], "branches": [[503, 504], [503, 507], [514, 515], [514, 518], [528, 531]]}

import types
import pytest
from types import SimpleNamespace

import pr_agent.tools.pr_help_docs as pr_help_mod


def _monkeypatch_prhelpdocs_init(monkeypatch):
    # Replace PRHelpDocs.__init__ to avoid heavy external initialization
    def fake_init(self, ctx_url, ai_handler=None, args=None, return_as_string=False):
        # minimal attributes used by the method under test
        self.ai_handler = object()
        self.vars = {}
        # default trim that simply returns input (can be overridden per-test)
        def default_trim(this, docs_prompt, max_allowed_txt_input, only_return_if_trim_needed=False):
            return docs_prompt
        self._trim_docs_input = types.MethodType(default_trim, self)
    monkeypatch.setattr(pr_help_mod.PRHelpDocs, "__init__", fake_init, raising=True)


@pytest.mark.asyncio
async def test_trim_returns_empty(monkeypatch):
    _monkeypatch_prhelpdocs_init(monkeypatch)

    # Prepare instance (uses patched __init__)
    inst = pr_help_mod.PRHelpDocs("ctx")

    # Monkeypatch aggregate to return something (should not be used because trim returns empty)
    def fake_aggregate(docs, return_just_headings=False):
        return "some headings"
    monkeypatch.setattr(pr_help_mod, "aggregate_documentation_files_for_prompt_contents", fake_aggregate)

    # Make _trim_docs_input return empty string to trigger early return and logging
    def trim_empty(self, docs_prompt, max_allowed_txt_input, only_return_if_trim_needed=False):
        return ""
    inst._trim_docs_input = types.MethodType(trim_empty, inst)

    # Provide a logger that records error calls
    logged = {"errors": []}
    class FakeLogger:
        def error(self, msg, **kwargs):
            logged["errors"].append((msg, kwargs))
        def exception(self, msg, **kwargs):
            logged["errors"].append(("EXC:"+msg, kwargs))
    monkeypatch.setattr(pr_help_mod, "get_logger", lambda: FakeLogger())

    res = await inst._rank_docs_and_return_them_as_prompt({"file1": "content"}, max_allowed_txt_input=1000)
    assert res == ""  # should return empty on trim empty
    assert any("_trim_docs_input returned an empty result." in e[0] for e in logged["errors"])


@pytest.mark.asyncio
async def test_load_yaml_returns_none(monkeypatch):
    _monkeypatch_prhelpdocs_init(monkeypatch)

    inst = pr_help_mod.PRHelpDocs("ctx")

    # aggregate to return headings
    def fake_aggregate(docs, return_just_headings=False):
        return "file1\n# heading"
    monkeypatch.setattr(pr_help_mod, "aggregate_documentation_files_for_prompt_contents", fake_aggregate)

    # trim returns the same non-empty string
    def trim_ok(self, docs_prompt, max_allowed_txt_input, only_return_if_trim_needed=False):
        return docs_prompt
    inst._trim_docs_input = types.MethodType(trim_ok, inst)

    # retry_with_fallback_models returns some response, but load_yaml returns None
    async def fake_retry(prep, model_type=None):
        return "some response that load_yaml can't parse"
    monkeypatch.setattr(pr_help_mod, "retry_with_fallback_models", fake_retry)

    # load_yaml returns None to trigger parse failure branch
    monkeypatch.setattr(pr_help_mod, "load_yaml", lambda response: None)

    # Minimal settings and PredictionPreparator
    monkeypatch.setattr(pr_help_mod, "get_settings", lambda: SimpleNamespace(pr_help_docs_headings_prompts=SimpleNamespace(system="s", user="u")))
    monkeypatch.setattr(pr_help_mod, "PredictionPreparator", lambda *a, **k: object())

    # Capture logger messages
    logged = {"errors": []}
    class FakeLogger:
        def error(self, msg, **kwargs):
            logged["errors"].append((msg, kwargs))
    monkeypatch.setattr(pr_help_mod, "get_logger", lambda: FakeLogger())

    res = await inst._rank_docs_and_return_them_as_prompt({"file1": "content", "file2": "other"}, max_allowed_txt_input=1000)
    assert res == ""
    assert any("Failed to parse the AI response." in e[0] for e in logged["errors"])


@pytest.mark.asyncio
async def test_successful_flow(monkeypatch):
    _monkeypatch_prhelpdocs_init(monkeypatch)

    inst = pr_help_mod.PRHelpDocs("ctx")

    # Create docs with deterministic ordering
    docs = {"path/a.md": "A content", "path/b.md": "B content"}

    # aggregate: when return_just_headings True return short headings; otherwise return full contents concatenated
    def fake_aggregate(docs_input, return_just_headings=False):
        if return_just_headings:
            # create a headings string that will be trimmed and set into vars
            return "\n".join(f"{i}: {k}" for i, k in enumerate(docs_input.keys()))
        else:
            return "\n\n".join(f"==={k}===\n{v}" for k, v in docs_input.items())
    monkeypatch.setattr(pr_help_mod, "aggregate_documentation_files_for_prompt_contents", fake_aggregate)

    # trim returns input unchanged
    def trim_ok(self, docs_prompt, max_allowed_txt_input, only_return_if_trim_needed=False):
        return docs_prompt
    inst._trim_docs_input = types.MethodType(trim_ok, inst)

    # Simulate AI response: relevant_files_ranking with indices "1" then "0"
    fake_response = "YAML-ISH"  # actual content ignored by load_yaml
    async def fake_retry(prep, model_type=None):
        return fake_response
    monkeypatch.setattr(pr_help_mod, "retry_with_fallback_models", fake_retry)

    # load_yaml will return dict with ranking indices
    def fake_load_yaml(response):
        assert response == fake_response
        return {"relevant_files_ranking": [{"idx": "1"}, {"idx": "0"}]}
    monkeypatch.setattr(pr_help_mod, "load_yaml", fake_load_yaml)

    # Minimal settings and PredictionPreparator
    monkeypatch.setattr(pr_help_mod, "get_settings", lambda: SimpleNamespace(pr_help_docs_headings_prompts=SimpleNamespace(system="sys", user="user")))
    monkeypatch.setattr(pr_help_mod, "PredictionPreparator", lambda *a, **k: object())

    # Logger not used in success path but provide one
    monkeypatch.setattr(pr_help_mod, "get_logger", lambda: SimpleNamespace(error=lambda *a, **k: None, exception=lambda *a, **k: None))

    res = await inst._rank_docs_and_return_them_as_prompt(docs, max_allowed_txt_input=1000)
    # Expect aggregate with selected docs in order of indices 1 then 0 -> keys b then a
    expected = fake_aggregate({"path/b.md": "B content", "path/a.md": "A content"}, return_just_headings=False)
    assert res == expected
    # Ensure vars['snippets'] was set (from initial headings aggregate)
    assert "snippets" in inst.vars and "path/a.md" in inst.vars["snippets"]


@pytest.mark.asyncio
async def test_exception_path(monkeypatch):
    _monkeypatch_prhelpdocs_init(monkeypatch)

    inst = pr_help_mod.PRHelpDocs("ctx")

    # aggregate to produce headings
    monkeypatch.setattr(pr_help_mod, "aggregate_documentation_files_for_prompt_contents", lambda docs, return_just_headings=False: "h")

    # trim returns non-empty so execution continues to retry
    def trim_ok(self, docs_prompt, max_allowed_txt_input, only_return_if_trim_needed=False):
        return docs_prompt
    inst._trim_docs_input = types.MethodType(trim_ok, inst)

    # Make retry_with_fallback_models raise to trigger exception handler
    async def fake_retry(prep, model_type=None):
        raise RuntimeError("boom")
    monkeypatch.setattr(pr_help_mod, "retry_with_fallback_models", fake_retry)

    # Provide minimal settings and PredictionPreparator
    monkeypatch.setattr(pr_help_mod, "get_settings", lambda: SimpleNamespace(pr_help_docs_headings_prompts=SimpleNamespace(system="s", user="u")))
    monkeypatch.setattr(pr_help_mod, "PredictionPreparator", lambda *a, **k: object())

    # Logger that records exception calls
    logged = {"exceptions": []}
    class FakeLogger:
        def error(self, *a, **k):
            pass
        def exception(self, msg, **kwargs):
            logged["exceptions"].append(msg)
    monkeypatch.setattr(pr_help_mod, "get_logger", lambda: FakeLogger())

    res = await inst._rank_docs_and_return_them_as_prompt({"f": "c"}, max_allowed_txt_input=1000)
    assert res == ""
    assert any("Unexpected exception thrown" in e for e in logged["exceptions"])
