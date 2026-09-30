# file: pr_agent/algo/utils.py:519-578
# asked: {"lines": [531, 532, 533, 534, 535, 536, 538, 539, 540, 541, 542, 543, 544, 545, 546, 547, 549, 550, 551, 552, 553, 554, 555, 570], "branches": [[530, 531], [532, 533], [532, 554], [534, 535], [534, 538], [538, 539], [538, 541], [541, 532], [541, 542], [545, 546], [545, 549], [558, 560], [569, 570], [573, 557]]}
# gained: {"lines": [531, 532, 533, 534, 535, 536, 538, 539, 540, 541, 542, 543, 544, 545, 546, 547, 550, 551, 552, 553, 554, 555, 570], "branches": [[530, 531], [532, 533], [532, 554], [534, 535], [534, 538], [538, 539], [538, 541], [541, 542], [545, 546], [569, 570], [573, 557]]}

import importlib
import pytest

def test_parse_code_suggestion_gfm_with_link_and_exception(monkeypatch):
    utils = importlib.import_module("pr_agent.algo.utils")

    # Stub logger to capture exception calls
    class StubLogger:
        def __init__(self):
            self.exceptions = []

        def exception(self, msg):
            self.exceptions.append(msg)

    stub_logger = StubLogger()
    # Replace get_logger in module to return our stub
    monkeypatch.setattr(utils, "get_logger", lambda: stub_logger)

    # Construct dict that will:
    # - Trigger the gfm_supported branch because it contains 'relevant_line'
    # - Contain 'relevant_file' and 'suggestion' to exercise those branches
    # - Contain a None key to raise inside the try (None.lower() will raise AttributeError)
    code_suggestion = {
        "relevant_file": '`"myfile.py"`',
        "suggestion": "  fix this  ",
        "relevant_line": "`[line 100](http://example.com)`",
        None: "will-cause-exception",
    }

    out = utils.parse_code_suggestion(code_suggestion, gfm_supported=True)

    # Basic structure checks
    assert out.startswith("<table>")
    assert out.endswith("<hr>")
    assert "</table>" in out

    # relevant_file should be stripped of backticks and quotes
    assert "<tr><td>relevant file</td><td>myfile.py</td></tr>" in out

    # suggestion should be wrapped in <strong> with stripped whitespace
    assert "<strong" in out
    assert "fix this" in out

    # relevant_line should produce a link-like element containing the url and visible text
    assert "<a href" in out
    assert "line 100" in out
    assert "http://example.com" in out

    # The None key should trigger an exception inside the try/except and be logged
    assert len(stub_logger.exceptions) >= 1


def test_parse_code_suggestion_non_gfm_variants(monkeypatch):
    utils = importlib.import_module("pr_agent.algo.utils")

    # Prepare a code suggestion that uses the non-GFM path
    code_suggestion = {
        " some_key ": "value\n",
        "relevant_file_name": "file.py\n",
        "code_example": {
            "before": "x=1",
            "after": "x=2",
        },
        "relevant_line": "42\n",
    }

    out = utils.parse_code_suggestion(code_suggestion, gfm_supported=False)

    # The dict "code_example" should render fenced code blocks indented
    back = "`" * 3
    assert back in out
    assert "x=1" in out
    assert "x=2" in out

    # The code block should be indented by 8 spaces before the fence
    expected_indented_fence = "\n" + " " * 8 + back
    assert expected_indented_fence in out

    # The relevant_file_name key should be recognized as relevant_file (substring match)
    assert "**relevant_file_name:** file.py" in out

    # Ensure that simple keys had trailing newlines trimmed for values
    assert "value" in out

    # The function always appends a final newline in the non-gfm branch
    assert out.endswith("\n")
