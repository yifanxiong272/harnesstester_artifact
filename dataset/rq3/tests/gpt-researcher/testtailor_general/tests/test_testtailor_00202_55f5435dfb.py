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
        """Test handle_start_command creates logs, invokes manager, and sends file paths including json log"""
        # Prepare a fake websocket to capture sent JSON messages
        class FakeWebsocket:
            def __init__(self):
                self.sent = []

            async def send_json(self, data):
                # store a deep copy to avoid mutation issues
                self.sent.append(json.loads(json.dumps(data)))

        # Fake manager with an async start_streaming that returns a simple report string
        class FakeManager:
            async def start_streaming(
                self,
                task,
                report_type,
                report_source,
                source_urls,
                document_urls,
                tone,
                websocket,
                headers,
                query_domains,
                mcp_enabled,
                mcp_strategy,
                mcp_configs,
                max_search_results,
            ):
                # simulate some streaming result
                return f"# Report for {task}\n\nThis is a test report."

        websocket = FakeWebsocket()
        manager = FakeManager()
        task = "unit test task"
        payload = {
            "task": task,
            "report_type": "summary",
            # other optional keys can be left out or empty
        }
        # handle_start_command slices off the first 6 characters of data
        data = "start " + json.dumps(payload)

        # Patch generate_report_files in the module where handle_start_command is defined
        mod = sys.modules[handle_start_command.__module__]
        original_generate = getattr(mod, "generate_report_files", None)

        async def fake_generate_report_files(report: str, filename: str):
            # Return simple paths quickly; actual json path will be added by the target code
            return {
                "pdf": os.path.join("outputs", f"{filename}.pdf"),
                "docx": os.path.join("outputs", f"{filename}.docx"),
                "md": os.path.join("outputs", f"{filename}.md"),
            }

        try:
            setattr(mod, "generate_report_files", fake_generate_report_files)
            # Run the async handler
            asyncio.get_event_loop().run_until_complete(
                handle_start_command(websocket, data, manager)
            )
        finally:
            # Restore original function to avoid side effects on other tests
            if original_generate is not None:
                setattr(mod, "generate_report_files", original_generate)

        # There should be at least two messages:
        #  - initial log content sent by CustomLogsHandler.send_json
        #  - final file paths sent by send_file_paths
        self.assertGreaterEqual(len(websocket.sent), 2)

        # First message is the initial log content
        first = websocket.sent[0]
        self.assertEqual(first, {"query": task, "sources": [], "context": [], "report": ""})

        # Final message should be the paths payload
        final = websocket.sent[-1]
        self.assertIsInstance(final, dict)
        self.assertEqual(final.get("type"), "path")
        output = final.get("output")
        self.assertIsInstance(output, dict)
        # json path must be present and point to an existing file (relative path)
        self.assertIn("json", output)
        json_path = output["json"]
        self.assertTrue(json_path.endswith(".json"))
        self.assertTrue(os.path.exists(json_path))
