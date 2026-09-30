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
        """Exercise raw_record_and_transcribe to hit queue/tempfile creation and full path to transcription."""
        # Prepare a predictable temp filename we can create/remove
        temp_filename = "test_temp_audio.wav"
        # Ensure no leftover file
        try:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
        except Exception:
            pass

        # Build a mock sounddevice module that behaves as needed by Voice
        mock_sd = MagicMock()
        # query_devices should return a list when called with no args (in __init__)
        # and return a dict with default_samplerate when called with args (in recording)
        def query_devices_side_effect(*args, **kwargs):
            if len(args) == 0:
                return [{"name": "mock_device", "max_input_channels": 1}]
            else:
                return {"default_samplerate": "16000"}

        mock_sd.query_devices.side_effect = query_devices_side_effect
        mock_sd.PortAudioError = Exception
        # Make InputStream a simple context manager that does nothing
        mock_input_cm = MagicMock()
        mock_input_cm.__enter__.return_value = None
        mock_input_cm.__exit__.return_value = None
        mock_sd.InputStream.return_value = mock_input_cm

        # Patch sounddevice import in aider.voice to our mock module
        with patch.dict("sys.modules", {"sounddevice": mock_sd}):
            # Patch other helpers inside the aider.voice module
            with patch("aider.voice.sf") as mock_sf, patch(
                "aider.voice.prompt", new=MagicMock(return_value=None)
            ), patch("aider.voice.tempfile.mktemp", return_value=temp_filename), patch(
                "aider.voice.os.path.getsize", return_value=100
            ), patch(
                "aider.voice.litellm.transcription",
                return_value=MagicMock(text="transcribed text"),
            ):
                # Make sf.SoundFile a context manager that will create the actual file when entered
                def soundfile_ctor(path, mode="x", samplerate=None, channels=None):
                    cm = MagicMock()
                    def enter():
                        # create the file so open(filename, "rb") later succeeds
                        open(path, "wb").close()
                        file_obj = MagicMock()
                        file_obj.write = MagicMock()
                        return file_obj
                    cm.__enter__.side_effect = enter
                    cm.__exit__.return_value = None
                    return cm

                mock_sf.SoundFile.side_effect = soundfile_ctor

                # Instantiate Voice (will use our mocked sounddevice)
                voice = Voice()

                # Call the target method; should return the mocked transcription text
                result = voice.raw_record_and_transcribe(history="prompt text", language="en")

                assert result == "transcribed text"

        # Cleanup created file
        try:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
        except Exception:
            pass
