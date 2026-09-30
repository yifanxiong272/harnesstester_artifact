# file: browser_use/filesystem/file_system.py:506-713
# asked: {"lines": [520, 521, 522, 524, 531, 533, 534, 535, 536, 547, 549, 550, 551, 554, 555, 556, 557, 558, 559, 562, 563, 564, 565, 566, 567, 568, 569, 570, 572, 575, 576, 579, 580, 582, 584, 585, 586, 587, 588, 589, 593, 594, 595, 596, 597, 599, 600, 603, 604, 605, 606, 607, 610, 611, 612, 615, 616, 617, 620, 621, 622, 623, 624, 625, 626, 628, 629, 630, 631, 632, 634, 635, 636, 637, 638, 639, 642, 643, 645, 646, 647, 648, 649, 650, 654, 656, 657, 658, 660, 676, 677, 683, 684, 708, 709, 710, 711, 712, 713], "branches": [[530, 531], [546, 547], [556, 557], [556, 562], [562, 563], [562, 575], [564, 565], [564, 567], [565, 564], [565, 566], [582, 584], [582, 593], [586, 582], [586, 587], [587, 588], [587, 589], [594, 595], [594, 603], [596, 597], [596, 600], [605, 606], [605, 610], [606, 605], [606, 607], [610, 611], [610, 615], [611, 610], [611, 612], [620, 621], [620, 642], [622, 623], [622, 624], [629, 630], [629, 631], [632, 634], [632, 635], [638, 620], [638, 639], [646, 647], [646, 654], [662, 676]]}
# gained: {"lines": [520, 521, 522, 524, 531, 533, 534, 535, 536, 547, 549, 550, 551, 554, 555, 556, 557, 558, 559, 562, 563, 564, 565, 566, 567, 568, 569, 570, 572, 575, 576, 579, 580, 582, 584, 585, 586, 587, 588, 589, 593, 594, 595, 596, 597, 599, 600, 603, 604, 605, 606, 607, 610, 611, 615, 616, 617, 620, 621, 622, 624, 625, 626, 628, 629, 631, 632, 634, 635, 636, 637, 638, 639, 642, 643, 645, 646, 647, 648, 649, 650, 656, 657, 658, 660, 676, 677, 683, 684, 708, 709, 710, 711, 712, 713], "branches": [[530, 531], [546, 547], [556, 557], [556, 562], [562, 563], [562, 575], [564, 565], [564, 567], [565, 566], [582, 584], [582, 593], [586, 582], [586, 587], [587, 588], [587, 589], [594, 595], [594, 603], [596, 597], [596, 600], [605, 606], [605, 610], [606, 605], [606, 607], [610, 611], [610, 615], [611, 610], [620, 621], [622, 624], [629, 631], [632, 634], [632, 635], [638, 620], [638, 639], [646, 647], [662, 676]]}

import asyncio
import base64
import builtins
import os
import sys
from types import SimpleNamespace

import pytest

from browser_use.filesystem.file_system import FileSystem, FileSystemError


# Helpers for fake anyio
class _FakeAnyIOFile:
    def __init__(self, path, mode, binary=False):
        self.path = path
        self.mode = mode
        self._binary = binary
        self._fh = None

    async def __aenter__(self):
        # open synchronously but return object whose read is async
        self._fh = builtins.open(self.path, self.mode)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._fh:
            try:
                self._fh.close()
            except Exception:
                pass

    async def read(self):
        data = self._fh.read()
        if self._binary:
            # if file opened in binary mode, ensure bytes
            return data
        else:
            return data


async def _anyio_open_file_for_text(path, mode):
    return _FakeAnyIOFile(path, mode, binary='b' in mode)


async def _anyio_open_file_for_bytes(path, mode):
    return _FakeAnyIOFile(path, mode, binary='b' in mode)


# Fake docx module
class _FakeParagraph:
    def __init__(self, text):
        self.text = text


