import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('backend.server.server_utils')
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
        """complete the test case here"""
        # Ensure a clean outputs directory
        shutil.rmtree("outputs", ignore_errors=True)

        # Dummy websocket that captures sent messages
        messages = []

        class DummyWebsocket:
            async def send_json(self, data):
                messages.append(data)

        websocket = DummyWebsocket()

        # Dummy manager with start_streaming coroutine
        class ManagerMock:
            async def start_streaming(
                self,
                task,
                report_type,
                report_source,
                source_urls,
                document_urls,
                tone,
                websocket_arg,
                headers,
                query_domains,
                mcp_enabled,
                mcp_strategy,
                mcp_configs,
                max_search_results,
            ):
                return "This is the generated report content."

        manager = ManagerMock()

        # Monkeypatch generate_report_files used by handle_start_command to avoid heavy IO
        async def fake_generate_report_files(report: str, filename: str) -> Dict[str, str]:
            return {
                "pdf": os.path.join("outputs", f"{filename}.pdf"),
                "docx": os.path.join("outputs", f"{filename}.docx"),
                "md": os.path.join("outputs", f"{filename}.md"),
            }

        # Replace the function in the target function's globals so the call inside uses our fake
        handle_start_command.__globals__["generate_report_files"] = fake_generate_report_files

        # Prepare input data: handle_start_command strips first 6 chars and json.loads the rest
        payload = {
            "task": "my_task",
            "report_type": "brief",
            "source_urls": [],
            "document_urls": [],
            "tone": "",
            "headers": {},
            "report_source": "web",
            "query_domains": [],
            "mcp_enabled": False,
            "mcp_strategy": "fast",
            "mcp_configs": [],
            "max_search_results": None,
        }
        data = "X" * 6 + json.dumps(payload)

        # Run the coroutine
        asyncio.get_event_loop().run_until_complete(
            handle_start_command(websocket, data, manager)
        )

        # There should be at least one .json log file in outputs
        self.assertTrue(os.path.isdir("outputs"))
        json_files = [f for f in os.listdir("outputs") if f.endswith(".json")]
        self.assertGreaterEqual(len(json_files), 1, "Expected at least one JSON log file")

        # Determine the log file path (relative) that should have been added to file_paths
        log_file_name = json_files[0]
        expected_json_relpath = os.path.relpath(os.path.join("outputs", log_file_name))

        # Find the path message sent over websocket
        path_message = None
        for msg in messages:
            if isinstance(msg, dict) and msg.get("type") == "path":
                path_message = msg
                break

        self.assertIsNotNone(path_message, "Did not receive a path message over websocket")
        output_paths = path_message.get("output", {})
        self.assertIn("json", output_paths, "Output paths should include 'json' key")
        self.assertEqual(output_paths["json"], expected_json_relpath)

        # Verify the log file content was updated with the query
        with open(os.path.join("outputs", log_file_name), "r") as f:
            log_data = json.load(f)
        self.assertEqual(log_data["content"]["query"], "my_task")
