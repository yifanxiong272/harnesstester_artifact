import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('multi_agents.agents.publisher')
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
        agent = PublisherAgent(output_dir=" out ")
        research_state = {
            "research_data": [
                "First section content",
                {"Subsection A": "Second section content"}
            ],
            "sources": ["Reference 1", "Reference 2"],
            "headers": {
                "title": "Test Report",
                "date": "Report Date",
                "introduction": "Introduction",
                "table_of_contents": "Table of Contents",
                "conclusion": "Conclusion",
                "references": "References"
            },
            "date": "2026-08-23",
            "introduction": "This is the introduction body.",
            "table_of_contents": "1. First\n2. Second",
            "conclusion": "This is the conclusion."
        }
        publish_formats = {}  # no formats to avoid calling external writers

        # import asyncio dynamically to avoid top-level import statement
        asyncio = __import__('asyncio')
        loop = asyncio.new_event_loop()
        try:
            layout = loop.run_until_complete(agent.publish_research_report(research_state, publish_formats))
        finally:
            loop.close()

        # Build expected layout string exactly as generate_layout would
        sections = ["First section content", "Second section content"]
        sections_text = '\n\n'.join(sections)
        references = '\n'.join(research_state.get("sources", []))
        headers = research_state.get("headers", {})
        expected_layout = f"""# {headers.get('title')}
#### {headers.get("date")}: {research_state.get('date')}

## {headers.get("introduction")}
{research_state.get('introduction')}

## {headers.get("table_of_contents")}
{research_state.get('table_of_contents')}

{sections_text}

## {headers.get("conclusion")}
{research_state.get('conclusion')}

## {headers.get("references")}
{references}
"""
        self.assertEqual(layout, expected_layout)
