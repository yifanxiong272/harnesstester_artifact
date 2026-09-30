# file: aider/voice.py:116-180
# asked: {"lines": [117, 119, 121, 122, 123, 124, 125, 126, 127, 130, 132, 133, 134, 136, 137, 138, 140, 141, 142, 144, 147, 148, 149, 150, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 167, 168, 169, 170, 172, 173, 174, 176, 177, 179, 180], "branches": [[141, 142], [141, 144], [148, 149], [148, 152], [153, 154], [153, 167], [176, 177], [176, 179]]}
# gained: {"lines": [117, 119, 121, 122, 123, 125, 126, 127, 130, 132, 133, 134, 136, 137, 138, 140, 141, 142, 144, 147, 148, 152, 153, 154, 155, 156, 157, 158, 159, 167, 168, 169, 170, 172, 173, 174, 176, 179, 180], "branches": [[141, 142], [141, 144], [148, 152], [153, 154], [153, 167], [176, 179]]}

import io
import os
import tempfile
import queue
import types
import threading

import pytest

import numpy as np

import aider.voice as av
from aider.voice import Voice, SoundDeviceError

class DummyTranscription:
    def __init__(self, text):
        self.text = text

class FakeSoundFile:
    """
    Mimics soundfile.SoundFile for writing arrays to disk so that os.path.getsize
    reflects a real file being created.
    """
    def __init__(self, path, mode="x", samplerate=None, channels=None):
        self.path = path
        self.mode = mode
        # ensure parent dirs exist
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        # open underlying file in binary append mode so writes add bytes
        # 'x' should create new file, so emulate that
        if 'x' in mode and os.path.exists(self.path):
            raise FileExistsError(self.path)
        self._fh = open(self.path, "wb")

    def write(self, data):
        # Accept numpy arrays or bytes; write some bytes to file to simulate audio content
        if isinstance(data, np.ndarray):
            # write raw bytes
            self._fh.write(data.tobytes())
        elif isinstance(data, (bytes, bytearray)):
            self._fh.write(data)
        else:
            # fallback
            self._fh.write(str(data).encode('utf-8'))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self._fh.close()
        except Exception:
            pass

class SimpleAudioSegment:
    def __init__(self, src_path, target_path=None, make_bytes=b''):
        self.src = src_path
        self.target_path = target_path
        self.make_bytes = make_bytes

    @classmethod
    def from_wav(cls, path):
        # return an instance bound to that path; actual export will create a file
        return cls(path)

    def export(self, outpath, format=None):
        # create the output file and write some bytes so os.path.getsize works
        with open(outpath, "wb") as fh:
            fh.write(b"MP3DATA" if format == "mp3" else b"DATA")
        return outpath

class FakeInputStream:
    """
    Acts as a context manager. On __enter__, it calls the provided callback once
    to simulate arriving audio frames. Can be configured to raise an error on enter.
    """
    def __init__(self, *, samplerate, channels, callback, device):
        self.callback = callback
        self.samplerate = samplerate
        self.channels = channels
        self.device = device
        # do not raise by default
        self.raise_on_enter = False
        self.raise_exc = None

    def __enter__(self):
        if self.raise_on_enter:
            raise self.raise_exc
        # simulate a short chunk of audio frames and call callback
        data = np.zeros((100, self.channels), dtype=np.float32)
        # frames param set to number of frames
        self.callback(data, data.shape[0], None, None)
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

class FakeSD:
    """
    Provides query_devices, InputStream factory, and PortAudioError for tests.
    """
    class PortAudioError(Exception):
        pass

    def __init__(self, default_samplerate="16000", input_works=True, input_raises=False, query_raises=False):
        self._default_samplerate = default_samplerate
        self.input_works = input_works
        self.input_raises = input_raises
        self.query_raises = query_raises
        # placeholder for the last created FakeInputStream so tests can configure it
        self.last_stream = None

    def query_devices(self, device_id, mode=None):
        if self.query_raises:
            raise self.PortAudioError("no device")
        return {"default_samplerate": self._default_samplerate}

    def InputStream(self, *, samplerate, channels, callback, device):
        stream = FakeInputStream(samplerate=samplerate, channels=channels, callback=callback, device=device)
        if self.input_raises:
            stream.raise_on_enter = True
            stream.raise_exc = self.PortAudioError("cannot open")
        self.last_stream = stream
        return stream

@pytest.fixture(autouse=True)
def patch_prompt(monkeypatch):
    # avoid interactive prompt; just no-op
    monkeypatch.setattr(av, "prompt", lambda *a, **kw: None)
    yield

def make_voice_instance(monkeypatch, audio_format="wav", sd=None):
    # instantiate Voice without invoking its __init__ which depends on real sounddevice
    v = Voice.__new__(Voice)
    v.audio_format = audio_format
    v.device_id = None
    if sd is None:
        sd = FakeSD()
    v.sd = sd
    # ensure get_prompt exists to be passed to prompt (even though prompt is patched)
    v.get_prompt = lambda: "X"
    # provide a simple callback that puts raw numpy arrays into the queue
    def callback(indata, frames, time_, status):
        # store raw frames into queue; keep the arrays small
        v.q.put(indata)
    v.callback = callback
    return v

