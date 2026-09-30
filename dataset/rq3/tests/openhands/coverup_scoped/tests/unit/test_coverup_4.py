# file: openhands/security/grayswan/utils.py:30-152
# asked: {"lines": [32, 34, 36, 37, 40, 47, 50, 51, 52, 54, 55, 56, 57, 58, 59, 61, 62, 63, 64, 68, 69, 70, 71, 74, 75, 76, 78, 79, 80, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 96, 97, 99, 100, 101, 102, 103, 104, 105, 107, 109, 110, 111, 112, 115, 118, 119, 120, 132, 133, 134, 136, 137, 138, 140, 141, 142, 144, 146, 148, 149, 152], "branches": [[36, 37], [36, 152], [40, 47], [40, 50], [50, 51], [50, 54], [54, 55], [54, 67], [56, 57], [56, 61], [61, 36], [61, 62], [67, 74], [67, 118], [78, 36], [78, 79], [83, 36], [83, 84], [85, 86], [85, 109], [86, 87], [86, 107], [100, 101], [100, 102], [118, 36], [118, 132], [133, 134], [133, 136], [137, 138], [137, 140], [140, 141], [140, 148]]}
# gained: {"lines": [32, 34, 36, 37, 40, 47, 50, 51, 52, 54, 55, 56, 57, 58, 59, 61, 62, 63, 64, 68, 69, 70, 71, 74, 75, 76, 78, 79, 80, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 96, 97, 99, 100, 101, 102, 103, 104, 105, 107, 109, 110, 111, 112, 115, 118, 119, 120, 132, 133, 134, 136, 137, 138, 140, 141, 142, 144, 146, 148, 149, 152], "branches": [[36, 37], [36, 152], [40, 47], [40, 50], [50, 51], [50, 54], [54, 55], [54, 67], [56, 57], [56, 61], [61, 62], [67, 74], [67, 118], [78, 79], [83, 84], [85, 86], [85, 109], [86, 87], [86, 107], [100, 101], [118, 132], [133, 134], [133, 136], [137, 138], [137, 140], [140, 141], [140, 148]]}

import importlib
import importlib.util
import sys
import types
import json
from pathlib import Path

import pytest