class _FakeDoc:
    def __init__(self, filename, paragraphs=None):
        # paragraphs is optional; if not provided, create default
        if paragraphs is None:
            paragraphs = ["p1", "p2"]
        self.paragraphs = [_FakeParagraph(t) for t in paragraphs]


# Fake pypdf
class _FakePage:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class _FakePdfReader:
    def __init__(self, filename, pages_texts):
        # pages_texts: list of strings
        self.pages = [_FakePage(t) for t in pages_texts]


@pytest.fixture(autouse=True)
def preserve_sys_modules(monkeypatch):
    # ensure each test starts with clean module entries for our fakes
    saved = {k: sys.modules.get(k) for k in ('anyio', 'docx', 'pypdf')}
    yield
    for k, v in saved.items():
        if v is None:
            if k in sys.modules:
                del sys.modules[k]
        else:
            sys.modules[k] = v


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def make_fs(tmp_path):
    # create FileSystem with no default files to keep tests isolated
    return FileSystem(tmp_path, create_default_files=False)


def test_external_invalid_filename_format(monkeypatch, tmp_path):
    fs = make_fs(tmp_path)

    # force _parse_filename to raise to hit the invalid filename branch
    async_call = run

    def bad_parse(_):
        raise Exception("bad parse")

    monkeypatch.setattr(fs, "_parse_filename", bad_parse)

    res = run(fs.read_file_structured("invalidfile", external_file=True))
    assert isinstance(res, dict)
    assert "Invalid filename format" in res["message"]
    assert res["images"] is None


def test_read_text_file_via_anyio(monkeypatch, tmp_path):
    fs = make_fs(tmp_path)

    # create a real text file
    p = tmp_path / "sample.txt"
    content = "Hello world\nLine2"
    p.write_text(content, encoding="utf-8")

    # inject fake anyio that reads the real file
    anyio_mod = SimpleNamespace(open_file=_anyio_open_file_for_text)
    monkeypatch.setitem(sys.modules, "anyio", anyio_mod)

    res = run(fs.read_file_structured(str(p), external_file=True))
    assert "Read from file" in res["message"]
    assert "<content>" in res["message"]
    assert "Hello world" in res["message"]


def test_read_docx_external(monkeypatch, tmp_path):
    fs = make_fs(tmp_path)

    # prepare fake docx module
    def FakeDocument(filename):
        # create a document with a few paragraphs
        return _FakeDoc(filename, paragraphs=["First para", "Second para"])

    docx_mod = SimpleNamespace(Document=FakeDocument)
    monkeypatch.setitem(sys.modules, "docx", docx_mod)

    # call with a .docx filename
    res = run(fs.read_file_structured("mydoc.docx", external_file=True))
    assert "Read from file mydoc.docx" in res["message"]
    assert "First para" in res["message"]
    assert "Second para" in res["message"]


def test_read_pdf_small(monkeypatch, tmp_path):
    fs = make_fs(tmp_path)

    # small PDF with two short pages
    pages = ["This is page one with some text.", "Page two has additional text."]
    # fake pypdf module such that PdfReader(filename) returns reader with pages
    def FakePdfReader(filename):
        return _FakePdfReader(filename, pages)

    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=FakePdfReader))

    res = run(fs.read_file_structured("a.pdf", external_file=True))
    assert "Read from file a.pdf" in res["message"]
    assert "--- Page 1 ---" in res["message"]
    assert "--- Page 2 ---" in res["message"]
    # ensure total chars reported (small)
    assert "chars" in res["message"]


