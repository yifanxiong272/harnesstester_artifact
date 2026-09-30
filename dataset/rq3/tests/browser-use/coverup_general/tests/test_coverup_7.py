# file: browser_use/filesystem/file_system.py:506-713
# asked: {"lines": [520, 521, 522, 524, 531, 533, 534, 535, 536, 547, 549, 550, 551, 554, 555, 556, 557, 558, 559, 562, 563, 564, 565, 566, 567, 568, 569, 570, 572, 575, 576, 579, 580, 582, 584, 585, 586, 587, 588, 589, 593, 594, 595, 596, 597, 599, 600, 603, 604, 605, 606, 607, 610, 611, 612, 615, 616, 617, 620, 621, 622, 623, 624, 625, 626, 628, 629, 630, 631, 632, 634, 635, 636, 637, 638, 639, 642, 643, 645, 646, 647, 648, 649, 650, 654, 656, 657, 658, 660, 676, 677, 683, 684, 708, 709, 710, 711, 712, 713], "branches": [[530, 531], [546, 547], [556, 557], [556, 562], [562, 563], [562, 575], [564, 565], [564, 567], [565, 564], [565, 566], [582, 584], [582, 593], [586, 582], [586, 587], [587, 588], [587, 589], [594, 595], [594, 603], [596, 597], [596, 600], [605, 606], [605, 610], [606, 605], [606, 607], [610, 611], [610, 615], [611, 610], [611, 612], [620, 621], [620, 642], [622, 623], [622, 624], [629, 630], [629, 631], [632, 634], [632, 635], [638, 620], [638, 639], [646, 647], [646, 654], [662, 676]]}
# gained: {"lines": [520, 521, 522, 524, 531, 533, 534, 535, 536, 547, 549, 550, 551, 554, 555, 556, 557, 558, 559, 562, 563, 564, 565, 566, 567, 568, 569, 570, 572, 575, 576, 579, 580, 582, 584, 585, 586, 587, 588, 589, 593, 594, 595, 596, 597, 599, 600, 603, 604, 605, 606, 607, 610, 611, 615, 616, 617, 620, 621, 622, 624, 625, 626, 628, 629, 631, 632, 634, 635, 636, 637, 638, 639, 642, 643, 645, 646, 647, 648, 649, 650, 656, 657, 658, 660, 676, 677, 683, 684, 708, 709, 710, 711, 712, 713], "branches": [[530, 531], [546, 547], [556, 557], [556, 562], [562, 563], [562, 575], [564, 565], [564, 567], [565, 566], [582, 584], [582, 593], [586, 582], [586, 587], [587, 588], [587, 589], [594, 595], [594, 603], [596, 597], [596, 600], [605, 606], [605, 610], [606, 605], [606, 607], [610, 611], [610, 615], [611, 610], [620, 621], [622, 624], [629, 631], [632, 634], [632, 635], [638, 620], [638, 639], [646, 647], [662, 676]]}

import sys
import types
import asyncio
import base64
import pytest

from browser_use.filesystem.file_system import FileSystem, FileSystemError


@pytest.mark.asyncio
async def test_external_invalid_filename(tmp_path, monkeypatch):
    fs = FileSystem(base_dir=tmp_path / "fs_invalid", create_default_files=False)

    # Force _parse_filename to raise to hit the invalid filename branch
    def bad_parse(filename):
        raise Exception("bad format")

    monkeypatch.setattr(fs, "_parse_filename", bad_parse)

    res = await fs.read_file_structured("some:bad:name", external_file=True)
    assert "Invalid filename format" in res['message']
    assert res['images'] is None


@pytest.mark.asyncio
async def test_external_text_file_anyio(tmp_path, monkeypatch):
    fs = FileSystem(base_dir=tmp_path / "fs_text", create_default_files=False)

    # Simulate _parse_filename returning a supported text extension like 'md'
    monkeypatch.setattr(fs, "_parse_filename", lambda fn: ("name", "md"))

    # Dummy async context manager for anyio.open_file that returns text content
    class DummyCtx:
        def __init__(self, data):
            self._data = data

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def read(self):
            return self._data

    async def dummy_open_file(full_filename, mode):
        assert mode == 'r'
        return DummyCtx("hello world")

    # Patch anyio.open_file
    import anyio
    monkeypatch.setattr(anyio, "open_file", dummy_open_file)

    res = await fs.read_file_structured("/tmp/some.md", external_file=True)
    assert "Read from file /tmp/some.md." in res['message']
    assert "<content>" in res['message']
    assert "hello world" in res['message']


