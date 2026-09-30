import asyncio

import backend.utils as utils


class _FakeAioFile:
    def __init__(self, record, expected_filename=None, expected_mode=None, expected_encoding=None):
        self._record = record
        self._expected_filename = expected_filename
        self._expected_mode = expected_mode
        self._expected_encoding = expected_encoding

    async def write(self, payload):
        # mimic real aiofiles behavior: accept str payload
        if not isinstance(payload, str):
            raise TypeError("write expects str")
        self._record.append(payload)


class _FakeOpenCM:
    def __init__(self, record, capture):
        # capture is used by the fake_open to store call metadata only.
        self._record = record
        self._capture = capture

    async def __aenter__(self):
        # Do NOT unpack capture as kwargs; capture contains metadata keys
        # like 'calls' which _FakeAioFile.__init__ does not accept.
        return _FakeAioFile(self._record)

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _make_fake_open(record, capture):
    # This function will replace aiofiles.open
    def fake_open(filename, mode, encoding=None):
        # capture the call arguments for assertions
        capture_info = capture.setdefault("calls", [])
        capture_info.append({"filename": filename, "mode": mode, "encoding": encoding})
        return _FakeOpenCM(record, capture)

    return fake_open


def test_write_to_file_with_str_round_171():
    """
    Ensure that when text is already a string, write_to_file writes the exact
    UTF-8-normalized string and calls aiofiles.open with expected kwargs.
    Covers branch: 14->18 (text is str) and lines 18,20,21.
    """
    recorded = []
    capture = {}

    # Patch the aiofiles.open used by backend.utils
    original_open = utils.aiofiles.open
    try:
        utils.aiofiles.open = _make_fake_open(recorded, capture)

        filename = "dummy.txt"
        text = "hello – world \u2603"  # include a unicode snowman and an en-dash

        # Run the async function synchronously
        asyncio.run(utils.write_to_file(filename, text))

        # Assertions: one write call recorded with UTF-8 roundtrip preserved
        assert len(recorded) == 1, "expected a single write call"
        expected = text.encode("utf-8", errors="replace").decode("utf-8")
        assert recorded[0] == expected

        # Verify aiofiles.open was called with prescribed args
        assert "calls" in capture and len(capture["calls"]) == 1
        call = capture["calls"][0]
        assert call["filename"] == filename
        assert call["mode"] == "w"
        assert call["encoding"] == "utf-8"
    finally:
        utils.aiofiles.open = original_open


def test_write_to_file_with_nonstr_round_171():
    """
    Ensure that when text is not a string (e.g., an int or bytes), it is
    converted via str(text) before encoding and writing.
    Covers branch: 14->15 (conversion) and subsequent lines 18,20,21.
    """
    recorded = []
    capture = {}

    original_open = utils.aiofiles.open
    try:
        utils.aiofiles.open = _make_fake_open(recorded, capture)

        filename = "another_dummy.txt"
        # Use a bytes object to trigger the conversion path
        text_input = b"binary-data-\xff"  # bytes; not a str

        asyncio.run(utils.write_to_file(filename, text_input))

        # After conversion, the code does text = str(text_input)
        expected_text = str(text_input).encode("utf-8", errors="replace").decode("utf-8")

        assert len(recorded) == 1, "expected a single write call on non-str input"
        assert recorded[0] == expected_text

        # Ensure aiofiles.open was invoked correctly
        assert "calls" in capture and len(capture["calls"]) == 1
        call = capture["calls"][0]
        assert call["filename"] == filename
        assert call["mode"] == "w"
        assert call["encoding"] == "utf-8"
    finally:
        utils.aiofiles.open = original_open
