# file: aider/coders/base_coder.py:817-857
# asked: {"lines": [836, 848, 849, 850, 851], "branches": [[835, 836], [843, 848], [848, 830], [848, 849]]}
# gained: {"lines": [836, 848, 849, 850, 851], "branches": [[835, 836], [843, 848], [848, 849]]}

import base64
import os
from types import SimpleNamespace

import pytest


def _make_coder(supports_vision=False, supports_pdf_input=False, name="model"):
    import aider.coders.base_coder as base_coder

    # Create instance without calling __init__
    coder = object.__new__(base_coder.Coder)
    coder.main_model = SimpleNamespace(
        info={"supports_vision": supports_vision, "supports_pdf_input": supports_pdf_input},
        name=name,
    )
    return coder


def test_get_images_message_skips_file_with_no_mime(tmp_path, monkeypatch):
    """
    Ensure that when mimetypes.guess_type returns no mime type (None),
    the code hits the 'continue' at the branch that skips files with no mime
    and ultimately returns None.
    """
    # Create a file with an uncommon extension so guess_type would normally be None
    fname = tmp_path / "file.unknownext"
    data = b"not an image"
    fname.write_bytes(data)

    import aider.coders.base_coder as base_coder

    # Force is_image_file to True so the file is considered for processing
    monkeypatch.setattr(base_coder, "is_image_file", lambda f: True)

    # Ensure mimetypes.guess_type returns (None, None) for this specific file
    original_guess = base_coder.mimetypes.guess_type

    def fake_guess(path, strict=True):
        if str(path).endswith(".unknownext"):
            return (None, None)
        return original_guess(path, strict)

    monkeypatch.setattr(base_coder.mimetypes, "guess_type", fake_guess)

    coder = _make_coder(supports_vision=True, supports_pdf_input=False)
    # Provide a safe get_rel_fname although it should not be called in this case
    coder.get_rel_fname = lambda p: os.path.basename(p)

    result = base_coder.Coder.get_images_message(coder, [str(fname)])
    # Because mime_type is None, the file is skipped and the result should be None
    assert result is None


def test_get_images_message_handles_pdf_branch(tmp_path, monkeypatch):
    """
    Ensure that a PDF file produces the PDF branch (application/pdf),
    returning the expected structure where image_url is a data URL string.
    """
    # Create a small PDF-like file (content can be arbitrary bytes)
    fname = tmp_path / "doc.pdf"
    pdf_bytes = b"%PDF-1.4\n%Fake PDF content\n"
    fname.write_bytes(pdf_bytes)

    import aider.coders.base_coder as base_coder

    # Force is_image_file to True so the file is processed
    monkeypatch.setattr(base_coder, "is_image_file", lambda f: True)

    # Ensure mimetypes.guess_type returns application/pdf for our file
    monkeypatch.setattr(base_coder.mimetypes, "guess_type", lambda p, strict=True: ("application/pdf", None))

    coder = _make_coder(supports_vision=False, supports_pdf_input=True)
    coder.get_rel_fname = lambda p: f"rel/{os.path.basename(p)}"

    result = base_coder.Coder.get_images_message(coder, [str(fname)])
    assert isinstance(result, dict)
    assert result["role"] == "user"
    content = result["content"]
    # Expect two messages: text and image_url
    assert isinstance(content, list) and len(content) == 2

    text_msg = content[0]
    image_msg = content[1]

    assert text_msg == {"type": "text", "text": f"PDF file: {coder.get_rel_fname(str(fname))}"}

    # Compute expected base64 data URL
    expected_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    expected_url = f"data:application/pdf;base64,{expected_b64}"

    assert image_msg == {"type": "image_url", "image_url": expected_url}
