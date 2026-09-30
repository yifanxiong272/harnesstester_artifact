# file: gpt_researcher/prompts.py:772-799
# asked: {"lines": [780, 781, 782, 783, 784, 785, 786, 787, 789, 794, 795, 796, 797, 798, 799], "branches": [[780, 781], [780, 782], [794, 795], [794, 796], [796, 797], [796, 798]]}
# gained: {"lines": [780, 781, 782, 783, 784, 785, 786, 787, 789, 794, 795, 796, 797, 798, 799], "branches": [[780, 781], [780, 782], [794, 795], [796, 797]]}

import pytest
from gpt_researcher.prompts import Granite3PromptFamily


class SimpleDoc:
    def __init__(self, metadata, page_content):
        self.metadata = metadata
        self.page_content = page_content


def test_pretty_print_docs_empty_returns_empty_string():
    # empty list should return empty string (covers lines 780-781)
    result = Granite3PromptFamily.pretty_print_docs([])
    assert result == ""


def test_pretty_print_docs_generates_expected_format_and_respects_top_n():
    # prepare two simple documents
    docs = [
        SimpleDoc({}, "Content of first doc"),
        SimpleDoc({"source": "source-two", "title": "Second Title"}, "Second doc content"),
    ]

    # full output (top_n is None) should include both documents
    full = Granite3PromptFamily.pretty_print_docs(docs)
    prefix = Granite3PromptFamily._DOCUMENTS_PREFIX
    suffix = Granite3PromptFamily._DOCUMENTS_SUFFIX

    expected_all_documents = (
        "Document 0\n"
        "Title: None\n"
        "Content of first doc\n\n"
        "Document source-two\n"
        "Title: Second Title\n"
        "Second doc content"
    )
    expected_full = "".join([prefix, expected_all_documents, suffix])
    assert full == expected_full

    # with top_n=1 should include only the first document (covers the top_n branch)
    top1 = Granite3PromptFamily.pretty_print_docs(docs, top_n=1)
    expected_first_only = (
        "Document 0\n"
        "Title: None\n"
        "Content of first doc"
    )
    assert top1 == "".join([prefix, expected_first_only, suffix])


def test_join_local_web_documents_strips_prefix_and_suffix_and_joins():
    prefix = Granite3PromptFamily._DOCUMENTS_PREFIX
    suffix = Granite3PromptFamily._DOCUMENTS_SUFFIX

    # docs_context starts with prefix and web_context ends with suffix to trigger both slices (lines 794-797)
    docs_content = "LOCAL_DOCS"
    web_content = "WEB_DOCS"
    docs_context = prefix + docs_content
    web_context = web_content + suffix

    joined = Granite3PromptFamily.join_local_web_documents(docs_context, web_context)

    expected_all_documents = docs_content + "\n\n" + web_content
    expected = "".join([prefix, expected_all_documents, suffix])
    assert joined == expected
