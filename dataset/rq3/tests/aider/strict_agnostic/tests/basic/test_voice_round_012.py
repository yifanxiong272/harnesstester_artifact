import io
import os
import queue
import tempfile
from types import SimpleNamespace
import pytest

import aider.voice as voice_mod


class FakeSD:
    """Fake sound device interface used to simulate device queries and provide
    a no-op InputStream context manager. Provides a PortAudioError attribute
    to mirror the real API used by the code under test.
    """

    class PortAudioError(Exception):
        pass

    def __init__(self, default_samplerate=None, query_raises=None):
        # query_raises: exception instance or None
        self._default_samplerate = default_samplerate
        self._query_raises = query_raises

    def query_devices(self, device_id, kind):
        if self._query_raises:
            raise self._query_raises
        return {"default_samplerate": str(self._default_samplerate)}

    class InputStream:
        def __init__(self, samplerate, channels, callback, device):
            # simple no-op context manager
            self.samplerate = samplerate
            self.channels = channels
            self.callback = callback
            self.device = device

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False


class FakeSoundFile:
    """A minimal replacement for sf.SoundFile that writes raw bytes to disk
    so that os.path.getsize and file operations are deterministic and local.
    The real SoundFile would accept numpy arrays, but for our tests we simply
    accept bytes or objects exposing tobytes().
    """

    def __init__(self, path, mode="x", samplerate=None, channels=None):
        self.path = path
        # ensure the directory exists
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # open in binary write mode (truncate/create)
        self._f = open(path, "wb")

    def write(self, data):
        if hasattr(data, "tobytes"):
            self._f.write(data.tobytes())
        elif isinstance(data, (bytes, bytearray)):
            self._f.write(data)
        else:
            # best effort: cast to bytes
            self._f.write(bytes(data))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self._f.close()
        return False


class FakeAudioSegment:
    def __init__(self, src_path, export_path=None, export_format=None, write_bytes=b"converted"):
        self.src_path = src_path
        self._write_bytes = write_bytes

    @classmethod
    def from_wav(cls, path):
        return cls(path)

    def export(self, out_path, format=None):
        # create a small file to represent the exported audio
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as fh:
            fh.write(self._write_bytes)


def bind_raw_method():
    # return the unbound method for convenience
    return voice_mod.Voice.raw_record_and_transcribe


def make_dummy(self_sd, device_id=0, audio_format="wav"):
    class Dummy:
        pass

    d = Dummy()
    d.sd = self_sd
    d.device_id = device_id
    d.callback = lambda *a, **k: None
    d.audio_format = audio_format
    d.get_prompt = lambda: "PROMPT"
    d.q = queue.Queue()
    return d


def _mktemp_sequence(tmp_path, names):
    # returns a function that yields subsequent paths from names
    seq = [str(tmp_path / n) for n in names]

    def _fn(suffix=""):
        if not seq:
            # fallback deterministic name
            return str(tmp_path / ("fallback" + suffix))
        return seq.pop(0) + suffix

    return _fn


def test_raw_record_small_file_round_012(tmp_path, monkeypatch):
    """Covers: sample_rate fallback (TypeError), queue write loop, small file
    path (no conversion), and successful transcription returning text.
    """
    # Arrange: tempfile.mktemp should return a predictable small wav path
    tmp_wav = tmp_path / "small.wav"
    mktemp = _mktemp_sequence(tmp_path, ["small"])  # will produce small + suffix
    monkeypatch.setattr(tempfile, "mktemp", mktemp)

    # Replace SoundFile with our fake that writes to disk
    monkeypatch.setattr(voice_mod, "sf", SimpleNamespace(SoundFile=FakeSoundFile))

    # Ensure prompt() is a no-op (don't block tests)
    monkeypatch.setattr(voice_mod, "prompt", lambda *a, **k: None)

    # Prepare fake sound device: query_devices raises TypeError to trigger fallback
    fake_sd = FakeSD(query_raises=TypeError())
    fake_sd.PortAudioError = FakeSD.PortAudioError
    fake_sd.InputStream = FakeSD.InputStream

    # Create dummy instance
    dummy = make_dummy(fake_sd, device_id=0, audio_format="wav")

    # Put a small chunk into the queue so the while loop writes to the file
    dummy.q.put(b"hello")

    # Monkeypatch litellm.transcription to return an object with .text
    def fake_transcribe(model, file, prompt, language):
        return SimpleNamespace(text=f"transcribed:{language}:{prompt}")

    monkeypatch.setattr(voice_mod, "litellm", SimpleNamespace(transcription=fake_transcribe))

    # Act
    func = bind_raw_method()
    result = func(dummy, history="history_text", language="en")

    # Assert: transcription text returned and matches expected formatted string
    assert result == "transcribed:en:history_text"


