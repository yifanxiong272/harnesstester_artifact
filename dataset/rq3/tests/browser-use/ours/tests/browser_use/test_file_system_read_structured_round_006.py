import sys
import types
import base64
import pytest

from browser_use.filesystem.file_system import FileSystem, _build_filename_error_message

# Helpers to build fake modules used by read_file_structured
class FakeAIOFileCtx:
    def __init__(self, filename, mode, content_map, exc_map=None):
        self.filename = filename
        self.mode = mode
        self.content_map = content_map
        self.exc_map = exc_map or {}

    async def __aenter__(self):
        if self.filename in self.exc_map:
            raise self.exc_map[self.filename]
        content = self.content_map.get(self.filename)

        class Reader:
            async def read(inner_self):
                return content

        return Reader()

    async def __aexit__(self, exc_type, exc, tb):
        return False


def make_fake_anyio(content_map=None, exc_map=None):
    content_map = content_map or {}
    exc_map = exc_map or {}
    fake_anyio = types.SimpleNamespace()

    async def open_file(filename, mode='r'):
        return FakeAIOFileCtx(filename, mode, content_map, exc_map)

    fake_anyio.open_file = open_file
    return fake_anyio

class DummyParagraph:
    def __init__(self, text):
        self.text = text

class DummyDoc:
    def __init__(self, paragraphs):
        self.paragraphs = [DummyParagraph(p) for p in paragraphs]

class DummyPage:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text

class DummyPdfReader:
    def __init__(self, pages_texts):
        self.pages = [DummyPage(t) for t in pages_texts]


@pytest.mark.asyncio
async def test_invalid_filename_parse_round_006(monkeypatch, tmp_path):
    fs = FileSystem(base_dir=tmp_path, create_default_files=False)

    # make _parse_filename raise to hit the invalid filename branch
    monkeypatch.setattr(fs, '_parse_filename', lambda fn: (_ for _ in ()).throw(Exception('bad')))

    res = await fs.read_file_structured('??invalid??', external_file=True)
    assert 'Invalid filename format' in res['message']


@pytest.mark.asyncio
async def test_read_text_file_round_006(monkeypatch, tmp_path):
    fs = FileSystem(base_dir=tmp_path, create_default_files=False)
    monkeypatch.setattr(fs, '_parse_filename', lambda fn: (fn, 'txt'))
    monkeypatch.setattr(fs, '_file_types', ['txt', 'md'])
    content_map = {'sample.txt': 'Hello world from text file'}
    fake_anyio = make_fake_anyio(content_map=content_map)
    monkeypatch.setitem(sys.modules, 'anyio', fake_anyio)

    res = await fs.read_file_structured('sample.txt', external_file=True)
    assert 'Read from file sample.txt' in res['message']
    assert 'Hello world from text file' in res['message']


@pytest.mark.asyncio
async def test_read_docx_round_006(monkeypatch, tmp_path):
    fs = FileSystem(base_dir=tmp_path, create_default_files=False)
    monkeypatch.setattr(fs, '_parse_filename', lambda fn: (fn, 'docx'))

    fake_docx = types.SimpleNamespace()
    fake_docx.Document = lambda fn: DummyDoc(['First para', 'Second para'])
    monkeypatch.setitem(sys.modules, 'docx', fake_docx)

    res = await fs.read_file_structured('file.docx', external_file=True)
    assert 'Read from file file.docx' in res['message']
    assert 'First para' in res['message'] and 'Second para' in res['message']


@pytest.mark.asyncio
async def test_read_pdf_small_round_006(monkeypatch, tmp_path):
    fs = FileSystem(base_dir=tmp_path, create_default_files=False)
    monkeypatch.setattr(fs, '_parse_filename', lambda fn: (fn, 'pdf'))

    pages = ['This is page one text', 'Page two content']
    fake_pypdf = types.SimpleNamespace()
    fake_pypdf.PdfReader = lambda fn: DummyPdfReader(pages)
    monkeypatch.setitem(sys.modules, 'pypdf', fake_pypdf)

    res = await fs.read_file_structured('small.pdf', external_file=True)
    assert 'pages' in res['message'] or 'Page' in res['message']
    assert '--- Page 1 ---' in res['message']
    assert '--- Page 2 ---' in res['message']


