import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.storage.s3')
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
        """Verify S3FileStore.write maps S3 ClientError codes to FileNotFoundError messages."""
        def make_client(code):
            class MockClient:
                def put_object(self, Bucket: str, Key: str, Body):
                    raise botocore.exceptions.ClientError(
                        {
                            'Error': {
                                'Code': code,
                                'Message': f"Simulated {code} error",
                            }
                        },
                        'PutObject',
                    )
            return MockClient()

        # AccessDenied -> specific message
        with patch('boto3.client', lambda *a, **k: make_client('AccessDenied')):
            store = S3FileStore('dear-liza')
            with self.assertRaises(FileNotFoundError) as cm:
                store.write('some/path.txt', 'content')
            self.assertEqual(
                str(cm.exception),
                "Error: Access denied to bucket 'dear-liza'."
            )

        # NoSuchBucket -> specific message
        with patch('boto3.client', lambda *a, **k: make_client('NoSuchBucket')):
            store = S3FileStore('dear-liza')
            with self.assertRaises(FileNotFoundError) as cm:
                store.write('another/path.txt', b'bytes')
            self.assertEqual(
                str(cm.exception),
                "Error: The bucket 'dear-liza' does not exist."
            )

        # Some other error -> generic message containing path and bucket
        with patch('boto3.client', lambda *a, **k: make_client('InternalError')):
            store = S3FileStore('dear-liza')
            path = 'yet/another/path.txt'
            with self.assertRaises(FileNotFoundError) as cm:
                store.write(path, 'data')
            msg = str(cm.exception)
            self.assertTrue(
                msg.startswith(f"Error: Failed to write to bucket 'dear-liza' at path {path}:"),
                f"Unexpected message: {msg}"
            )