def test_raw_record_conversion_and_cleanup_round_012(tmp_path, monkeypatch):
    """Covers: large file detection, switching to mp3 conversion, conversion via
    AudioSegment.from_wav/export, deletion of converted file after transcription.
    """
    # Arrange: prepare two mktemp return names: original wav and new mp3
    mktemp = _mktemp_sequence(tmp_path, ["bigfile", "converted"])
    monkeypatch.setattr(tempfile, "mktemp", mktemp)

    # Use real FakeSoundFile to create a small wav file - we will fake getsize to be large
    monkeypatch.setattr(voice_mod, "sf", SimpleNamespace(SoundFile=FakeSoundFile))

    # prompt no-op
    monkeypatch.setattr(voice_mod, "prompt", lambda *a, **k: None)

    # Fake sd returns a real samplerate string so no fallback
    fake_sd = FakeSD(default_samplerate=44100)
    fake_sd.PortAudioError = FakeSD.PortAudioError
    fake_sd.InputStream = FakeSD.InputStream

    dummy = make_dummy(fake_sd, device_id=0, audio_format="wav")
    # queue has some bytes so file.write will be called
    dummy.q.put(b"audio-bytes")

    # Force os.path.getsize to report a value above the threshold for the temp wav
    def fake_getsize(path):
        # if path ends with .wav report > 24.9MB, else use real getsize for converted file
        if str(path).endswith(".wav"):
            return int(25 * 1024 * 1024)
        return original_getsize(path)

    original_getsize = os.path.getsize
    monkeypatch.setattr(os.path, "getsize", fake_getsize)

    # Provide FakeAudioSegment implementation in the voice module that will create the mp3
    monkeypatch.setattr(voice_mod, "AudioSegment", FakeAudioSegment)

    # Track removals
    removed = []

    def fake_remove(path):
        removed.append(path)
        # actually remove the file if present
        try:
            original_remove(path)
        except Exception:
            pass

    original_remove = os.remove
    monkeypatch.setattr(os, "remove", fake_remove)

    # Monkeypatch transcription to return a simple text
    def fake_transcribe(model, file, prompt, language):
        return SimpleNamespace(text="ok-from-mp3")

    monkeypatch.setattr(voice_mod, "litellm", SimpleNamespace(transcription=fake_transcribe))

    # Act
    func = bind_raw_method()
    result = func(dummy, history="h", language="en")

    # Assert: transcription succeeded and returned expected text
    assert result == "ok-from-mp3"
    # Because conversion was performed, the converted filename (second mktemp call) should be removed
    # We expect at least one removal call and it should refer to the converted file (endswith .mp3)
    assert any(str(p).endswith(".mp3") or str(p).endswith("converted.mp3") or "converted" in str(p) for p in removed)


def test_raw_record_transcription_fails_round_012(tmp_path, monkeypatch):
    """Covers the transcription exception path: litellm.transcription raises and
    the function returns None (early return after printing the error).
    """
    mktemp = _mktemp_sequence(tmp_path, ["failwav"])  # single wav path
    monkeypatch.setattr(tempfile, "mktemp", mktemp)

    monkeypatch.setattr(voice_mod, "sf", SimpleNamespace(SoundFile=FakeSoundFile))
    monkeypatch.setattr(voice_mod, "prompt", lambda *a, **k: None)

    fake_sd = FakeSD(default_samplerate=16000)
    fake_sd.PortAudioError = FakeSD.PortAudioError
    fake_sd.InputStream = FakeSD.InputStream

    dummy = make_dummy(fake_sd, device_id=0, audio_format="wav")
    dummy.q.put(b"bytes")

    # Make transcription raise
    def raising_transcribe(model, file, prompt, language):
        raise RuntimeError("transcription subsystem failed")

    monkeypatch.setattr(voice_mod, "litellm", SimpleNamespace(transcription=raising_transcribe))

    func = bind_raw_method()
    result = func(dummy, history="h", language="en")

    # When transcription fails the function returns None
    assert result is None
