# file: aider/commands.py:1234-1258
# asked: {"lines": [1237, 1238, 1239, 1240, 1241, 1242, 1243, 1245, 1246, 1247, 1249, 1251, 1252, 1253, 1254, 1255, 1257, 1258], "branches": [[1237, 1238], [1237, 1251], [1238, 1239], [1238, 1241], [1257, 0], [1257, 1258]]}
# gained: {"lines": [1237, 1238, 1239, 1240, 1241, 1242, 1243, 1245, 1246, 1247, 1249, 1251, 1252, 1253, 1254, 1255, 1257, 1258], "branches": [[1237, 1238], [1237, 1251], [1238, 1239], [1238, 1241], [1257, 1258]]}

import types
import pytest
import aider.commands as commands_module
from aider.commands import Commands


class DummyIO:
    def __init__(self):
        self.errors = []
        self.placeholder = None

    def tool_error(self, msg):
        self.errors.append(msg)


def make_commands(io=None, **kwargs):
    return Commands(io=io or DummyIO(), coder=None, **kwargs)


def test_cmd_voice_no_api_key_calls_tool_error(monkeypatch):
    # Ensure OPENAI_API_KEY is not in env
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    io = DummyIO()
    cmd = make_commands(io=io)
    # Ensure no voice configured
    cmd.voice = None

    cmd.cmd_voice(args=None)

    assert any("To use /voice you must provide an OpenAI API key." in e for e in io.errors)
    assert cmd.voice is None
    assert io.placeholder is None


def test_cmd_voice_sounddevice_error(monkeypatch):
    # Provide OPENAI_API_KEY so initialization is attempted
    monkeypatch.setenv("OPENAI_API_KEY", "x")

    # Create a mock SoundDeviceError and Voice that raises it on init
    class MockSoundDeviceError(Exception):
        pass

    class VoiceRaiser:
        def __init__(self, audio_format=None, device_name=None):
            raise MockSoundDeviceError()

    mock_voice_module = types.SimpleNamespace(Voice=VoiceRaiser, SoundDeviceError=MockSoundDeviceError)
    monkeypatch.setattr(commands_module, "voice", mock_voice_module)

    io = DummyIO()
    cmd = make_commands(io=io)
    cmd.voice = None

    cmd.cmd_voice(args=None)

    assert any("Unable to import `sounddevice` and/or `soundfile`, is portaudio installed?" in e for e in io.errors)
    assert cmd.voice is None
    assert io.placeholder is None


def test_cmd_voice_success_sets_placeholder(monkeypatch):
    # Provide OPENAI_API_KEY so initialization is attempted
    monkeypatch.setenv("OPENAI_API_KEY", "x")

    # Mock Voice that records and transcribes successfully
    class MockVoice:
        def __init__(self, audio_format=None, device_name=None):
            self.audio_format = audio_format
            self.device_name = device_name
            self.record_and_transcribe_called = False

        def record_and_transcribe(self, *args, **kwargs):
            self.record_and_transcribe_called = True
            # verify that language kwarg is accepted (default None)
            return "transcribed text"

    mock_voice_module = types.SimpleNamespace(Voice=MockVoice, SoundDeviceError=Exception)
    monkeypatch.setattr(commands_module, "voice", mock_voice_module)

    # Ensure litellm.OpenAIError exists but not used here
    class DummyOpenAIError(Exception):
        pass

    mock_litellm = types.SimpleNamespace(OpenAIError=DummyOpenAIError)
    monkeypatch.setattr(commands_module, "litellm", mock_litellm)

    io = DummyIO()
    cmd = make_commands(io=io)
    cmd.voice = None
    # leave voice_language as default (None)

    cmd.cmd_voice(args=None)

    # After successful transcription, placeholder must be set
    assert io.placeholder == "transcribed text"
    # The voice instance should now be stored on the Commands instance
    assert isinstance(cmd.voice, MockVoice)
    assert cmd.voice.record_and_transcribe_called


def test_cmd_voice_existing_voice_openai_error(monkeypatch):
    # Ensure OPENAI_API_KEY handling is irrelevant since voice already set
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    # Create a mock OpenAIError
    class MockOpenAIError(Exception):
        pass

    # Mock litellm.OpenAIError and set it to be raised by record_and_transcribe
    mock_litellm = types.SimpleNamespace(OpenAIError=MockOpenAIError)
    monkeypatch.setattr(commands_module, "litellm", mock_litellm)

    class VoiceThatFails:
        def record_and_transcribe(self, *args, **kwargs):
            raise MockOpenAIError("something went wrong")

    io = DummyIO()
    cmd = make_commands(io=io)
    # Pre-populate voice so the initialization branch is skipped
    cmd.voice = VoiceThatFails()

    cmd.cmd_voice(args=None)

    assert any("Unable to use OpenAI whisper model: something went wrong" in e for e in io.errors)
    # placeholder should remain None because transcription failed
    assert io.placeholder is None
