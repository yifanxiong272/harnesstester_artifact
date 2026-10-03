import sys
import json
from pathlib import Path

from openhands.sdk.hooks.executor import HookExecutor
from openhands.sdk.hooks.config import HookDefinition
from openhands.sdk.hooks.types import HookEvent, HookEventType


def test_probe_001(tmp_path):
    """Verify non-string (null) 'decision' in JSON stdout does not cause execute to fail.

    This constructs a small Python script that prints {"decision": null} and exits 0,
    then runs it via HookExecutor.execute and asserts the result remains a success and
    no type/parsing error is surfaced and decision stays None.
    """
    # Write a small deterministic script that prints JSON with decision set to null
    script_path = Path(tmp_path) / "print_null_decision.py"
    script_path.write_text(
        "import json,sys\nprint(json.dumps({'decision': None}))\n",
        encoding="utf-8",
    )

    # Build executor and event
    executor = HookExecutor(working_dir=str(tmp_path))
    event = HookEvent(
        event_type=HookEventType.PRE_TOOL_USE,
        tool_name="BashTool",
        tool_input={"command": "ls -la"},
        session_id="test-session",
    )

    # Command invokes the same Python interpreter on the script file
    command = f"{sys.executable} {str(script_path)}"
    hook = HookDefinition(command=command)

    result = executor.execute(hook, event)

    # Primary behavioral oracle: success preserved and decision tolerated as None
    assert result.success is True
    assert result.exit_code == 0
    # Decision should be None when non-string/null was emitted
    assert result.decision is None
    # No parsing/type error should be reported
    assert not getattr(result, "error", None)