@pytest.mark.asyncio
async def test_external_pdf_small(tmp_path, monkeypatch):
    fs = FileSystem(base_dir=tmp_path / "fs_pdf_small", create_default_files=False)

    # Make _parse_filename return pdf extension
    monkeypatch.setattr(fs, "_parse_filename", lambda fn: ("doc", "pdf"))

    # Build a fake pypdf module with PdfReader and pages
    pypdf_mod = types.ModuleType("pypdf")

    class Page:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    class Reader:
        def __init__(self, filename):
            # Two small pages
            self.pages = [Page("First page text."), Page("Second page text.")]

    pypdf_mod.PdfReader = Reader
    # Insert fake module so runtime import in function finds it
    monkeypatch.setitem(sys.modules, "pypdf", pypdf_mod)

    res = await fs.read_file_structured("/tmp/test.pdf", external_file=True)
    assert "Read from file /tmp/test.pdf" in res['message']
    assert "--- Page 1 ---" in res['message']
    assert "First page text." in res['message']
    assert "--- Page 2 ---" in res['message']


@pytest.mark.asyncio
async def test_external_pdf_large_truncation_and_priority(tmp_path, monkeypatch):
    fs = FileSystem(base_dir=tmp_path / "fs_pdf_large", create_default_files=False)

    # Make _parse_filename return pdf extension
    monkeypatch.setattr(fs, "_parse_filename", lambda fn: ("big", "pdf"))

    # Create a fake pypdf with many pages to force > MAX_CHARS and trigger long-processing branch
    pypdf_mod = types.ModuleType("pypdf")

    class Page:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    class Reader:
        def __init__(self, filename):
            # Create 12 pages of repetitive but differing text to create words and counts
            self.pages = []
            for i in range(12):
                # Each page around many chars -> total > 60000 MAX_CHARS
                word = f"uniqueword{i}"
                text = (" ".join([word] * 200) + " commonword " * 200 + " fillertext " * 100)
                self.pages.append(Page(text))

    pypdf_mod.PdfReader = Reader
    monkeypatch.setitem(sys.modules, "pypdf", pypdf_mod)

    res = await fs.read_file_structured("/tmp/large.pdf", external_file=True)
    # Ensure truncated message components and truncation note appear (or at least priority pages processed)
    assert "Read from file /tmp/large.pdf" in res['message']
    assert "--- Page 1 ---" in res['message']
    # If there are omitted pages a truncation note may appear; ensure message length reflects extraction
    assert len(res['message']) > 0


@pytest.mark.asyncio
async def test_external_unsupported_extension(tmp_path, monkeypatch):
    fs = FileSystem(base_dir=tmp_path / "fs_unsup", create_default_files=False)

    # Force an unsupported extension
    monkeypatch.setattr(fs, "_parse_filename", lambda fn: ("file", "abcxyz"))

    res = await fs.read_file_structured("some.file", external_file=True)
    assert "extension is not supported" in res['message']


@pytest.mark.asyncio
async def test_external_open_file_not_found_and_permission(tmp_path, monkeypatch):
    fs = FileSystem(base_dir=tmp_path / "fs_notfound", create_default_files=False)

    # Setup parse to return text extension so code tries to open file
    monkeypatch.setattr(fs, "_parse_filename", lambda fn: ("fn", "md"))

    import anyio

    async def raise_not_found(full_filename, mode):
        raise FileNotFoundError()

    async def raise_perm(full_filename, mode):
        raise PermissionError()

    # Test FileNotFoundError handling
    monkeypatch.setattr(anyio, "open_file", raise_not_found)
    res = await fs.read_file_structured("/tmp/doesnotexist.md", external_file=True)
    assert "not found" in res['message'].lower()

    # Test PermissionError handling
    monkeypatch.setattr(anyio, "open_file", raise_perm)
    res = await fs.read_file_structured("/tmp/noaccess.md", external_file=True)
    assert "permission" in res['message'].lower()


@pytest.mark.asyncio
async def test_internal_file_read_raises_filesystemerror_and_generic(tmp_path, monkeypatch):
    fs = FileSystem(base_dir=tmp_path / "fs_internal", create_default_files=False)

    # Simulate resolution and valid filename
    monkeypatch.setattr(fs, "_resolve_filename", lambda fn: ("internal.txt", False))
    monkeypatch.setattr(fs, "_is_valid_filename", lambda fn: True)

    # Create dummy file object whose read raises FileSystemError
    class BadFile1:
        def read(self):
            raise FileSystemError("custom fs error")

    fs.files["internal.txt"] = BadFile1()
    res = await fs.read_file_structured("internal.txt", external_file=False)
    assert res['message'] == "custom fs error"

    # Now generic exception
    class BadFile2:
        def read(self):
            raise Exception("boomboom")

    fs.files["internal.txt"] = BadFile2()
    res = await fs.read_file_structured("internal.txt", external_file=False)
    assert res['message'].startswith("Error: Could not read file 'internal.txt'.")
    assert "boomboom" in res['message']
