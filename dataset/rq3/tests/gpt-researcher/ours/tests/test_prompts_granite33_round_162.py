import pytest
from types import SimpleNamespace

from gpt_researcher.prompts import Granite33PromptFamily


def make_doc(page_content, metadata):
    return SimpleNamespace(page_content=page_content, metadata=metadata)


def test_get_content_with_title_round_162():
    doc = make_doc("Some content", {"title": "MyTitle"})
    result = Granite33PromptFamily._get_content(doc)
    # When metadata contains a title, it should be prefixed and newline-separated,
    # and surrounding whitespace trimmed.
    assert result == "Title: MyTitle\nSome content"


def test_get_content_without_title_round_162():
    # No title in metadata: should return the page_content stripped
    doc = make_doc("  Content with spaces \n", {"source": "doc1"})
    result = Granite33PromptFamily._get_content(doc)
    assert result == "Content with spaces"


def test_pretty_print_docs_top_n_and_source_round_162():
    # First doc has a source and title; second has empty metadata.
    docs = [
        make_doc("First body", {"source": "s1", "title": "T1"}),
        make_doc("Second body", {}),
    ]
    out = Granite33PromptFamily.pretty_print_docs(docs, top_n=1)
    # Only the first document should be included because top_n=1
    assert '"document_id": "s1"' in out
    # Title should be included and formatted as in _get_content
    assert "Title: T1\nFirst body" in out


def test_pretty_print_docs_default_source_and_join_round_162():
    # When metadata lacks a 'source', the index should be used as the document_id
    docs = [
        make_doc("A", {}),
        make_doc("B", {}),
    ]
    out = Granite33PromptFamily.pretty_print_docs(docs)
    # Both documents should be present and have numeric ids 0 and 1
    assert '"document_id": "0"' in out
    assert '"document_id": "1"' in out
    assert "A" in out and "B" in out


def test_join_local_web_documents_round_162():
    local = "local context"
    web = "web context"
    joined = Granite33PromptFamily.join_local_web_documents(local, web)
    assert joined == "local context\n\nweb context"
