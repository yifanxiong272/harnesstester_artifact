import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.voice')
except Exception:
    _testtailor_target = None
else:
    globals().update({
        name: value
        for name, value in vars(_testtailor_target).items()
        if not name.startswith("__")
    })

class _TestTailorTimeout:
    @staticmethod
    def timeout(_seconds):
        return lambda function: function

timeout_decorator = _TestTailorTimeout()

class Test(unittest.TestCase):
    @timeout_decorator.timeout(1)
    def test_case_XX(self):
        """Ensure branch switching to mp3 conversion is taken when WAV file is too large."""
        # Prepare a mocked sounddevice module
        mock_sd = MagicMock()
        mock_sd.query_devices.return_value = {"default_samplerate": "16000"}
        mock_sd.PortAudioError = Exception
        # Make InputStream act as a no-op context manager
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = None
        mock_cm.__exit__.return_value = None
        mock_sd.InputStream.return_value = mock_cm

        # Prepare a mocked soundfile (sf) with a SoundFile context manager that provides a write method
        mock_sf = MagicMock()
        mock_file_cm = MagicMock()
        mock_file = MagicMock()
        mock_file.write = MagicMock()
        mock_file_cm.__enter__.return_value = mock_file
        mock_file_cm.__exit__.return_value = None
        mock_sf.SoundFile.return_value = mock_file_cm

        # Patch modules and functions used inside raw_record_and_transcribe
        with patch.dict("sys.modules", {"sounddevice": mock_sd}):
            with patch("aider.voice.sf", mock_sf):
                with patch("aider.voice.prompt", lambda *args, **kwargs: None):
                    # tempfile.mktemp called twice: first for wav, then for converted file
                    wav_path = "/tmp/fake_large.wav"
                    mp3_path = "/tmp/fake_converted.mp3"
                    with patch("tempfile.mktemp", side_effect=[wav_path, mp3_path]):
                        # Force file size to be larger than the threshold
                        large_size = int(25 * 1024 * 1024)
                        with patch("os.path.getsize", return_value=large_size):
                            # Ensure AudioSegment.from_wav returns an object whose export writes the file
                            def fake_from_wav(path):
                                class FakeAudio:
                                    def export(self, new_filename, format=None):
                                        # create the converted file so it can be opened later
                                        with open(new_filename, "wb") as f:
                                            f.write(b"fake mp3 data")
                                return FakeAudio()

                            with patch("aider.voice.AudioSegment.from_wav", side_effect=fake_from_wav) as mock_from_wav:
                                # Prevent actual file removals (no-op)
                                with patch("os.remove", side_effect=lambda *args, **kwargs: None) as mock_remove:
                                    # Mock the transcription call to return an object with a .text attribute
                                    fake_transcript = type("T", (), {"text": "transcribed text"})()
                                    with patch("aider.voice.litellm.transcription", return_value=fake_transcript) as mock_trans:
                                        # Create the Voice instance (will pick up our mocked sounddevice)
                                        voice = Voice()
                                        # Ensure audio_format is wav to trigger the branch
                                        voice.audio_format = "wav"

                                        # Call the method under test
                                        result = voice.raw_record_and_transcribe(history="prompt history", language="en")

                                        # Assertions: conversion path executed and transcription result returned
                                        self.assertEqual(result, "transcribed text")
                                        mock_from_wav.assert_called_once_with(wav_path)
                                        mock_trans.assert_called_once()
