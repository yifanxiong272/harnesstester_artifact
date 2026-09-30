from types import SimpleNamespace
import gpt_researcher.prompts as prompts


def test_granite33_branch_round_128(monkeypatch):
    """When cfg.smart_llm contains '3.3' Granite33PromptFamily should be selected
    and its class-level methods should be invoked by the instance wrappers.
    """
    # Create instance bypassing __init__ and inject cfg
    gp = object.__new__(prompts.GranitePromptFamily)
    gp.cfg = SimpleNamespace(smart_llm="model-3.3-alpha")

    # Patch the Granite33PromptFamily methods that will be dispatched to
    def fake_pretty_print_docs(docs, top_n=None, *args, **kwargs):
        return f"G33_PRETTY:{docs}:{top_n}"

    def fake_join_local_web_documents(docs_context, web_context, *args, **kwargs):
        return f"G33_JOIN:{docs_context}:{web_context}"

    monkeypatch.setattr(prompts.Granite33PromptFamily, "pretty_print_docs", fake_pretty_print_docs)
    monkeypatch.setattr(prompts.Granite33PromptFamily, "join_local_web_documents", fake_join_local_web_documents)

    # Call the instance wrappers which should delegate to the patched class methods
    out1 = gp.pretty_print_docs(["doc1"], top_n=5)
    assert out1 == "G33_PRETTY:['doc1']:5"

    out2 = gp.join_local_web_documents({"k": "v"}, ["web"])
    assert out2 == "G33_JOIN:{'k': 'v'}:['web']"

    # Ensure the internal selector returns the expected class object
    assert gp._get_granite_class() is prompts.Granite33PromptFamily


def test_granite3_branch_round_128(monkeypatch):
    """When cfg.smart_llm contains '3' (but not '3.3') Granite3PromptFamily should
    be selected and its methods used.
    """
    gp = object.__new__(prompts.GranitePromptFamily)
    gp.cfg = SimpleNamespace(smart_llm="release-3")

    def fake_pretty(docs, top_n=None, *args, **kwargs):
        return f"G3_PRETTY:{docs}:{top_n}"

    def fake_join(ctx, web, *args, **kwargs):
        return f"G3_JOIN:{ctx}:{web}"

    monkeypatch.setattr(prompts.Granite3PromptFamily, "pretty_print_docs", fake_pretty)
    monkeypatch.setattr(prompts.Granite3PromptFamily, "join_local_web_documents", fake_join)

    assert gp.pretty_print_docs("single-doc", top_n=1) == "G3_PRETTY:single-doc:1"
    assert gp.join_local_web_documents("ctx", "web") == "G3_JOIN:ctx:web"
    assert gp._get_granite_class() is prompts.Granite3PromptFamily


def test_default_prompt_family_branch_round_128(monkeypatch):
    """When cfg.smart_llm does not contain a recognized granite version the default
    PromptFamily should be returned and its methods invoked.
    """
    gp = object.__new__(prompts.GranitePromptFamily)
    gp.cfg = SimpleNamespace(smart_llm="legacy-2")

    def stub_pretty(docs, top_n=None, *args, **kwargs):
        return f"DEFAULT_PRETTY:{docs}:{top_n}"

    def stub_join(docs_context, web_context, *args, **kwargs):
        return f"DEFAULT_JOIN:{docs_context}:{web_context}"

    monkeypatch.setattr(prompts.PromptFamily, "pretty_print_docs", stub_pretty)
    monkeypatch.setattr(prompts.PromptFamily, "join_local_web_documents", stub_join)

    assert gp.pretty_print_docs([1, 2, 3], top_n=0) == "DEFAULT_PRETTY:[1, 2, 3]:0"
    assert gp.join_local_web_documents(None, True) == "DEFAULT_JOIN:None:True"
    assert gp._get_granite_class() is prompts.PromptFamily