def test_raw_record_and_transcribe_success_wav(tmp_path, monkeypatch):
    # Arrange
    temp_wav = str(tmp_path / "test.wav")
    # Patch tempfile.mktemp to return our path
    monkeypatch.setattr(av.tempfile, "mktemp", lambda suffix=".wav": temp_wav)
    # Patch soundfile.SoundFile to our FakeSoundFile that writes a real file
    monkeypatch.setattr(av.sf, "SoundFile", FakeSoundFile)
    # Patch get AudioSegment only to be present (won't be used because audio_format is wav)
    monkeypatch.setattr(av, "AudioSegment", SimpleAudioSegment)
    # Patch litellm.transcription to return a dummy object with .text
    monkeypatch.setattr(av.litellm, "transcription", lambda model, file, prompt, language: DummyTranscription("hello world"))
    # Create fake sd that returns default samplerate as a string
    sd = FakeSD(default_samplerate="16000")
    v = make_voice_instance(monkeypatch, audio_format="wav", sd=sd)

    # Act
    result = v.raw_record_and_transcribe(history="ctx", language="en")

    # Assert
    assert result == "hello world"
    # Confirm that temp_wav was created by FakeSoundFile and has non-zero size
    assert os.path.exists(temp_wav)
    assert os.path.getsize(temp_wav) > 0
    # Clean up
    os.remove(temp_wav)

def test_raw_record_and_transcribe_conversion_and_transcription_failure(tmp_path, monkeypatch):
    # Arrange: audio_format is mp3 so conversion branch is exercised
    temp_wav = str(tmp_path / "record.wav")
    new_mp3 = str(tmp_path / "record.mp3")
    # mktemp should first return temp_wav, then also used to create new_filename in conversion
    calls = {"count": 0}
    def fake_mktemp(suffix=".wav"):
        calls["count"] += 1
        if calls["count"] == 1:
            return temp_wav
        else:
            # ensure extension for conversion
            return new_mp3
    monkeypatch.setattr(av.tempfile, "mktemp", fake_mktemp)
    # Ensure FakeSoundFile creates the WAV file
    monkeypatch.setattr(av.sf, "SoundFile", FakeSoundFile)
    # Patch AudioSegment.from_wav and export to create the converted file
    class AS:
        @staticmethod
        def from_wav(path):
            return SimpleAudioSegment(path)
    monkeypatch.setattr(av, "AudioSegment", AS)
    # Patch litellm.transcription to raise an exception to hit the error printing and early return
    def raise_transcription(model, file, prompt, language):
        raise RuntimeError("transcription failed")
    monkeypatch.setattr(av.litellm, "transcription", raise_transcription)
    sd = FakeSD(default_samplerate="44100")
    v = make_voice_instance(monkeypatch, audio_format="mp3", sd=sd)

    # Pre-conditions: no files exist
    assert not os.path.exists(temp_wav)
    assert not os.path.exists(new_mp3)

    # Act
    result = v.raw_record_and_transcribe(history="ctx", language="en")

    # Assert: since transcription raised, function returns None
    assert result is None
    # Ensure mp3 was created and wav was removed during conversion
    assert os.path.exists(new_mp3)
    assert not os.path.exists(temp_wav)
    # Clean up
    if os.path.exists(new_mp3):
        os.remove(new_mp3)

def test_raw_record_and_transcribe_query_devices_portaudio_raises(monkeypatch):
    # Arrange: simulate query_devices raising PortAudioError -> should raise SoundDeviceError
    sd = FakeSD(query_raises=True)
    v = make_voice_instance(monkeypatch, audio_format="wav", sd=sd)

    # Patch tempfile.mktemp though it should not be reached, but keep safe
    monkeypatch.setattr(av.tempfile, "mktemp", lambda suffix=".wav": os.path.join(tempfile.gettempdir(), "should_not_be_created.wav"))
    # Patch sf.SoundFile to prevent accidental writes
    monkeypatch.setattr(av.sf, "SoundFile", FakeSoundFile)

    # Act & Assert
    with pytest.raises(SoundDeviceError):
        v.raw_record_and_transcribe(history=None, language=None)

def test_raw_record_and_transcribe_inputstream_portaudio_raises(monkeypatch):
    # Arrange: simulate InputStream failing on enter -> should raise SoundDeviceError
    sd = FakeSD()
    sd.input_raises = True
    v = make_voice_instance(monkeypatch, audio_format="wav", sd=sd)

    # Patch tempfile.mktemp
    monkeypatch.setattr(av.tempfile, "mktemp", lambda suffix=".wav": os.path.join(tempfile.gettempdir(), "should_not_be_created2.wav"))
    # Patch sf.SoundFile to our FakeSoundFile to be safe
    monkeypatch.setattr(av.sf, "SoundFile", FakeSoundFile)

    # Act & Assert: InputStream __enter__ raises PortAudioError causing SoundDeviceError
    with pytest.raises(SoundDeviceError):
        v.raw_record_and_transcribe(history=None, language=None)
