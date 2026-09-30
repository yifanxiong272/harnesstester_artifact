# file: aider/voice.py:116-180
# asked: {"lines": [117, 119, 121, 122, 123, 124, 125, 126, 127, 130, 132, 133, 134, 136, 137, 138, 140, 141, 142, 144, 147, 148, 149, 150, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 167, 168, 169, 170, 172, 173, 174, 176, 177, 179, 180], "branches": [[141, 142], [141, 144], [148, 149], [148, 152], [153, 154], [153, 167], [176, 177], [176, 179]]}
# gained: {"lines": [117, 119, 121, 122, 123, 124, 130, 132, 133, 134, 136, 140, 141, 142, 144, 147, 148, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 167, 168, 169, 170, 176, 177, 179, 180], "branches": [[141, 142], [141, 144], [148, 152], [153, 154], [153, 167], [176, 177], [176, 179]]}

import io
import os
import queue
import tempfile
import numpy as np
import builtins

import pytest

from types import SimpleNamespace

# Import the Voice class and exceptions
from aider.voice import Voice


class FakePortAudioError(Exception):
    pass


class FakeInputStream:
    def __init__(self, *, samplerate, channels, callback, device):
        self.callback = callback
        self.samplerate = samplerate
        self.channels = channels
        self.device = device

    def __enter__(self):
        # Call the callback once with a small numpy array as audio data.
        arr = np.array([[0.1], [0.2]], dtype="float32")
        frames = arr.shape[0]
        time_info = None
        status = None
        # The real callback expects the array shape (frames, channels)
        self.callback(arr, frames, time_info, status)
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeSD:
    PortAudioError = FakePortAudioError

    def __init__(self, samplerate_value="44100"):
        self._sr = samplerate_value

    def query_devices(self, device_id=None, kind="input"):
        return {"default_samplerate": self._sr}

    def InputStream(self, *, samplerate, channels, callback, device):
        return FakeInputStream(samplerate=samplerate, channels=channels, callback=callback, device=device)


