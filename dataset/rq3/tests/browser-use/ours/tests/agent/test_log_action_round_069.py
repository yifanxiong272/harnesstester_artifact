import asyncio
from types import SimpleNamespace
from browser_use.agent.service import Agent


class FakeLogger:
    def __init__(self):
        self.messages = []

    def info(self, msg):
        # emulate standard logger.info (synchronous)
        self.messages.append(msg)


class DummyAction:
    def __init__(self, dump_val):
        self._dump_val = dump_val

    def model_dump(self, exclude_unset=True):
        # preserve the exact call signature used by the production code
        return self._dump_val


def test_log_action_with_params_and_demo_round_069():
    """Covers branch: total_actions > 1, params present, demo mode enabled,
    plain_param_parts non-empty -> demo mode call is awaited and logger.info called with params.
    """
    # Arrange
    action_name = "do_something"
    action_num = 1
    total_actions = 2  # triggers total_actions > 1 branch

    # action model_dump should return a mapping keyed by action_name
    action = DummyAction({action_name: {"param1": "value1"}})

    demo_calls = []

    async def fake_demo_mode_log(message, level, metadata):
        demo_calls.append((message, level, metadata))

    fake_self = SimpleNamespace()
    fake_self.logger = FakeLogger()
    fake_self._demo_mode_enabled = True
    fake_self._demo_mode_log = fake_demo_mode_log
    fake_self.state = SimpleNamespace(n_steps=5)

    # Act
    asyncio.run(Agent._log_action(fake_self, action, action_name, action_num, total_actions))

    # Assert logger got an info message containing the header and the parameter
    assert fake_self.logger.messages, "logger.info was not called"
    logged = fake_self.logger.messages[-1]
    assert action_name in logged
    assert "param1" in logged
    assert "value1" in logged
    # Assert demo log was called with expected structure
    assert len(demo_calls) == 1, f"demo log was not called as expected: {demo_calls}"
    called_message, called_level, called_meta = demo_calls[0]
    assert called_level == "action"
    assert called_meta["action"] == action_name
    assert called_meta["step"] == 5
    # plain header should include the action name and show the action index/total
    assert f"[{action_num}/{total_actions}]" in called_message
    assert action_name in called_message


def test_log_action_truncation_and_no_demo_round_069():
    """Covers branches:
    - total_actions == 1 (else branch for action header)
    - string truncation branch (len > 150)
    - list truncation branch (len(str(list)) > 200)
    - demo mode disabled path
    """
    action_name = "shortrun"
    action_num = 1
    total_actions = 1  # triggers else header branch

    # Prepare a very long string and a long list to trigger both truncation branches
    long_string = "x" * 160  # >150 to trigger string truncation
    long_list = ["y" * 300, "z" * 50]

    action = DummyAction({action_name: {"long": long_string, "alist": long_list}})

    fake_self = SimpleNamespace()
    fake_self.logger = FakeLogger()
    fake_self._demo_mode_enabled = False  # ensure demo branch skipped
    async def unreachable_demo(*a, **k):
        raise AssertionError("_demo_mode_log should not be called when demo is disabled")
    fake_self._demo_mode_log = unreachable_demo
    fake_self.state = SimpleNamespace(n_steps=99)

    # Act
    asyncio.run(Agent._log_action(fake_self, action, action_name, action_num, total_actions))

    # Assert
    assert fake_self.logger.messages, "logger.info was not called"
    msg = fake_self.logger.messages[-1]
    # The message must contain parameter names
    assert "long" in msg
    assert "alist" in msg
    # The long string and list string representations should have been truncated with ellipses
    assert "..." in msg
    # Because demo mode was disabled, no exception should have been raised and no demo call happened
    # (unreachable_demo would raise if invoked)
