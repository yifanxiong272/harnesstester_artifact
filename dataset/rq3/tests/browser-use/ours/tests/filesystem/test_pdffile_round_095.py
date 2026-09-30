import sys
import types
from pathlib import Path
import pytest

from browser_use.filesystem.file_system import PdfFile, FileSystemError


def _install_fake_reportlab(build_side_effect=None):
    """Install fake reportlab submodules into sys.modules.

    Returns previous sys.modules snapshot and the fake platypus module.
    """
    keys = [
        "reportlab",
        "reportlab.lib",
        "reportlab.lib.pagesizes",
        "reportlab.lib.styles",
        "reportlab.platypus",
    ]
    prev = {k: sys.modules.get(k) for k in keys}

    reportlab = types.ModuleType("reportlab")
    lib = types.ModuleType("reportlab.lib")
    pagesizes = types.ModuleType("reportlab.lib.pagesizes")
    styles_mod = types.ModuleType("reportlab.lib.styles")
    platypus = types.ModuleType("reportlab.platypus")

    pagesizes.letter = (612, 792)

    def getSampleStyleSheet():
        return {
            "Title": "STYLE_TITLE",
            "Heading1": "STYLE_H1",
            "Heading2": "STYLE_H2",
            "Normal": "STYLE_NORMAL",
        }

    styles_mod.getSampleStyleSheet = getSampleStyleSheet

    class Paragraph:
        def __init__(self, text, style):
            self.text = text
            self.style = style

        def __repr__(self):
            return f"<Paragraph text={self.text!r} style={self.style!r}>"

    class Spacer:
        def __init__(self, a, b):
            self.a = a
            self.b = b

        def __repr__(self):
            return f"<Spacer {self.a},{self.b}>"

    def _make_SimpleDocTemplate():
        class SimpleDocTemplate:
            def __init__(self, filename, pagesize=None):
                self.filename = filename
                self.pagesize = pagesize
                self.built_story = None

            def build(self, story):
                if build_side_effect is not None:
                    if isinstance(build_side_effect, Exception):
                        raise build_side_effect
                    if callable(build_side_effect):
                        return build_side_effect(story)
                self.built_story = list(story)
                platypus.last_doc = self

        return SimpleDocTemplate

    platypus.Paragraph = Paragraph
    platypus.Spacer = Spacer
    platypus.SimpleDocTemplate = _make_SimpleDocTemplate()
    platypus.last_doc = None

    sys.modules["reportlab"] = reportlab
    sys.modules["reportlab.lib"] = lib
    sys.modules["reportlab.lib.pagesizes"] = pagesizes
    sys.modules["reportlab.lib.styles"] = styles_mod
    sys.modules["reportlab.platypus"] = platypus

    return prev, platypus


def _restore_sys_modules(prev):
    for k, v in prev.items():
        if v is None:
            if k in sys.modules:
                del sys.modules[k]
        else:
            sys.modules[k] = v


def test_pdffile_sync_to_disk_sync_success_round_095(tmp_path):
    # Arrange: install fake reportlab that records the built story
    prev, platypus = _install_fake_reportlab()
    try:
        # Provide required pydantic fields: name and content
        p = PdfFile(name="test", content="# MyTitle\n\n## Sub\n### Subsub\nA normal line")

        # Act
        p.sync_to_disk_sync(Path(tmp_path))

        # Assert: extension property
        assert p.extension == "pdf"

        # Assert: SimpleDocTemplate was created and built
        assert platypus.last_doc is not None
        expected_filename = str(Path(tmp_path) / p.full_name)
        assert platypus.last_doc.filename == expected_filename

        story = platypus.last_doc.built_story
        # Expect: Title paragraph, Spacer (for blank line), Heading1, Heading2, Normal
        assert len(story) == 5
        assert getattr(story[0], "text", None) == "MyTitle"
        assert story[0].style == "STYLE_TITLE"
        assert hasattr(story[1], "a") and hasattr(story[1], "b")
        assert story[2].text == "Sub" and story[2].style == "STYLE_H1"
        assert story[3].text == "Subsub" and story[3].style == "STYLE_H2"
        assert story[4].text == "A normal line" and story[4].style == "STYLE_NORMAL"
    finally:
        _restore_sys_modules(prev)


def test_pdffile_sync_to_disk_sync_error_round_095(tmp_path):
    # Arrange: install fake reportlab where build raises an exception
    prev, platypus = _install_fake_reportlab(build_side_effect=Exception("boom"))
    try:
        p = PdfFile(name="error", content="Some content")

        # Act & Assert: should wrap underlying exception in FileSystemError
        with pytest.raises(FileSystemError) as excinfo:
            p.sync_to_disk_sync(Path(tmp_path))

        msg = str(excinfo.value)
        # full_name should reflect the provided name plus extension
        assert "error.pdf" in msg
        assert "boom" in msg
    finally:
        _restore_sys_modules(prev)