@pytest.mark.asyncio
async def test_read_pdf_large_round_006(monkeypatch, tmp_path):
    fs = FileSystem(base_dir=tmp_path, create_default_files=False)
    monkeypatch.setattr(fs, '_parse_filename', lambda fn: (fn, 'pdf'))

    pages = []
    for i in range(1, 8):
        pages.append(('pagecontent ' + ('unique' + str(i) + ' ') * 2000).strip())

    fake_pypdf = types.SimpleNamespace()
    fake_pypdf.PdfReader = lambda fn: DummyPdfReader(pages)
    monkeypatch.setitem(sys.modules, 'pypdf', fake_pypdf)

    res = await fs.read_file_structured('big.pdf', external_file=True)
    assert 'Showing' in res['message'] or 'truncated' in res['message'] or 'pages' in res['message']
    assert '--- Page' in res['message']


@pytest.mark.asyncio
async def test_read_image_round_006(monkeypatch, tmp_path):
    fs = FileSystem(base_dir=tmp_path, create_default_files=False)
    monkeypatch.setattr(fs, '_parse_filename', lambda fn: (fn, 'png'))
    content_map = {'image.png': b'\x00\x01\x02'}
    fake_anyio = make_fake_anyio(content_map=content_map)
    monkeypatch.setitem(sys.modules, 'anyio', fake_anyio)

    res = await fs.read_file_structured('image.png', external_file=True)
    assert 'Read image file image.png' in res['message']
    assert res['images'] and res['images'][0]['name'] == 'image.png'
    expected_b64 = base64.b64encode(content_map['image.png']).decode('utf-8')
    assert res['images'][0]['data'] == expected_b64


@pytest.mark.asyncio
async def test_unsupported_extension_round_006(monkeypatch, tmp_path):
    fs = FileSystem(base_dir=tmp_path, create_default_files=False)
    monkeypatch.setattr(fs, '_parse_filename', lambda fn: (fn, 'exe'))
    monkeypatch.setattr(fs, '_file_types', ['txt', 'pdf', 'png'])

    res = await fs.read_file_structured('bad.exe', external_file=True)
    assert 'not supported' in res['message']


@pytest.mark.asyncio
async def test_internal_filename_invalid_round_006(monkeypatch, tmp_path):
    fs = FileSystem(base_dir=tmp_path, create_default_files=False)
    monkeypatch.setattr(fs, '_resolve_filename', lambda fn: ('resolved', False))
    monkeypatch.setattr(fs, '_is_valid_filename', lambda name: False)

    res = await fs.read_file_structured('somefile', external_file=False)
    expected = _build_filename_error_message('somefile', fs.get_allowed_extensions())
    assert res['message'] == expected


@pytest.mark.asyncio
async def test_internal_file_not_found_and_sanitized_round_006(monkeypatch, tmp_path):
    fs = FileSystem(base_dir=tmp_path, create_default_files=False)
    monkeypatch.setattr(fs, '_resolve_filename', lambda fn: ('resolved_name', True))
    monkeypatch.setattr(fs, '_is_valid_filename', lambda name: True)
    fs.files = {}

    res = await fs.read_file_structured('origname', external_file=False)
    assert "auto-corrected" in res['message']
    assert "resolved_name" in res['message']


@pytest.mark.asyncio
async def test_internal_file_read_success_with_sanitize_note_round_006(monkeypatch, tmp_path):
    fs = FileSystem(base_dir=tmp_path, create_default_files=False)
    monkeypatch.setattr(fs, '_resolve_filename', lambda fn: ('resolved_name', True))
    monkeypatch.setattr(fs, '_is_valid_filename', lambda name: True)

    class InMemoryFile:
        def read(self):
            return 'CONTENTS HERE'

    fs.files = {'resolved_name': InMemoryFile()}

    res = await fs.read_file_structured('origname', external_file=False)
    assert 'auto-corrected' in res['message']
    assert 'CONTENTS HERE' in res['message']
