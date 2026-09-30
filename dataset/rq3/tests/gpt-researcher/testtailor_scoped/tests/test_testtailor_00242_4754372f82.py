import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.llm_provider.generic.base')
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
        """Ensure usage_metadata.model_dump() branch is exercised."""
        class _Chunk:
            def __init__(self, content, usage_metadata=None, response_metadata=None):
                self.content = content
                self.usage_metadata = usage_metadata
                self.response_metadata = response_metadata

        class _Usage:
            def __init__(self, data):
                self._data = data

            def model_dump(self):
                return self._data

        class _Resp:
            def __init__(self, data):
                self._data = data

            def model_dump(self):
                return self._data

        class _StreamingLLM:
            async def astream(self, messages, **kwargs):
                yield _Chunk("Hello")
                # Final chunk has no content but provides usage_metadata with model_dump
                yield _Chunk(
                    "",
                    usage_metadata=_Usage({"input_tokens": 10, "output_tokens": 5}),
                    response_metadata=_Resp({"meta": "ok", "usage": {"input_tokens": 10, "output_tokens": 5}}),
                )

        provider = GenericLLMProvider(_StreamingLLM(), verbose=False)

        response = asyncio.run(provider.stream_response([{"role": "user", "content": "hi"}]))

        self.assertEqual(response, "Hello")
        self.assertEqual(provider.last_usage_metadata, {"input_tokens": 10, "output_tokens": 5})
        self.assertEqual(provider.last_response_metadata.get("usage"), {"input_tokens": 10, "output_tokens": 5})
        self.assertEqual(provider.last_response_metadata.get("meta"), "ok")
