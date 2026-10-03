def test_probe_001():
    """Probe cancellation that occurs while waiting for resource locks.

    Invariant: If a CancellationToken becomes cancelled after _run_safe begins
    but before the tool_runner would be invoked (i.e. during lock wait), the
    executor must not call the tool_runner for that action and must return an
    AgentErrorEvent for that action.
    """

    import threading
    from unittest.mock import MagicMock

    from openhands.sdk.agent.parallel_executor import ParallelToolExecutor
    from openhands.sdk.conversation.resource_lock_manager import ResourceLockManager
    from openhands.sdk.tool.tool import DeclaredResources
    from openhands.sdk.event.llm_convertible import AgentErrorEvent

    # Simple CancellationToken-like object used by _run_safe (only is_cancelled read)
    class SimpleCancel:
        def __init__(self) -> None:
            self.is_cancelled = False
        def cancel(self) -> None:
            self.is_cancelled = True

    # Helpers to create minimal ActionEvent-like objects expected by executor
    def _make_action(tool_name: str, tool_call_id: str):
        a = MagicMock()
        a.tool_name = tool_name
        a.tool_call_id = tool_call_id
        return a

    # Setup lock manager and executor
    lock_mgr = ResourceLockManager()
    executor = ParallelToolExecutor(max_workers=2, lock_manager=lock_mgr)

    # Choose a resource key that will be held by the test thread to force blocking
    blocked_key = "file:/blocked.py"
    free_key = "file:/free.py"

    # Build two actions: first will be blocked on the lock, second will run normally
    blocked_action = _make_action("editor", "call_block")
    free_action = _make_action("editor", "call_free")
    actions = [blocked_action, free_action]

    # Event used to observe that the worker has computed declared resources
    resource_computed = threading.Event()

    # Tool definition mock: declared_resources signals when called for the blocked action
    tool = MagicMock()

    def declared_resources(a):
        # Signal that the worker has reached resource extraction for this action
        if a.tool_call_id == "call_block":
            resource_computed.set()
            return DeclaredResources(keys=(blocked_key,), declared=True)
        return DeclaredResources(keys=(free_key,), declared=True)

    tool.declared_resources = declared_resources
    tools = {"editor": tool}

    # Track invocations of the provided tool_runner
    called_ids = []

    ok_event = MagicMock(name="ok")

    def tool_runner(a):
        called_ids.append(a.tool_call_id)
        return [ok_event]

    # Prepare cancel token and holder of results
    cancel_token = SimpleCancel()
    results_container = {}

    # Acquire the resource lock for 'blocked_key' so the worker will block when attempting to lock
    lock_cm = lock_mgr.lock(blocked_key)
    lock_cm.__enter__()

    try:
        # Run execute_batch in a background thread so the main thread can flip cancellation
        def run_exec():
            results_container['res'] = executor.execute_batch(actions, tool_runner, tools, cancel_token)

        t = threading.Thread(target=run_exec, daemon=True)
        t.start()

        # Wait until the worker has computed resources for the blocked action
        got = resource_computed.wait(timeout=2.0)
        assert got, "timed out waiting for worker to reach resource computation"

        # Now mark the token cancelled while the caller still holds the lock
        cancel_token.cancel()

        # Release the held lock so the worker can proceed (it should observe cancellation and not call tool_runner)
    finally:
        lock_cm.__exit__(None, None, None)

    # Wait for background execution to finish deterministically
    t.join(timeout=5.0)
    assert not t.is_alive(), "execute_batch did not finish within timeout"

    results = results_container.get('res')
    assert results is not None, "no results returned from execute_batch"

    # Results preserve input ordering: index 0 corresponds to blocked_action
    blocked_result = results[0]
    free_result = results[1]

    # Primary oracle: blocked action must have been cancelled by the executor and not run
    assert len(blocked_result) == 1, "expected single Event result for blocked action"
    assert isinstance(blocked_result[0], AgentErrorEvent), (
        f"Expected AgentErrorEvent for cancelled blocked action, got {type(blocked_result[0])}"
    )

    # The tool_runner must NOT have been invoked for the blocked action
    assert "call_block" not in called_ids, "tool_runner was invoked for the blocked action despite cancellation"

    # Sanity: the free action should have executed normally
    assert free_result == [ok_event], "expected free action to run normally"
