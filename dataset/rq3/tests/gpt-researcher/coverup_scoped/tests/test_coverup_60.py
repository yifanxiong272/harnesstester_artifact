# file: gpt_researcher/llm_provider/image/image_generator.py:156-223
# asked: {"lines": [168, 170, 182, 183, 192, 199, 201, 203, 220, 221, 223], "branches": [[168, 170], [168, 182], [182, 183], [182, 192], [220, 221], [220, 223]]}
# gained: {"lines": [168, 170, 182, 183, 192, 199, 201, 203, 220, 221, 223], "branches": [[168, 170], [168, 182], [182, 183], [182, 192], [220, 221], [220, 223]]}

import string
import random

import pytest

from gpt_researcher.llm_provider.image.image_generator import ImageGeneratorProvider


def test_build_enhanced_prompt_dark_no_context():
    provider = ImageGeneratorProvider()
    prompt = "A futuristic data visualization of AI research trends"
    styled = provider._build_enhanced_prompt(prompt=prompt, context="", style="dark")

    # Basic expected pieces
    assert "SUBJECT: A futuristic data visualization of AI research trends" in styled
    # Dark style header should be present
    assert "STYLE REQUIREMENTS - DARK MODE THEME" in styled or "DARK MODE" in styled.upper()
    # Technical requirements snippet included
    assert "TECHNICAL REQUIREMENTS" in styled
    # No research context should be present when context is empty
    assert "RESEARCH CONTEXT:" not in styled


def test_build_enhanced_prompt_light_with_context_truncation():
    provider = ImageGeneratorProvider()
    prompt = "An infographic summarizing recent experiments"
    # Create a long context (>300 chars)
    long_context = "".join(random.choices(string.ascii_letters + " ", k=350))
    styled = provider._build_enhanced_prompt(prompt=prompt, context=long_context, style="light")

    # Subject/prompt present
    assert "SUBJECT: An infographic summarizing recent experiments" in styled
    # Light style header should be present
    assert "STYLE REQUIREMENTS - LIGHT MODE" in styled or "LIGHT MODE" in styled.upper()
    # Research context appended and truncated to 300 characters
    assert "RESEARCH CONTEXT:" in styled
    # Extract what was appended after the label and compare to first 300 chars of context
    appended = styled.split("RESEARCH CONTEXT: ", 1)[1]
    assert appended == long_context[:300]


def test_build_enhanced_prompt_other_style_includes_professional():
    provider = ImageGeneratorProvider()
    prompt = "A polished diagram of neural network architecture"
    # Use a style that triggers the else branch
    styled = provider._build_enhanced_prompt(prompt=prompt, context="some context", style="auto")

    # Subject/prompt present
    assert "SUBJECT: A polished diagram of neural network architecture" in styled
    # "PROFESSIONAL" style header should be present for non-dark/non-light
    assert "STYLE REQUIREMENTS - PROFESSIONAL" in styled or "PROFESSIONAL" in styled.upper()
    # Context included and not longer than 300 chars
    assert "RESEARCH CONTEXT: some context" in styled
