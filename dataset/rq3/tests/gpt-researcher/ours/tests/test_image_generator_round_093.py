import pytest
from gpt_researcher.llm_provider.image import image_generator


def _make_provider():
    # __init__(self, model_name, api_key, output_dir) per source outline
    return image_generator.ImageGeneratorProvider("model", "key", "/tmp")


def test_dark_style_includes_dark_requirements_round_093():
    prov = _make_provider()
    out = prov._build_enhanced_prompt("Climate model", context="", style="dark")

    # Dark-specific header and some unique dark tokens
    assert "STYLE REQUIREMENTS - DARK MODE THEME" in out
    assert "Dark background" in out or "#0d1117" in out

    # Subject must be present
    assert "SUBJECT: Climate model" in out

    # Technical requirements block must be present
    assert "TECHNICAL REQUIREMENTS" in out

    # No research context when empty
    assert "RESEARCH CONTEXT:" not in out


def test_light_style_includes_light_requirements_round_093():
    prov = _make_provider()
    out = prov._build_enhanced_prompt("Ocean salinity", context="", style="light")

    # Light-specific header and tokens
    assert "STYLE REQUIREMENTS - LIGHT MODE" in out
    assert "Clean white or light gray background" in out or "Deep blue (#1e40af)" in out

    # Subject must be present
    assert "SUBJECT: Ocean salinity" in out

    # Technical requirements should still be present
    assert "TECHNICAL REQUIREMENTS" in out

    # No research context when empty
    assert "RESEARCH CONTEXT:" not in out


def test_auto_style_and_context_truncation_round_093():
    prov = _make_provider()

    # Build a long context > 300 chars to exercise truncation
    long_ctx = "x" * 350
    out = prov._build_enhanced_prompt("X", context=long_ctx, style="auto")

    # Professional style branch
    assert "STYLE REQUIREMENTS - PROFESSIONAL" in out

    # Research context must be appended and must be truncated to 300 chars
    assert "RESEARCH CONTEXT:" in out
    # Extract the appended context portion after the marker
    rc_part = out.split("RESEARCH CONTEXT: ", 1)[1]
    # The appended portion should start with the first 300 characters of long_ctx
    assert rc_part.startswith(long_ctx[:300])
    # It must NOT include the full original long_ctx (truncation happened)
    assert long_ctx not in out