def _setup_fake_openhands_modules():
    """
    Insert fake openhands.* modules into sys.modules to satisfy imports performed
    by the real openhands.security.grayswan.utils module when loaded from file.
    Returns (fake_logger, restore_fn).
    """
    # Names we'll manage
    created = {}
    originals = {}

    names = [
        'openhands',
        'openhands.core',
        'openhands.core.logger',
        'openhands.events',
        'openhands.events.action',
        'openhands.events.action.message',
        'openhands.events.event',
        'openhands.events.observation',
        'openhands.events.observation.observation',
        'openhands.events.observation.browse',
        'openhands.events.observation.commands',
        'openhands.events.observation.file_download',
        'openhands.events.observation.files',
        'openhands.events.observation.mcp',
    ]

    for name in names:
        originals[name] = sys.modules.get(name)

    # Create base packages
    mod_openhands = types.ModuleType('openhands')
    mod_openhands.__path__ = []
    created['openhands'] = mod_openhands
    sys.modules['openhands'] = mod_openhands

    mod_core = types.ModuleType('openhands.core')
    mod_core.__path__ = []
    created['openhands.core'] = mod_core
    sys.modules['openhands.core'] = mod_core
    mod_openhands.core = mod_core

    mod_events = types.ModuleType('openhands.events')
    mod_events.__path__ = []
    created['openhands.events'] = mod_events
    sys.modules['openhands.events'] = mod_events
    mod_openhands.events = mod_events

    # fake logger module
    class FakeLogger:
        def __init__(self):
            self.infos = []
            self.warnings = []

        def info(self, msg):
            self.infos.append(msg)

        def warning(self, msg):
            self.warnings.append(msg)

    fake_logger = FakeLogger()
    mod_logger = types.ModuleType('openhands.core.logger')
    mod_logger.openhands_logger = fake_logger
    created['openhands.core.logger'] = mod_logger
    sys.modules['openhands.core.logger'] = mod_logger
    mod_core.logger = mod_logger

    # action.message module with MessageAction and SystemMessageAction
    mod_action = types.ModuleType('openhands.events.action')
    mod_action.__path__ = []
    created['openhands.events.action'] = mod_action
    sys.modules['openhands.events.action'] = mod_action
    mod_events.action = mod_action

    mod_action_msg = types.ModuleType('openhands.events.action.message')

    class MessageAction:
        def __init__(self, content='', source=None, _source=None):
            self.content = content
            if source is not None:
                self.source = source
            if _source is not None:
                self._source = _source

    class SystemMessageAction:
        def __init__(self, content=''):
            self.content = content

    mod_action_msg.MessageAction = MessageAction
    mod_action_msg.SystemMessageAction = SystemMessageAction
    created['openhands.events.action.message'] = mod_action_msg
    sys.modules['openhands.events.action.message'] = mod_action_msg
    mod_action.message = mod_action_msg

    # events.event module with EventSource
    mod_event = types.ModuleType('openhands.events.event')

    class EventSource:
        USER = 'user'
        AGENT = 'agent'
        ENVIRONMENT = 'environment'

    mod_event.EventSource = EventSource
    created['openhands.events.event'] = mod_event
    sys.modules['openhands.events.event'] = mod_event
    mod_events.event = mod_event

    # observation base
    mod_obs_pkg = types.ModuleType('openhands.events.observation')
    mod_obs_pkg.__path__ = []
    created['openhands.events.observation'] = mod_obs_pkg
    sys.modules['openhands.events.observation'] = mod_obs_pkg
    mod_events.observation = mod_obs_pkg

    mod_obs_base = types.ModuleType('openhands.events.observation.observation')

    class Observation:
        pass

    mod_obs_base.Observation = Observation
    created['openhands.events.observation.observation'] = mod_obs_base
    sys.modules['openhands.events.observation.observation'] = mod_obs_base
    mod_obs_pkg.observation = mod_obs_base

    # browse observation
    mod_browse = types.ModuleType('openhands.events.observation.browse')

    class BrowserOutputObservation(Observation):
        def __init__(self, content=None, source=None, _source=None, tool_call_metadata=None):
            if content is not None:
                self.content = content
            if source is not None:
                self.source = source
            if _source is not None:
                self._source = _source
            self.tool_call_metadata = tool_call_metadata

    mod_browse.BrowserOutputObservation = BrowserOutputObservation
    created['openhands.events.observation.browse'] = mod_browse
    sys.modules['openhands.events.observation.browse'] = mod_browse
    mod_obs_pkg.browse = mod_browse

    # commands observations
    mod_commands = types.ModuleType('openhands.events.observation.commands')

    class CmdOutputObservation(Observation):
        def __init__(self, content=None, source=None, _source=None, tool_call_metadata=None):
            if content is not None:
                self.content = content
            if source is not None:
                self.source = source
            if _source is not None:
                self._source = _source
            self.tool_call_metadata = tool_call_metadata

    class IPythonRunCellObservation(Observation):
        def __init__(self, content=None, source=None, _source=None, tool_call_metadata=None):
            if content is not None:
                self.content = content
            if source is not None:
                self.source = source
            if _source is not None:
                self._source = _source
            self.tool_call_metadata = tool_call_metadata

    mod_commands.CmdOutputObservation = CmdOutputObservation
    mod_commands.IPythonRunCellObservation = IPythonRunCellObservation
    created['openhands.events.observation.commands'] = mod_commands
    sys.modules['openhands.events.observation.commands'] = mod_commands
    mod_obs_pkg.commands = mod_commands

    # file_download observation
    mod_file_download = types.ModuleType('openhands.events.observation.file_download')

    class FileDownloadObservation(Observation):
        def __init__(self, content=None, source=None, _source=None, tool_call_metadata=None):
            if content is not None:
                self.content = content
            if source is not None:
                self.source = source
            if _source is not None:
                self._source = _source
            self.tool_call_metadata = tool_call_metadata

    mod_file_download.FileDownloadObservation = FileDownloadObservation
    created['openhands.events.observation.file_download'] = mod_file_download
    sys.modules['openhands.events.observation.file_download'] = mod_file_download
    mod_obs_pkg.file_download = mod_file_download

    # files observations
    mod_files = types.ModuleType('openhands.events.observation.files')

    class FileReadObservation(Observation):
        def __init__(self, content=None, source=None, _source=None, tool_call_metadata=None):
            if content is not None:
                self.content = content
            if source is not None:
                self.source = source
            if _source is not None:
                self._source = _source
            self.tool_call_metadata = tool_call_metadata

    class FileWriteObservation(Observation):
        def __init__(self, content=None, source=None, _source=None, tool_call_metadata=None):
            if content is not None:
                self.content = content
            if source is not None:
                self.source = source
            if _source is not None:
                self._source = _source
            self.tool_call_metadata = tool_call_metadata

    class FileEditObservation(Observation):
        def __init__(self, content=None, source=None, _source=None, tool_call_metadata=None):
            if content is not None:
                self.content = content
            if source is not None:
                self.source = source
            if _source is not None:
                self._source = _source
            self.tool_call_metadata = tool_call_metadata

    mod_files.FileReadObservation = FileReadObservation
    mod_files.FileWriteObservation = FileWriteObservation
    mod_files.FileEditObservation = FileEditObservation
    created['openhands.events.observation.files'] = mod_files
    sys.modules['openhands.events.observation.files'] = mod_files
    mod_obs_pkg.files = mod_files

    # mcp observation
    mod_mcp = types.ModuleType('openhands.events.observation.mcp')

    class MCPObservation(Observation):
        def __init__(self, content=None, source=None, _source=None, tool_call_metadata=None):
            if content is not None:
                self.content = content
            if source is not None:
                self.source = source
            if _source is not None:
                self._source = _source
            self.tool_call_metadata = tool_call_metadata

    mod_mcp.MCPObservation = MCPObservation
    created['openhands.events.observation.mcp'] = mod_mcp
    sys.modules['openhands.events.observation.mcp'] = mod_mcp
    mod_obs_pkg.mcp = mod_mcp

    def restore():
        for name in names:
            orig = originals.get(name)
            if orig is None:
                if name in sys.modules:
                    del sys.modules[name]
            else:
                sys.modules[name] = orig

    return fake_logger, restore


