import types
import pytest

import pr_agent.algo.utils as utils


class FakeLogger:
    def __init__(self):
        self.infos = []
        self.debugs = []

    def info(self, msg):
        # record the message for assertions
        self.infos.append(str(msg))

    def debug(self, msg):
        # record the message for assertions
        self.debugs.append(str(msg))


def test_try_fix_yaml_first_last_keys_round_083(monkeypatch):
    """
    Ensure the code path that extracts a YAML snippet by first_key/last_key returns parsed YAML
    and emits the success info message.
    """
    fake_logger = FakeLogger()
    monkeypatch.setattr(utils, "get_logger", lambda: fake_logger)

    # Create a response_text that contains a YAML snippet between start and end markers.
    response_text = (
        "some preamble\n"
        "start:\n"
        "  alpha: 1\n"
        "  beta: 2\n"
        "\n"
        "end:\n"
        "trailing text\n"
    )

    # Stub yaml.safe_load: only return a value when given the extracted snippet portion (contains 'start:')
    def fake_safe_load(arg):
        s = str(arg)
        if "start:" in s:
            return {"start": {"alpha": 1, "beta": 2}}
        raise Exception("not parsable in earlier attempts")

    monkeypatch.setattr(utils.yaml, "safe_load", fake_safe_load)

    result = utils.try_fix_yaml(response_text, keys_fix_yaml=[], first_key="start", last_key="end")

    assert result == {"start": {"alpha": 1, "beta": 2}}
    # ensure the info log for successful extraction was emitted
    assert any("Successfully parsed AI prediction after extracting yaml snippet" in m for m in fake_logger.infos)


def test_try_fix_yaml_snippet_debug_and_curly_braces_round_083(monkeypatch):
    """
    When extracting a ```yaml snippet fails, the function should emit a debug message and
    succeed later by removing surrounding curly braces and parsing the inner YAML.
    """
    fake_logger = FakeLogger()
    monkeypatch.setattr(utils, "get_logger", lambda: fake_logger)

    # Craft response text with a failing yaml snippet but with valid YAML inside curly braces when braces removed
    response_text = "{\nvalid_key: valid_value\n```yaml\ninvalid: yes\n```\n}"

    # Stub yaml.safe_load:
    # - Raise when asked to parse the snippet body (we trigger the snippet branch)
    # - Succeed when given text that contains 'valid_key: valid_value' (i.e., after removing braces)
    def fake_safe_load(arg):
        s = str(arg)
        if "invalid: yes" in s:
            # simulate parser failure for the extracted snippet
            raise Exception("snippet failed")
        if "valid_key: valid_value" in s:
            return {"valid_key": "valid_value"}
        # For any other earlier attempts, raise to continue fallbacks
        raise Exception("not parsable yet")

    monkeypatch.setattr(utils.yaml, "safe_load", fake_safe_load)

    result = utils.try_fix_yaml(response_text, keys_fix_yaml=[], first_key="", last_key="", response_text_original=response_text)

    assert result == {"valid_key": "valid_value"}
    # ensure debug message about failing to parse snippet was emitted
    assert any("Failed to parse AI prediction after extracting yaml snippet" in m for m in fake_logger.debugs)
    # ensure info about successful parse after removing curly braces was emitted
    assert any("Successfully parsed AI prediction after removing curly brackets" in m for m in fake_logger.infos)


def test_try_fix_yaml_tabs_replacement_round_083(monkeypatch):
    """
    If the response contains tabs, the sixth fallback replaces them with spaces and parses.
    """
    fake_logger = FakeLogger()
    monkeypatch.setattr(utils, "get_logger", lambda: fake_logger)

    # response_text contains a tab that should be replaced
    response_text = "\tmy_key: my_value"

    # Stub yaml.safe_load: fail for inputs that still contain a tab; succeed when tabs replaced by 4 spaces
    def fake_safe_load(arg):
        s = str(arg)
        if "\t" in s:
            raise Exception("contains tab")
        if "    my_key: my_value" in s or "my_key: my_value" in s:
            return {"my_key": "my_value"}
        raise Exception("other parse failure")

    monkeypatch.setattr(utils.yaml, "safe_load", fake_safe_load)

    result = utils.try_fix_yaml(response_text)

    assert result == {"my_key": "my_value"}
    assert any("replacing tabs with spaces" in m for m in fake_logger.infos)


def test_try_fix_yaml_add_indent_for_sections_round_083(monkeypatch):
    """
    The seventh fallback should add indentation for lines following recognized section keys
    and parse successfully when indentation is applied.
    """
    fake_logger = FakeLogger()
    monkeypatch.setattr(utils, "get_logger", lambda: fake_logger)

    # This response has a section key 'existing_code:' followed by lines that need indentation.
    response_text = (
        "some header\n"
        "existing_code:\n"
        "def hello():\n"
        "print(\"hi\")\n"
    )

    # Stub yaml.safe_load: succeed only when indentation has been added (i.e., '    print' exists)
    def fake_safe_load(arg):
        s = str(arg)
        if "    print(\"hi\")" in s or "    def hello()" in s:
            return {"existing_code": "indented"}
        # fail all other attempts
        raise Exception("not indented yet")

    monkeypatch.setattr(utils.yaml, "safe_load", fake_safe_load)

    result = utils.try_fix_yaml(response_text)

    assert result == {"existing_code": "indented"}
    assert any("adding indent for sections of code blocks" in m for m in fake_logger.infos)