class DummySoundFile:
    """
    Minimal replacement for soundfile.SoundFile used in the function under test.
    It writes raw numpy bytes to the path so that the file exists for later operations.
    """

    def __init__(self, path, mode, samplerate, channels):
        # open in exclusive creation to imitate mode="x"
        self.path = path
        # ensure parent dir exists
        parent = os.path.dirname(path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        self._fh = open(path, "xb")

    def write(self, data):
        if isinstance(data, np.ndarray):
            self._fh.write(data.tobytes())
        else:
            self._fh.write(bytes(data))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self._fh.close()
        return False


class DummyTranscription:
    def __init__(self, text):
        self.text = text


def test_raw_record_and_transcribe_wav_success(monkeypatch, tmp_path):
    # Create an instance without running __init__
    v = Voice.__new__(Voice)
    # Prepare attributes expected by raw_record_and_transcribe
    v.device_id = None
    v.sd = FakeSD(samplerate_value="44100")
    v.audio_format = "wav"
    # Replace the prompt used in the aider.voice module so it returns immediately
    monkeypatch.setattr("aider.voice.prompt", lambda *args, **kwargs: "")
    # Replace sf.SoundFile with our dummy
    monkeypatch.setattr("aider.voice.sf.SoundFile", DummySoundFile)
    # Replace tempfile.mktemp to return a predictable path within tmp_path
    temp_wav = str(tmp_path / "test_audio.wav")
    monkeypatch.setattr("tempfile.mktemp", lambda suffix=".wav": temp_wav)
    # Ensure the callback will put numpy arrays into the queue
    def cb(indata, frames, time_info, status):
        v.q.put(indata)
    v.callback = cb
    # Replace litellm.transcription to assert file readable and return DummyTranscription
    def fake_transcription(model, file, prompt, language):
        data = file.read(10)
        assert isinstance(data, (bytes, bytearray))
        return DummyTranscription("hello-wav")
    monkeypatch.setattr("aider.voice.litellm.transcription", fake_transcription)
    # Run the function
    text = v.raw_record_and_transcribe(history="history", language="en")
    assert text == "hello-wav"
    # Clean up created file if any remains
    if os.path.exists(temp_wav):
        os.remove(temp_wav)


def test_raw_record_and_transcribe_conversion_to_mp3(monkeypatch, tmp_path):
    v = Voice.__new__(Voice)
    v.device_id = None
    v.sd = FakeSD(samplerate_value="44100")
    v.audio_format = "mp3"
    monkeypatch.setattr("aider.voice.prompt", lambda *args, **kwargs: "")
    monkeypatch.setattr("aider.voice.sf.SoundFile", DummySoundFile)
    # mktemp returns temp wav path then mp3 path
    temp_wav = str(tmp_path / "conv_test.wav")
    temp_mp3 = str(tmp_path / "conv_out.mp3")
    mk_calls = [temp_wav, temp_mp3]

    def fake_mktemp(suffix=".wav"):
        return mk_calls.pop(0)

    monkeypatch.setattr("tempfile.mktemp", fake_mktemp)

    # Setup callback to put numpy data
    def cb(indata, frames, time_info, status):
        v.q.put(indata)

    v.callback = cb

    # Monkeypatch AudioSegment.from_wav to return object with export method
    exported = {"called": False, "path": None}

    class DummyAudio:
        def __init__(self, path):
            self.path = path

        def export(self, out_path, format):
            exported["called"] = True
            exported["path"] = out_path
            # create the output file so later open("rb") in code succeeds
            with open(out_path, "wb") as fh:
                fh.write(b"MP3DATA")
            return True

    monkeypatch.setattr("aider.voice.AudioSegment.from_wav", lambda p: DummyAudio(p))

    # Replace litellm.transcription to verify it gets the mp3 file and return transcription
    def fake_transcription(model, file, prompt, language):
        content = file.read()
        assert content == b"MP3DATA"
        return DummyTranscription("converted-mp3")

    monkeypatch.setattr("aider.voice.litellm.transcription", fake_transcription)

    # Run function
    text = v.raw_record_and_transcribe(history="h", language="en")
    assert text == "converted-mp3"
    assert exported["called"] is True
    # Ensure both temp files were cleaned up
    assert not os.path.exists(temp_wav)
    assert not os.path.exists(temp_mp3)


def test_raw_record_and_transcribe_conversion_decode_error(monkeypatch, tmp_path):
    # This test triggers AudioSegment.from_wav raising CouldntDecodeError
    from pydub.exceptions import CouldntDecodeError

    v = Voice.__new__(Voice)
    v.device_id = None
    v.sd = FakeSD(samplerate_value=None)  # will cause fallback to 16000
    v.audio_format = "mp3"
    monkeypatch.setattr("aider.voice.prompt", lambda *args, **kwargs: "")
    monkeypatch.setattr("aider.voice.sf.SoundFile", DummySoundFile)
    temp_wav = str(tmp_path / "fail_conv.wav")
    temp_mp3 = str(tmp_path / "fail_conv.mp3")
    mk_calls = [temp_wav, temp_mp3]
    monkeypatch.setattr("tempfile.mktemp", lambda suffix=".wav": mk_calls.pop(0))
    # callback puts data
    def cb(indata, frames, time_info, status):
        v.q.put(indata)
    v.callback = cb
    # Make AudioSegment.from_wav raise CouldntDecodeError
    def raise_decode(p):
        raise CouldntDecodeError("bad wav")
    monkeypatch.setattr("aider.voice.AudioSegment.from_wav", raise_decode)
    # litellm.transcription should be called with the original wav file
    def fake_transcription(model, file, prompt, language):
        data = file.read(4)
        assert isinstance(data, (bytes, bytearray))
        return DummyTranscription("decode-failed-but-transcribed")

    monkeypatch.setattr("aider.voice.litellm.transcription", fake_transcription)
    # Run function
    text = v.raw_record_and_transcribe(history="h", language="en")
    assert text == "decode-failed-but-transcribed"
    # Clean up
    if os.path.exists(temp_wav):
        os.remove(temp_wav)
