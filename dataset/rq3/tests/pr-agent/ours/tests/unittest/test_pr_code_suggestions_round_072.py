import pytest

import pr_agent.tools.pr_code_suggestions as pcs_module
from pr_agent.tools.pr_code_suggestions import PRCodeSuggestions


class _FakeLogger:
    def __init__(self):
        self.messages = []

    def error(self, msg):
        # store for later assertions
        self.messages.append(msg)


def _new_prcodesuggestions_instance():
    # avoid running heavy __init__; create bare instance and set attrs directly
    inst = PRCodeSuggestions.__new__(PRCodeSuggestions)
    return inst


def test_remove_line_numbers_varied_round_072():
    """Covers numeric-only lines, lines starting with digits followed by letters,
    and lines that become empty after processing.
    """
    inst = _new_prcodesuggestions_instance()

    # Setup patches containing various cases handled by the method
    # 1st patch: numeric-only line then a normal alpha line
    patch1 = "123\nabc"

    # 2nd patch: starts with digits then letters (12abc -> becomes 'bc' per algorithm),
    # numeric-only line (0044 -> becomes ''), and a short digit+letter (9x -> becomes '')
    patch2 = "12abc\n0044\n9x"

    inst.patches_diff_list = [patch1, patch2]

    result = inst.remove_line_numbers([])  # argument is ignored on success path

    # Based on the implementation:
    # patch1: ['123','abc'] -> '123' is isnumeric -> '' ; 'abc' unchanged -> '\nabc'
    # patch2: ['12abc','0044','9x'] ->
    #   '12abc': first non-digit at index 2 ('a') -> stored slice line[j+1:] => j=2 => slice from 3 => 'bc'
    #   '0044': isnumeric -> ''
    #   '9x': first non-digit at j=1 -> slice from 2 -> ''
    expected = ["\nabc", "bc\n\n"]

    assert isinstance(result, list) and len(result) == 2
    assert result == expected


def test_remove_line_numbers_exception_round_072(monkeypatch):
    """Force an exception inside the method (by providing a non-string item in
    self.patches_diff_list) and assert the exception branch: logger.error called
    and the original argument is returned.
    """
    inst = _new_prcodesuggestions_instance()

    # cause splitlines() to raise by using None inside the list
    inst.patches_diff_list = [None]

    fake_logger = _FakeLogger()
    # Patch the module-level get_logger to return our shared fake logger
    monkeypatch.setattr(pcs_module, "get_logger", lambda: fake_logger)

    sentinel = ["original_input"]
    returned = inst.remove_line_numbers(sentinel)

    # On exception, the method should log an error and return the supplied argument
    assert returned is sentinel
    assert len(fake_logger.messages) == 1
    assert "Error removing line numbers" in fake_logger.messages[0]
