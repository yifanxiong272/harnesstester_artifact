# file: aider/coders/wholefile_func_coder.py:60-87
# asked: {"lines": [60, 61, 62, 64, 66, 67, 69, 70, 72, 73, 74, 76, 77, 78, 79, 80, 81, 82, 84, 85, 87], "branches": [[61, 62], [61, 64], [66, 67], [66, 69], [73, 74], [73, 76], [76, 77], [76, 87], [78, 79], [78, 80], [81, 82], [81, 84]]}
# gained: {"lines": [60, 61, 62, 64, 66, 69, 70, 72, 73, 74, 76, 77, 78, 79, 80, 81, 82, 84, 85, 87], "branches": [[61, 62], [61, 64], [66, 69], [73, 74], [76, 77], [76, 87], [78, 79], [78, 80], [81, 82], [81, 84]]}

import types
from aider.coders.wholefile_func_coder import WholeFileFunctionCoder


def test_render_incremental_response_returns_partial_when_present():
    # Create a dummy self with only partial_response_content set.
    dummy = types.SimpleNamespace()
    dummy.partial_response_content = "PARTIAL_CONTENT"
    # Call the unbound function with our dummy instance.
    result = WholeFileFunctionCoder.render_incremental_response(dummy, final=True)
    assert result == "PARTIAL_CONTENT"


def test_render_incremental_response_processes_files_and_explanation():
    calls = []

    # Define files to exercise branches:
    # 0: missing path -> skipped
    # 1: has path but empty content -> skipped
    # 2: valid non-last file -> live_diffs called with this_final True (because i < len(files)-1)
    # 3: valid last file -> live_diffs called with this_final == final (we pass final=False so False)
    files = [
        {},  # missing path
        {"path": "ignored.txt", "content": ""},  # content falsy -> skipped
        {"path": "b.txt", "content": "Content B"},
        {"path": "c.txt", "content": "Content C"},
    ]

    def parse_partial_args():
        return {"explanation": "Planned changes", "files": files}

    def live_diffs(path, content, final_flag):
        calls.append((path, content, final_flag))
        return f"DIFF:{path}:{content}:{final_flag}\n"

    # Create dummy object with required attributes/methods
    dummy = types.SimpleNamespace()
    dummy.partial_response_content = None
    dummy.parse_partial_args = parse_partial_args
    dummy.live_diffs = live_diffs

    result = WholeFileFunctionCoder.render_incremental_response(dummy, final=False)

    # Explanation should be included followed by two diffs in order
    assert result.startswith("Planned changes\n\n")
    assert "DIFF:b.txt:Content B:True" in result
    assert "DIFF:c.txt:Content C:False" in result

    # Ensure live_diffs was called exactly for the two valid files and with correct final flags
    assert calls == [
        ("b.txt", "Content B", True),
        ("c.txt", "Content C", False),
    ]
