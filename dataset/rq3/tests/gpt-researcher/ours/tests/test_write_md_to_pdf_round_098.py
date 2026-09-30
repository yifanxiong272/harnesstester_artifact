import sys
import types
import asyncio
import urllib
import builtins

import backend.utils as utils


def _install_fake_md2pdf(fake_impl):
    """Install a fake md2pdf.core module into sys.modules with md2pdf = fake_impl.
    Returns a cleanup function to remove inserted modules.
    """
    pkg = types.ModuleType("md2pdf")
    core = types.ModuleType("md2pdf.core")
    core.md2pdf = fake_impl
    sys.modules["md2pdf"] = pkg
    sys.modules["md2pdf.core"] = core

    def _cleanup():
        # remove entries if they still point to our modules
        if sys.modules.get("md2pdf") is pkg:
            del sys.modules["md2pdf"]
        if sys.modules.get("md2pdf.core") is core:
            del sys.modules["md2pdf.core"]

    return _cleanup


def test_write_md_to_pdf_success_round_098(capsys):
    # Arrange: capture calls to md2pdf and force preprocessing to a known value
    calls = []

    def fake_md2pdf(file_path, raw=None, css=None, base_url=None):
        # record the call for assertions
        calls.append((file_path, raw, css, base_url))
        # do not raise

    cleanup = _install_fake_md2pdf(fake_md2pdf)
    # Patch the image preprocessing function in the module under test
    orig_pre = utils._preprocess_images_for_pdf
    utils._preprocess_images_for_pdf = lambda text: "processed_text"

    try:
        # Act: run the coroutine synchronously
        result = asyncio.run(utils.write_md_to_pdf("![](img.png)", "report"))

        # Capture stdout from the function
        captured = capsys.readouterr()

        # Assert: md2pdf was called with expected file path and processed text
        assert calls, "md2pdf was not called"
        called_file_path, called_raw, called_css, called_base = calls[0]
        assert called_file_path == "outputs/report.pdf"
        assert called_raw == "processed_text"
        # base_url should be provided (exact value may vary by environment) but must be a str
        assert isinstance(called_base, str) and called_base

        # The function returns the URL-encoded file path
        assert result == urllib.parse.quote("outputs/report.pdf")

        # It should have printed a success message including the file path
        assert "Report written to outputs/report.pdf" in captured.out
    finally:
        # Restore and cleanup
        utils._preprocess_images_for_pdf = orig_pre
        cleanup()


def test_write_md_to_pdf_exception_round_098(capsys):
    # Arrange: make md2pdf raise to exercise the except branch
    def raising_md2pdf(file_path, raw=None, css=None, base_url=None):
        raise RuntimeError("boom")

    cleanup = _install_fake_md2pdf(raising_md2pdf)
    orig_pre = utils._preprocess_images_for_pdf
    utils._preprocess_images_for_pdf = lambda text: "processed_text"

    try:
        # Act
        result = asyncio.run(utils.write_md_to_pdf("text", "report"))

        # Capture stdout
        captured = capsys.readouterr()

        # Assert: on exception the function prints an error and returns an empty string
        assert result == ""
        assert "Error in converting Markdown to PDF: boom" in captured.out
    finally:
        utils._preprocess_images_for_pdf = orig_pre
        cleanup()
