import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.server.data_models.feedback')
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
        # Prepare a FeedbackDataModel where feedback initially differs from polarity
        fb = FeedbackDataModel(
            version='1.0',
            email='user@example.com',
            polarity='positive',
            feedback='negative',  # will be overwritten by store_feedback
            permissions='public',
            trajectory=[{'step': 1}, {'step': 2}],
        )

        called = {}

        # Fake httpx.post to capture call and return a successful response
        def fake_post(*args, **kwargs):
            called['args'] = args
            called['kwargs'] = kwargs
            class Resp:
                pass
            resp = Resp()
            resp.status_code = 200
            # Use module-level json to build response text
            resp.text = json.dumps({'result': 'ok'})
            return resp

        # Replace httpx.post with our fake, call the function, then restore
        original_post = httpx.post
        try:
            httpx.post = fake_post
            result = store_feedback(fb)
        finally:
            httpx.post = original_post

        # Assert returned data parsed correctly
        self.assertEqual(result, {'result': 'ok'})
        # The model's feedback attribute should have been updated to match polarity
        self.assertEqual(fb.feedback, fb.polarity)
        # The payload sent to httpx.post should reflect the updated feedback field
        sent_json = called['kwargs'].get('json')
        self.assertIsNotNone(sent_json)
        self.assertEqual(sent_json.get('feedback'), fb.polarity)
        # Ensure the request was sent to the expected URL
        self.assertEqual(called['args'][0], FEEDBACK_URL)
