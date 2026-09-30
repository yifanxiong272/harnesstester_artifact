import importlib
from pathlib import Path


def _patch_message_types(module, monkeypatch):
    # Minimal stand-ins for the message and content classes used by the function under test.
    class ContentPartTextParam:
        def __init__(self, text):
            self.text = text

        def __repr__(self):
            return f"ContentPartTextParam(text={self.text!r})"

    class ImageURL:
        def __init__(self, url, media_type):
            self.url = url
            self.media_type = media_type

        def __repr__(self):
            return f"ImageURL(url={self.url!r}, media_type={self.media_type!r})"

    class ContentPartImageParam:
        def __init__(self, image_url):
            self.image_url = image_url

        def __repr__(self):
            return f"ContentPartImageParam(image_url={self.image_url!r})"

    class SystemMessage:
        def __init__(self, content):
            self.content = content

        def __repr__(self):
            return f"SystemMessage(content={self.content!r})"

    class UserMessage:
        def __init__(self, content):
            # content is expected to be list[ContentPartTextParam | ContentPartImageParam]
            self.content = content

        def __repr__(self):
            return f"UserMessage(content={self.content!r})"

    monkeypatch.setattr(module, "ContentPartTextParam", ContentPartTextParam)
    monkeypatch.setattr(module, "ImageURL", ImageURL)
    monkeypatch.setattr(module, "ContentPartImageParam", ContentPartImageParam)
    monkeypatch.setattr(module, "SystemMessage", SystemMessage)
    monkeypatch.setattr(module, "UserMessage", UserMessage)


def test_include_images_and_ground_truth_round_106(monkeypatch):
    """
    - Exercise the branch where use_vision is True and ground_truth is provided.
    - _encode_image returns a truthy value for some images and falsy for others -> only truthy encoded images are attached.
    - _truncate_text is called for task, final_result and joined steps.
    - datetime.now is patched for deterministic current_date interpolation in the system prompt.
    """
    judge = importlib.import_module("browser_use.agent.judge")

    # Patch message/content types to simple inspection-friendly classes
    _patch_message_types(judge, monkeypatch)

    # Track calls to truncate and provide predictable truncated results
    truncate_calls = []

    def fake_truncate(text, max_length, from_beginning=False):
        truncate_calls.append((text, max_length, from_beginning))
        # make truncated form obvious in the built prompts
        return "TRUNC:" + text

    monkeypatch.setattr(judge, "_truncate_text", fake_truncate)

    # _encode_image: return non-empty for paths containing 'ok', empty otherwise
    def fake_encode(path):
        name = Path(path).name
        if "ok" in name:
            return "ENCODED-" + name
        return ""  # falsy -> should be skipped

    monkeypatch.setattr(judge, "_encode_image", fake_encode)

    # Patch datetime to fixed deterministic value used in system prompt
    class DummyDateTime:
        @staticmethod
        def now(tz):
            from datetime import datetime, timezone

            return datetime(2020, 1, 2, 3, 4, tzinfo=timezone.utc)

    monkeypatch.setattr(judge, "datetime", DummyDateTime)

    # Prepare inputs
    task = "My test task"
    final_result = "Final answer"
    steps = ["Step A: did X", "Step B: did Y"]
    screenshots = ["/tmp/img_ok.png", "/tmp/img_bad.png"]

    msgs = judge.construct_judge_messages(
        task=task,
        final_result=final_result,
        agent_steps=steps,
        screenshot_paths=screenshots,
        max_images=10,
        ground_truth="EXPECTED_GROUND_TRUTH",
        use_vision=True,
    )

    # Expect exactly two messages: SystemMessage and UserMessage
    assert isinstance(msgs, list) and len(msgs) == 2
    system_msg, user_msg = msgs

    # System prompt must include the ground-truth section and the deterministic current date
    assert isinstance(system_msg, judge.SystemMessage)
    assert "GROUND TRUTH VALIDATION" in system_msg.content
    assert "2020-01-02 03:04 UTC" in system_msg.content

    # User message content: first element is ContentPartTextParam and contains our truncated values
    assert isinstance(user_msg, judge.UserMessage)
    assert isinstance(user_msg.content, list)
    assert len(user_msg.content) >= 1
    text_part = user_msg.content[0]
    assert isinstance(text_part, judge.ContentPartTextParam)
    # _truncate_text prepended 'TRUNC:' so user prompt should reflect that
    assert "TRUNC:My test task" in text_part.text
    assert "TRUNC:Final answer" in text_part.text

    # Only the 'ok' screenshot should be encoded and attached
    image_parts = [p for p in user_msg.content if isinstance(p, judge.ContentPartImageParam)]
    assert len(image_parts) == 1
    img_url = image_parts[0].image_url
    assert img_url.url.startswith("data:image/png;base64,ENCODED-img_ok.png")

    # Verify that _truncate_text was called for task, final_result and the joined steps
    assert any(call[0] == task for call in truncate_calls)
    assert any(call[0] == final_result for call in truncate_calls)
    # joined steps_text contains 'Step A' therefore one call should include it
    assert any("Step A" in call[0] or "Step B" in call[0] for call in truncate_calls)


def test_disable_vision_and_truncate_round_106(monkeypatch):
    """
    - Exercise the branch where use_vision is False; ensure no image encoding happens and encoded images list remains empty.
    - ground_truth is None so ground truth sections must be omitted.
    - Verify the user prompt reflects zero screenshots attached.
    """
    judge = importlib.import_module("browser_use.agent.judge")

    # Patch message/content types
    _patch_message_types(judge, monkeypatch)

    # Make _truncate_text identity to keep prompts readable
    monkeypatch.setattr(judge, "_truncate_text", lambda text, max_length, from_beginning=False: text)

    # If the code tries to call _encode_image when use_vision is False, fail the test
    def failing_encode(path):
        raise AssertionError("_encode_image should not be called when use_vision is False")

    monkeypatch.setattr(judge, "_encode_image", failing_encode)

    # Prepare inputs with more screenshots than max_images to exercise selection logic path (even though skipped)
    task = "T"
    final_result = "R"
    steps = ["only step"]
    screenshots = ["one.png", "two.png"]

    msgs = judge.construct_judge_messages(
        task=task,
        final_result=final_result,
        agent_steps=steps,
        screenshot_paths=screenshots,
        max_images=1,
        ground_truth=None,
        use_vision=False,
    )

    assert isinstance(msgs, list) and len(msgs) == 2
    system_msg, user_msg = msgs

    # No ground truth section should be present
    assert "GROUND TRUTH VALIDATION" not in system_msg.content

    # User prompt should mention 0 screenshots attached because vision disabled -> encoded_images empty
    assert isinstance(user_msg.content[0], judge.ContentPartTextParam)
    assert "0 screenshots from execution are attached" in user_msg.content[0].text

    # No image parts attached
    image_parts = [p for p in user_msg.content if isinstance(p, judge.ContentPartImageParam)]
    assert len(image_parts) == 0
