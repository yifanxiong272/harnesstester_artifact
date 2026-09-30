import os
import types
import pytest

import aider.commands as commands


class DummyIO:
    def __init__(self):
        self.errors = []
        self.placeholder = None

    def tool_error(self, msg):
        # preserve exact call shape used by Commands.cmd_voice
        self.errors.append(msg)


def make_instance():
    # create a minimal object that can be used as `self` for Commands.cmd_voice
    inst = types.SimpleNamespace()
    inst.voice = None
    inst.voice_format = None
    inst.voice_input_device = None
    inst.voice_language = None
    inst.io = DummyIO()
    return inst


def test_no_api_key_round_079(monkeypatch):
    # Ensure OPENAI_API_KEY is not present and that cmd_voice reports the expected tool error
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    inst = make_instance()

    # Call the unbound method with our simple instance
    result = commands.Commands.cmd_voice(inst, None)

    assert result is None
    assert inst.voice is None
    # Exact message asserted from source
    assert inst.io.errors == ["To use /voice you must provide an OpenAI API key."]
    assert inst.io.placeholder is None


def test_sound_device_error_round_079(monkeypatch):
    # When OPENAI_API_KEY is present but voice.Voice raises SoundDeviceError,
    # cmd_voice should call io.tool_error with the portaudio message and return.
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-key")

    # Patch Voice to raise the SoundDeviceError from the voice module where commands resolves it
    def raise_sound(*a, **kw):
        raise commands.voice.SoundDeviceError()

    monkeypatch.setattr(commands.voice, "Voice", raise_sound, raising=True)

    inst = make_instance()

    result = commands.Commands.cmd_voice(inst, None)

    assert result is None
    assert inst.voice is None
    # Message must match the one in the source exactly
    assert inst.io.errors == [
        "Unable to import `sounddevice` and/or `soundfile`, is portaudio installed?"
    ]
    assert inst.io.placeholder is None


def test_openai_error_from_transcription_round_079(monkeypatch):
    # When Voice constructed successfully but record_and_transcribe raises litellm.OpenAIError,
    # cmd_voice should surface a helpful tool_error with the exception message.
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-key")

    class FakeVoiceRaise:
        def __init__(self, *a, **kw):
            pass

        def record_and_transcribe(self, *a, **kw):
            raise commands.litellm.OpenAIError("boom")

    monkeypatch.setattr(commands.voice, "Voice", FakeVoiceRaise, raising=True)

    inst = make_instance()

    result = commands.Commands.cmd_voice(inst, None)

    assert result is None
    # voice should have been assigned to the fake instance
    assert isinstance(inst.voice, FakeVoiceRaise)
    # Error message should include the original exception text
    assert inst.io.errors == ["Unable to use OpenAI whisper model: boom"]
    assert inst.io.placeholder is None


def test_successful_transcription_sets_placeholder_round_079(monkeypatch):
    # When record_and_transcribe returns non-empty text, io.placeholder must be set to that text
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-key")

    class FakeVoiceOk:
        def __init__(self, *a, **kw):
            pass

        def record_and_transcribe(self, *a, **kw):
            return "hello world"

    monkeypatch.setattr(commands.voice, "Voice", FakeVoiceOk, raising=True)

    inst = make_instance()

    result = commands.Commands.cmd_voice(inst, None)

    assert result is None
    assert isinstance(inst.voice, FakeVoiceOk)
    assert inst.io.errors == []
    assert inst.io.placeholder == "hello world"


def test_empty_transcription_does_not_set_placeholder_round_079(monkeypatch):
    # If record_and_transcribe returns empty/falsey value, placeholder should remain None
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-key")

    class FakeVoiceEmpty:
        def __init__(self, *a, **kw):
            pass

        def record_and_transcribe(self, *a, **kw):
            return ""  # falsey -> should not set placeholder

    monkeypatch.setattr(commands.voice, "Voice", FakeVoiceEmpty, raising=True)

    inst = make_instance()

    result = commands.Commands.cmd_voice(inst, None)

    assert result is None
    assert isinstance(inst.voice, FakeVoiceEmpty)
    assert inst.io.errors == []
    assert inst.io.placeholder is None