def _load_utils_module_from_repo():
    """
    Locate openhands/security/grayswan/utils.py in the repository and load it as a module
    without importing the package __init__ files.
    """
    # Search for the file relative to current working directory
    candidates = list(Path.cwd().rglob('openhands/security/grayswan/utils.py'))
    if not candidates:
        # As a fallback, try relative to this file's directory
        candidates = list(Path(__file__).parent.rglob('openhands/security/grayswan/utils.py'))
    if not candidates:
        raise FileNotFoundError('Could not find openhands/security/grayswan/utils.py in the repository')
    utils_path = candidates[0]
    spec = importlib.util.spec_from_file_location('test_grayswan_utils', str(utils_path))
    module = importlib.util.module_from_spec(spec)
    # Ensure module is inserted so relative imports inside it (if any) can work
    sys.modules['test_grayswan_utils'] = module
    loader = spec.loader
    assert loader is not None
    loader.exec_module(module)
    return module


def test_convert_events_to_openai_messages_all_branches():
    fake_logger, restore = _setup_fake_openhands_modules()
    try:
        # Load the utils module directly from the repo file to avoid package __init__ side-effects
        utils = _load_utils_module_from_repo()

        # Create a series of events to exercise all branches

        # 1) Event type that should be skipped by name
        class AgentStateChangedObservation:
            pass

        skip_event = AgentStateChangedObservation()

        # 2) SystemMessageAction
        SystemMessageAction = sys.modules['openhands.events.action.message'].SystemMessageAction
        sys_msg = SystemMessageAction(content='system content')

        # 3) MessageAction from user and agent
        MessageAction = sys.modules['openhands.events.action.message'].MessageAction
        EventSource = sys.modules['openhands.events.event'].EventSource
        user_msg = MessageAction(content='hello user', source=EventSource.USER)
        agent_msg = MessageAction(content='hello agent', source=EventSource.AGENT)

        # 4) Tool call event (not an Observation) with tool_call_metadata and model_response choices with tool_calls
        class FakeFunction:
            def __init__(self, name, arguments):
                self.name = name
                self.arguments = arguments

        class ToolCallWithID:
            def __init__(self, id, func, type_=None):
                self.id = id
                if type_ is not None:
                    self.type = type_
                self.function = func

        # tc1: valid json arguments containing 'security_risk' (should be removed)
        func1 = FakeFunction('f1', json.dumps({'x': 1, 'security_risk': True}))
        tc1 = ToolCallWithID('tc1', func1, type_='function')

        # tc2: invalid json arguments (JSONDecodeError) -> should leave arguments as-is
        func2 = FakeFunction('f2', 'not a json')
        tc2 = ToolCallWithID('tc2', func2)

        # tc3: no id attribute (should be appended as-is)
        tc3 = {'not_id': True, 'function': {'name': 'f3', 'arguments': '{}'}}

        class FakeToolMetadata:
            def __init__(self, model_response):
                self.model_response = model_response

        model_response = {
            'choices': [
                {
                    'message': {
                        'content': 'assistant text',
                        'tool_calls': [tc1, tc2, tc3],
                    }
                }
            ]
        }

        class ToolEvent:
            def __init__(self, tool_call_metadata, source=None, _source=None):
                self.tool_call_metadata = tool_call_metadata
                if source is not None:
                    self.source = source
                if _source is not None:
                    self._source = _source

        tool_event = ToolEvent(FakeToolMetadata(model_response), source=EventSource.AGENT)

        # 5) Observation with tool_call_id -> should create 'tool' message
        FileReadObservation = sys.modules['openhands.events.observation.files'].FileReadObservation

        class ToolCallMetaWithID:
            def __init__(self, tool_call_id):
                self.tool_call_id = tool_call_id

        obs_with_id = FileReadObservation(content='file content', source=EventSource.AGENT, tool_call_metadata=ToolCallMetaWithID('call-123'))

        # 6) Observation with ENVIRONMENT source -> should be skipped
        obs_env = FileReadObservation(content='env content', source=EventSource.ENVIRONMENT, tool_call_metadata=ToolCallMetaWithID('call-999'))

        # 7) Observation without tool_call_metadata -> should trigger logger.warning
        obs_no_meta = FileReadObservation(content='no meta', source=EventSource.AGENT, tool_call_metadata=None)

        events = [skip_event, sys_msg, user_msg, agent_msg, tool_event, obs_with_id, obs_env, obs_no_meta]

        out = utils.convert_events_to_openai_messages(events)

        # Assertions about outputs
        roles = [m.get('role') for m in out]
        assert 'system' in roles
        assert roles.count('user') == 1
        assert roles.count('assistant') >= 2  # one from agent_msg, one from tool_event assistant_msg
        assert any(m.get('role') == 'tool' and m.get('tool_call_id') == 'call-123' for m in out)

        # Check assistant tool_calls processed correctly
        assistant_msgs = [m for m in out if m.get('role') == 'assistant']
        tool_assistant_msgs = [m for m in assistant_msgs if 'tool_calls' in m]
        assert len(tool_assistant_msgs) == 1
        tac = tool_assistant_msgs[0]
        tool_calls = tac['tool_calls']
        # Expect entries for tc1 and tc2 as dicts with ids, and the original tc3 dict present
        assert any(isinstance(tc, dict) and tc.get('id') == 'tc1' for tc in tool_calls)
        assert any(isinstance(tc, dict) and tc.get('id') == 'tc2' for tc in tool_calls)
        # Ensure security_risk removed from tc1 arguments
        tc1_processed = next(tc for tc in tool_calls if isinstance(tc, dict) and tc.get('id') == 'tc1')
        args_json = tc1_processed['function']['arguments']
        parsed_args = json.loads(args_json)
        assert 'security_risk' not in parsed_args

        # Ensure tc2 arguments remained the invalid string (since JSON decode failed)
        tc2_processed = next(tc for tc in tool_calls if isinstance(tc, dict) and tc.get('id') == 'tc2')
        assert tc2_processed['function']['arguments'] == 'not a json'

        # Ensure the third entry (no id) is present as original dict
        assert any((not isinstance(tc, dict) or 'id' not in tc) for tc in tool_calls)

        # Check logger warning was called for obs_no_meta
        # fake_logger captured in our fake module
        fake_logger = sys.modules['openhands.core.logger'].openhands_logger
        assert any('Could not find tool_call_id' in msg for msg in fake_logger.warnings)

    finally:
        # cleanup
        restore()
        sys.modules.pop('test_grayswan_utils', None)


def test_message_action_source_variants_and_sysmsg():
    fake_logger, restore = _setup_fake_openhands_modules()
    try:
        utils = _load_utils_module_from_repo()

        MessageAction = sys.modules['openhands.events.action.message'].MessageAction
        SystemMessageAction = sys.modules['openhands.events.action.message'].SystemMessageAction
        EventSource = sys.modules['openhands.events.event'].EventSource

        # Create MessageAction using _source attribute instead of source
        ma_user = MessageAction(content='u2', _source=EventSource.USER)
        ma_agent = MessageAction(content='a2', _source=EventSource.AGENT)
        sm = SystemMessageAction(content='sys2')

        out = utils.convert_events_to_openai_messages([ma_user, ma_agent, sm])

        # Assert roles and contents
        assert {'role': 'user', 'content': 'u2'} in out
        assert {'role': 'assistant', 'content': 'a2'} in out
        assert {'role': 'system', 'content': 'sys2'} in out

    finally:
        restore()
        sys.modules.pop('test_grayswan_utils', None)
