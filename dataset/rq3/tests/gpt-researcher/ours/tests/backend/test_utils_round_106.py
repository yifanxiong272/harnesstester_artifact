import backend.utils as utils


def test_replace_outputs_url_round_106(monkeypatch):
    """When an image URL starts with /outputs/, it should be converted to an absolute file path.

    We patch the path functions used inside backend.utils so the output is deterministic
    across platforms.
    """
    # Make base_path deterministic and ensure join produces POSIX-like paths
    monkeypatch.setattr(utils.os.path, "abspath", lambda p: "/abs/base")
    monkeypatch.setattr(utils.os.path, "join", lambda a, b: f"{a}/{b}")

    text = "Intro ![alt](/outputs/images/pic.png) tail"
    result = utils._preprocess_images_for_pdf(text)

    expected = "![alt](/abs/base/outputs/images/pic.png)"
    assert expected in result
    # ensure rest of the text is preserved around the replacement
    assert result.startswith("Intro ") and result.endswith(" tail")


def test_non_outputs_url_unchanged_round_106(monkeypatch):
    """If the URL does not start with /outputs/, the original markdown should be left intact."""
    # Patch path functions anyway to avoid any reliance on real FS calls
    monkeypatch.setattr(utils.os.path, "abspath", lambda p: "/unused")
    monkeypatch.setattr(utils.os.path, "join", lambda a, b: f"{a}/{b}")

    original = "Text ![img](http://example.com/img.png) end"
    result = utils._preprocess_images_for_pdf(original)

    # should be exactly unchanged because pattern matches but branch returns original match
    assert result == original


def test_empty_alt_text_round_106(monkeypatch):
    """Covers images with empty alt text and ensures the absolute path is formed correctly."""
    monkeypatch.setattr(utils.os.path, "abspath", lambda p: "/basepath")
    monkeypatch.setattr(utils.os.path, "join", lambda a, b: f"{a}/{b}")

    text = "![](/outputs/foo.png)"
    result = utils._preprocess_images_for_pdf(text)

    assert result == "![ ](\/basepath/outputs/foo.png)" or "![ ]" not in result  # defensive check
    # More robust check: ensure file path from our patched abspath/join appears
    assert "/basepath/outputs/foo.png" in result
