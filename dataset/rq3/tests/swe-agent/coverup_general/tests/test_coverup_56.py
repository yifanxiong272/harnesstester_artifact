# file: sweagent/api/hooks.py:98-117
# asked: {"lines": [101, 104, 107, 108, 111, 112, 113, 114, 117], "branches": [[112, 0], [112, 113]]}
# gained: {"lines": [101, 104, 107, 108, 111, 112, 113, 114, 117], "branches": [[112, 0], [112, 113]]}

import pytest
from sweagent.api.hooks import MainUpdateHook

class WebUpdateMock:
    def __init__(self):
        self.calls = []
        self.finish_called = False

    def up_env(self, message=None, format=None, type_=None):
        # record explicit signature used in code
        self.calls.append(('up_env', message, format, type_))

    def up_agent(self, *args, **kwargs):
        # record positional and keyword invocation
        self.calls.append(('up_agent', args, kwargs))

    def finish_run(self):
        self.finish_called = True
        self.calls.append(('finish_run',))


def test_on_start_and_on_end_calls_webupdate_methods():
    wu = WebUpdateMock()
    hook = MainUpdateHook(wu)  # executes __init__ (line 101)

    # Call on_start should call up_env with specific args
    hook.on_start()
    assert len(wu.calls) >= 1
    first = wu.calls[0]
    assert first[0] == 'up_env'
    assert first[1] == "Environment container initialized"
    assert first[2] == "text"
    assert first[3] == "info"

    # Call on_end should call up_agent with message kw and format kw, then finish_run
    hook.on_end()
    # After previous up_env, on_end should have appended up_agent and finish_run
    assert any(c[0] == 'up_agent' for c in wu.calls), "up_agent was not called on end"
    # find the up_agent call that corresponds to on_end (message kw)
    up_agent_calls = [c for c in wu.calls if c[0] == 'up_agent']
    # There should be at least one up_agent call; the on_end one uses message kw
    found_on_end = False
    for _, args, kwargs in up_agent_calls:
        if kwargs.get("message") == "The run has ended" and kwargs.get("format") == "text":
            found_on_end = True
            break
    assert found_on_end, "Did not find expected on_end up_agent call with correct kwargs"
    # finish_run should have been called
    assert wu.finish_called is True
    assert any(c[0] == 'finish_run' for c in wu.calls)


def test_on_instance_completed_branches_and_print(capsys):
    wu = WebUpdateMock()
    hook = MainUpdateHook(wu)

    # Case 1: submission present but exit_status not 'submitted' -> only print, no success up_agent
    info1 = {"submission": "my-submission-id", "exit_status": "failed"}
    hook.on_instance_completed(info=info1, trajectory=None)
    captured = capsys.readouterr()
    # Should print the submission value
    assert "my-submission-id" in captured.out

    # Ensure no success up_agent call was made (i.e., type_ == "success")
    success_calls = [c for c in wu.calls if c[0] == 'up_agent' and c[2].get("type_") == "success"]
    assert success_calls == [], "No success up_agent should be called for non-submitted exit_status"

    # Case 2: submission present and exit_status == 'submitted' -> print and then up_agent with success
    info2 = {"submission": "my-submission-id", "exit_status": "submitted"}
    hook.on_instance_completed(info=info2, trajectory=None)
    captured = capsys.readouterr()
    assert "my-submission-id" in captured.out

    # The expected message created in the hook
    expected_msg = (
        "The submission was successful. You can find the patch (diff) in the right panel. "
        "To apply it to your code, run `git apply /path/to/patch/file.patch`. "
    )

    # Find a call matching positional msg and type_="success"
    found = False
    for name, args, kwargs in wu.calls:
        if name != 'up_agent':
            continue
        if len(args) == 1 and args[0] == expected_msg and kwargs.get("type_") == "success":
            found = True
            break
    assert found, "Expected success up_agent call with the submission message and type_='success'"
