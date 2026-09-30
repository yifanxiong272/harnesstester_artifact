import pytest

from gpt_researcher.prompts import Granite3PromptFamily


class FakeDoc:
    def __init__(self, metadata, page_content):
        # metadata must implement .get(key, default)
        self.metadata = metadata
        self.page_content = page_content


def test_pretty_print_docs_empty_round_086():
    # empty docs should return empty string (covers 780->781)
    out = Granite3PromptFamily.pretty_print_docs([])
    assert out == ""


def test_pretty_print_docs_top_n_round_086():
    # when docs present, output should include prefix, formatted document, and suffix
    docs = [
        FakeDoc({"source": "source-a", "title": "Title A"}, "Content A"),
        FakeDoc({"source": "source-b", "title": "Title B"}, "Content B"),
    ]
    # Use top_n to exercise the comprehension limiting branch
    out = Granite3PromptFamily.pretty_print_docs(docs, top_n=1)

    prefix = Granite3PromptFamily._DOCUMENTS_PREFIX
    suffix = Granite3PromptFamily._DOCUMENTS_SUFFIX

    expected_body = "Document source-a\nTitle: Title A\nContent A"
    expected = "".join([prefix, expected_body, suffix])

    assert out == expected


def test_join_local_web_documents_trim_both_round_086():
    # docs_context starts with prefix and web_context ends with suffix -> both trimmed
    prefix = Granite3PromptFamily._DOCUMENTS_PREFIX
    suffix = Granite3PromptFamily._DOCUMENTS_SUFFIX

    docs_inner = "LOCAL_DOC"
    web_inner = "WEB_DOC"

    docs_context = prefix + docs_inner
    web_context = web_inner + suffix

    out = Granite3PromptFamily.join_local_web_documents(docs_context, web_context)

    # After trimming, the joined middle should be docs_inner + "\n\n" + web_inner
    expected_middle = docs_inner + "\n\n" + web_inner
    expected = "".join([prefix, expected_middle, suffix])

    assert out == expected


def test_join_local_web_documents_no_trim_round_086():
    # neither docs_context nor web_context include prefix/suffix -> no trimming
    prefix = Granite3PromptFamily._DOCUMENTS_PREFIX
    suffix = Granite3PromptFamily._DOCUMENTS_SUFFIX

    docs_context = "DOCS_RAW"
    web_context = "WEB_RAW"

    out = Granite3PromptFamily.join_local_web_documents(docs_context, web_context)

    expected_middle = docs_context + "\n\n" + web_context
    expected = "".join([prefix, expected_middle, suffix])

    assert out == expected