def test_read_pdf_large_truncation(monkeypatch, tmp_path):
    fs = make_fs(tmp_path)

    # create many large pages to force > MAX_CHARS
    # Each page contains repeated distinctive words to allow scoring
    ptext = ("loremipsum " * 4000).strip()  # ~11 * 4000 = 44k chars approx
    ptext2 = ("uniquecontent " * 4000).strip()
    # Use three pages so total chars > 60000
    pages = [ptext, ptext2, ptext]

    def FakePdfReader(filename):
        return _FakePdfReader(filename, pages)

    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=FakePdfReader))

    res = run(fs.read_file_structured("big.pdf", external_file=True))
    assert "Read from file big.pdf" in res["message"]
    # For large PDF we should see pages listed and a truncation / skipped note possibly
    assert "pages" in res["message"]
    # If truncated, message should contain either '[Showing' or '<content>' (content is present)
    assert "<content>" in res["message"]


def test_read_image_anyio(monkeypatch, tmp_path):
    fs = make_fs(tmp_path)

    # create an image file (binary)
    p = tmp_path / "img.png"
    img_bytes = b"\x89PNG\r\n\x1a\n" + b"fakepngdata"
    p.write_bytes(img_bytes)

    # anyio that reads binary
    async def anyio_open(path, mode):
        return _FakeAnyIOFile(path, mode, binary=True)

    monkeypatch.setitem(sys.modules, "anyio", SimpleNamespace(open_file=anyio_open))

    res = run(fs.read_file_structured(str(p), external_file=True))
    assert res["images"] is not None and isinstance(res["images"], list)
    assert res["images"][0]["name"] == os.path.basename(str(p))
    assert res["images"][0]["data"] == base64.b64encode(img_bytes).decode("utf-8")
    assert "Read image file" in res["message"]


def test_unsupported_extension(monkeypatch, tmp_path):
    fs = make_fs(tmp_path)

    # force parse to return unsupported extension
    def parse(filename):
        return ("file", "xyz")

    monkeypatch.setattr(fs, "_parse_filename", parse)

    res = run(fs.read_file_structured("file.xyz", external_file=True))
    assert "not supported" in res["message"]


def test_external_file_not_found_permission_and_generic(monkeypatch, tmp_path):
    fs = make_fs(tmp_path)

    # Use dummy parser to return txt so it goes into anyio open
    def parse(filename):
        return ("f", "txt")

    monkeypatch.setattr(fs, "_parse_filename", parse)

    # 1) FileNotFoundError
    async def anyio_open_notfound(path, mode):
        raise FileNotFoundError()

    monkeypatch.setitem(sys.modules, "anyio", SimpleNamespace(open_file=anyio_open_notfound))
    res = run(fs.read_file_structured("f.txt", external_file=True))
    assert "not found" in res["message"].lower()

    # 2) PermissionError
    async def anyio_open_perm(path, mode):
        raise PermissionError()

    monkeypatch.setitem(sys.modules, "anyio", SimpleNamespace(open_file=anyio_open_perm))
    res2 = run(fs.read_file_structured("f.txt", external_file=True))
    assert "permission denied" in res2["message"].lower()

    # 3) Generic Exception
    async def anyio_open_bad(path, mode):
        raise RuntimeError("boom")

    monkeypatch.setitem(sys.modules, "anyio", SimpleNamespace(open_file=anyio_open_bad))
    res3 = run(fs.read_file_structured("f.txt", external_file=True))
    assert "Could not read file" in res3["message"]


def test_internal_file_read_exceptions(monkeypatch, tmp_path):
    fs = make_fs(tmp_path)

    # ensure filename resolves and is considered valid
    monkeypatch.setattr(fs, "_resolve_filename", lambda x: ("resolved.txt", False))
    monkeypatch.setattr(fs, "_is_valid_filename", lambda x: True)

    class BadFile:
        def read(self):
            raise FileSystemError("internal fs error")

    fs.files["resolved.txt"] = BadFile()
    res = run(fs.read_file_structured("resolved.txt", external_file=False))
    assert "internal fs error" in res["message"]

    class BadFile2:
        def read(self):
            raise ValueError("unexpected")

    fs.files["resolved.txt"] = BadFile2()
    res2 = run(fs.read_file_structured("resolved.txt", external_file=False))
    assert "Could not read file" in res2["message"]
    assert "unexpected" in res2["message"]
