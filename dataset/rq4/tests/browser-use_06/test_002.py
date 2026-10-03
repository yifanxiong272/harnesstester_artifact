def test_probe_001():
    # Import the public entrypoint class
    from browser_use.agent.views import AgentHistory

    SECRET = 'SECRET_VALUE'

    # Dummy action object whose model_dump returns the nested structure:
    # {'input': {'params': [[ 'SECRET_VALUE' ]]}}
    class DummyAction:
        def model_dump(self, *args, **kwargs):
            # Accept any kwargs the real code passes (exclude_none, mode, ...)
            return {'input': {'params': [[SECRET]]}}

    # Dummy model_output object with attributes accessed by AgentHistory.model_dump
    class DummyModelOutput:
        def __init__(self, actions):
            self.evaluation_previous_goal = None
            self.memory = None
            self.next_goal = None
            self.action = actions
            self.thinking = None
            self.current_plan_item = None
            self.plan_update = None

    # Minimal dummy Tab that implements model_dump used by BrowserStateHistory.to_dict
    class DummyTab:
        def model_dump(self):
            return {'url': 'http://example', 'title': 'title'}

    # Minimal BrowserStateHistory-compatible dummy implementing to_dict
    class DummyState:
        def __init__(self):
            self.url = 'http://example'
            self.title = 'title'
            self.tabs = [DummyTab()]
            # interacted_element entries may be None or objects with to_dict; use None for simplicity
            self.interacted_element = [None]
            self.screenshot_path = None

        def to_dict(self):
            return {
                'tabs': [tab.model_dump() for tab in self.tabs],
                'screenshot_path': self.screenshot_path,
                'interacted_element': [el if el is None else el.to_dict() for el in self.interacted_element],
                'url': self.url,
                'title': self.title,
            }

    dummy_output = DummyModelOutput(actions=[DummyAction()])
    state = DummyState()

    # Construct AgentHistory without running full validation to avoid needing other complex types.
    # Use model_construct if available (pydantic v2 escape hatch)
    if hasattr(AgentHistory, 'model_construct'):
        ah = AgentHistory.model_construct(model_output=dummy_output, result=[], state=state, metadata=None, state_message=None)
    else:
        ah = AgentHistory(model_output=dummy_output, result=[], state=state, metadata=None, state_message=None)

    # Call the public entrypoint under test
    dumped = ah.model_dump(sensitive_data={'password': SECRET})

    # Helper: recursively collect all string values from the returned structure
    def collect_strings(obj):
        if isinstance(obj, str):
            yield obj
        elif isinstance(obj, dict):
            for v in obj.values():
                yield from collect_strings(v)
        elif isinstance(obj, (list, tuple, set)):
            for item in obj:
                yield from collect_strings(item)
        # ignore other types

    found = [s for s in collect_strings(dumped) if SECRET in s]

    # Primary assertion: the exact sensitive literal must not appear anywhere in any returned string
    assert not found, f"Sensitive literal {SECRET!r} found in dumped output: {found}. Full dump: {dumped!r}"
