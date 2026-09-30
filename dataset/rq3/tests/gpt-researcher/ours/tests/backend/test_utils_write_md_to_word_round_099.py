import sys
import types
import asyncio
import backend.utils as utils


def _make_fake_docx_module(doc_instances_list):
    mod = types.ModuleType("docx")

    class Document:
        def __init__(self):
            # record every created document so tests can inspect it
            doc_instances_list.append(self)
            self.saved = None

        def save(self, path):
            # don't touch the filesystem; just record the path
            self.saved = path

    mod.Document = Document
    return mod


def _make_fake_htmldocx_module(add_behavior):
    mod = types.ModuleType("htmldocx")

    class HtmlToDocx:
        def add_html_to_document(self, html, doc):
            return add_behavior(html, doc)

    mod.HtmlToDocx = HtmlToDocx
    return mod


def test_write_md_to_word_success_round_099(monkeypatch, capsys):
    # Prepare a container to capture created Document instances
    created_docs = []

    # Install fake docx module so `from docx import Document` inside the function
    fake_docx = _make_fake_docx_module(created_docs)
    monkeypatch.setitem(sys.modules, "docx", fake_docx)

    # HtmlToDocx behaviour: attach the html to the doc but do not raise
    def add_html_behaviour(html, doc):
        # record the html on the doc instance for later inspection
        setattr(doc, "_added_html", html)
        return None

    fake_htmldocx = _make_fake_htmldocx_module(add_html_behaviour)
    monkeypatch.setitem(sys.modules, "htmldocx", fake_htmldocx)

    # Patch mistune.html used inside the function to produce deterministic HTML
    monkeypatch.setattr(utils.mistune, "html", lambda text: "<p>converted</p>")

    # Patch urllib.parse.quote to a deterministic wrapper so we can assert on it
    monkeypatch.setattr(utils.urllib.parse, "quote", lambda x: f"encoded:{x}")

    # Call the async function synchronously via asyncio.run
    result = asyncio.run(utils.write_md_to_word("# title", filename="report"))

    # Ensure the function returned the encoded file path and the doc save was invoked
    expected_file_path = "outputs/report.docx"
    assert result == f"encoded:{expected_file_path}", "expected encoded file path returned"

    # Confirm a Document instance was created and its save() recorded the path
    assert created_docs, "Document() should have been instantiated"
    doc = created_docs[0]
    assert getattr(doc, "saved") == expected_file_path, "Document.save should have been called with the expected path"

    # Confirm the HtmlToDocx.add_html_to_document was invoked with the converted HTML
    assert getattr(doc, "_added_html") == "<p>converted</p>", "converted HTML should have been added to the document"

    # Confirm user-facing print was emitted
    captured = capsys.readouterr()
    assert f"Report written to {expected_file_path}" in captured.out


def test_write_md_to_word_exception_round_099(monkeypatch, capsys):
    # Simulate a failure in HtmlToDocx.add_html_to_document to exercise the except path
    fake_docx = _make_fake_docx_module([])
    monkeypatch.setitem(sys.modules, "docx", fake_docx)

    def raising_add_html(html, doc):
        raise ValueError("boom")

    fake_htmldocx = _make_fake_htmldocx_module(raising_add_html)
    monkeypatch.setitem(sys.modules, "htmldocx", fake_htmldocx)

    # Ensure mistune.html is deterministic
    monkeypatch.setattr(utils.mistune, "html", lambda text: "<p>converted</p>")

    # Use the real urllib.quote behavior or a deterministic stub; here we don't need it
    # because an exception occurs before return. Still, keep things explicit.
    monkeypatch.setattr(utils.urllib.parse, "quote", lambda x: f"encoded:{x}")

    # Run the function; it should catch the exception and return an empty string
    result = asyncio.run(utils.write_md_to_word("# title", filename="report"))

    assert result == "", "On exception the function should return an empty string"

    # Confirm the error message was printed with the original exception message
    captured = capsys.readouterr()
    assert "Error in converting Markdown to DOCX: boom" in captured.out
