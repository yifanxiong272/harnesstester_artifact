# file: pr_agent/algo/utils.py:368-462
# asked: {"lines": [386, 387, 388, 393, 398, 399, 400, 410, 412, 417, 418, 419, 420, 422, 423, 424, 431, 432, 433, 434, 436, 437, 438, 440, 441, 442, 443, 444, 446, 447, 459, 460], "branches": [[374, 462], [385, 386], [391, 399], [392, 393], [395, 398], [399, 400], [399, 403], [403, 407], [407, 409], [409, 410], [411, 412], [416, 417], [427, 453], [428, 431], [431, 432], [431, 434], [434, 436], [434, 442], [436, 437], [436, 440], [442, 443], [442, 446], [453, 459]]}
# gained: {"lines": [386, 387, 388, 393, 398, 399, 400, 410, 412, 417, 418, 419, 420, 422, 423, 424, 431, 432, 433, 434, 436, 437, 438, 442, 443, 444, 446, 447, 459, 460], "branches": [[374, 462], [385, 386], [391, 399], [392, 393], [395, 398], [399, 400], [407, 409], [409, 410], [411, 412], [416, 417], [427, 453], [428, 431], [431, 432], [431, 434], [434, 436], [434, 442], [436, 437], [442, 443], [442, 446], [453, 459]]}

import pytest

from pr_agent.algo import utils as utils_mod
from pr_agent.algo.utils import ticket_markdown_logic


class FakeLogger:
    def __init__(self):
        self.debug_calls = []
        self.exception_calls = []

    def debug(self, msg, artifact=None):
        self.debug_calls.append((msg, artifact))

    def exception(self, msg):
        self.exception_calls.append(msg)


class FakeSettings:
    def __init__(self):
        self.set_calls = []

    def set(self, key, value):
        self.set_calls.append((key, value))


def _patch_logger_and_settings(monkeypatch):
    fake_logger = FakeLogger()
    fake_settings = FakeSettings()
    # Patch the names imported in the module under test
    monkeypatch.setattr(utils_mod, "get_logger", lambda: fake_logger)
    monkeypatch.setattr(utils_mod, "get_settings", lambda: fake_settings)
    return fake_logger, fake_settings


def test_non_list_value_returns_original(monkeypatch):
    # Ensure that when value is not a list, the markdown_text is returned unchanged.
    fake_logger, fake_settings = _patch_logger_and_settings(monkeypatch)

    original_text = "original markdown"
    result = ticket_markdown_logic("🔧", original_text, value={"not": "a list"}, gfm_supported=False)

    assert result == original_text
    # Nothing should have been set
    assert fake_settings.set_calls == []


def test_empty_requirements_skips_ticket_and_logs_debug(monkeypatch):
    # Ticket with no fully_compliant_requirements and no not_compliant_requirements should be skipped
    fake_logger, fake_settings = _patch_logger_and_settings(monkeypatch)

    value = [
        {"ticket_url": "http://example.com/TICKET-1"}  # no requirement fields -> empty strings after .get(...).strip()
    ]
    md = "START\n"
    result = ticket_markdown_logic("E", md, value=value, gfm_supported=False)

    # Should log debug about no requirements
    assert any("Ticket compliance has no requirements" in call[0] for call in fake_logger.debug_calls)
    # Because ticket was skipped, no extra statistics should be set
    assert fake_settings.set_calls == []
    # Should still return markdown with header (non-gfm)
    assert result.startswith("START")
    assert "### E Ticket compliance analysis" in result


def test_various_compliance_levels_and_logging_gfm_true(monkeypatch):
    # Complex scenario: partially compliant, fully compliant, PR Code Verified, not compliant and a bad ticket raising exception.
    fake_logger, fake_settings = _patch_logger_and_settings(monkeypatch)

    class BadTicket:
        def get(self, *args, **kwargs):
            raise RuntimeError("boom")

    value = [
        # Partially compliant (both fully and not)
        {
            "ticket_url": "http://host/TCKT0",
            "fully_compliant_requirements": "OK requirement A",
            "not_compliant_requirements": "Missing something"
        },
        # Fully compliant
        {
            "ticket_url": "http://host/TCKT1",
            "fully_compliant_requirements": "All good",
            "not_compliant_requirements": ""
        },
        # PR Code Verified (fully + requires further)
        {
            "ticket_url": "http://host/TCKT2",
            "fully_compliant_requirements": "Some checks",
            "not_compliant_requirements": "",
            "requires_further_human_verification": "Please verify code formatting"
        },
        # Not compliant
        {
            "ticket_url": "http://host/TCKT3",
            "fully_compliant_requirements": "",
            "not_compliant_requirements": "Fails tests"
        },
        # This will raise inside the processing loop and trigger exception logging
        BadTicket()
    ]

    result = ticket_markdown_logic("EM", "", value=value, gfm_supported=True)

    # Ensure exception was logged for BadTicket
    assert any("Failed to process ticket compliance" in msg for msg in fake_logger.exception_calls)
    # Ensure the requires_further_human_verification debug was logged for TCKT2
    assert any("Ticket compliance requires further human verification" in call[0] for call in fake_logger.debug_calls)
    # Settings should be set to 'Partially compliant' because there is at least one 'Not compliant' and at least one 'Fully compliant'/'PR Code Verified'
    assert fake_settings.set_calls, "Expected settings.set to be called"
    last_key, last_val = fake_settings.set_calls[-1]
    assert last_key == "config.extra_statistics"
    assert last_val["compliance_level"] == "Partially compliant"
    # Result should contain GFM table wrapper and the compliance emoji for partially compliant
    assert result.startswith("<tr><td>")
    assert "Ticket compliance analysis 🔶" in result
    # Check that each ticket ID appears in the output with its compliance label
    assert "TCKT0" in result and "Partially compliant" in result
    assert "TCKT1" in result and "Fully compliant" in result
    assert "TCKT2" in result and "PR Code Verified" in result
    assert "TCKT3" in result and "Not compliant" in result


def test_all_pr_code_verified_non_gfm(monkeypatch):
    # Two tickets both PR Code Verified -> overall PR Code Verified branch (all PR Code Verified)
    fake_logger, fake_settings = _patch_logger_and_settings(monkeypatch)

    value = [
        {
            "ticket_url": "http://host/TCKT-A",
            "fully_compliant_requirements": "All good A",
            "not_compliant_requirements": "",
            "requires_further_human_verification": "verify A"
        },
        {
            "ticket_url": "http://host/TCKT-B",
            "fully_compliant_requirements": "All good B",
            "not_compliant_requirements": "",
            "requires_further_human_verification": "verify B"
        },
    ]

    result = ticket_markdown_logic("PR", "", value=value, gfm_supported=False)

    # Should set settings to PR Code Verified
    assert fake_settings.set_calls, "Expected settings.set to be called"
    last_key, last_val = fake_settings.set_calls[-1]
    assert last_key == "config.extra_statistics"
    assert last_val["compliance_level"] == "PR Code Verified"
    # Non-GFM header expected and check emoji
    assert "### PR Ticket compliance analysis ✅" in result
    # Ensure both ticket IDs are present with PR Code Verified label
    assert "TCKT-A" in result and "PR Code Verified" in result
    assert "TCKT-B" in result and "PR Code Verified" in result


def test_partially_compliant_without_notcomply(monkeypatch):
    # Single ticket that is Partially compliant should lead to overall Partially compliant via the any Partially branch
    fake_logger, fake_settings = _patch_logger_and_settings(monkeypatch)

    value = [
        {
            "ticket_url": "http://host/TCKT-P",
            "fully_compliant_requirements": "Good",
            "not_compliant_requirements": "Also some issues"
        }
    ]

    result = ticket_markdown_logic("P", "", value=value, gfm_supported=False)

    # Should set to Partially compliant
    assert fake_settings.set_calls, "Expected settings.set to be called"
    last_key, last_val = fake_settings.set_calls[-1]
    assert last_val["compliance_level"] == "Partially compliant"
    assert "### P Ticket compliance analysis 🔶" in result
    assert "TCKT-P" in result and "Partially compliant" in result


def test_mixed_fully_and_pr_default_to_pr_code_verified(monkeypatch):
    # Mixed Fully compliant and PR Code Verified (no Not, no Partially) should hit the default else -> PR Code Verified
    fake_logger, fake_settings = _patch_logger_and_settings(monkeypatch)

    value = [
        {
            "ticket_url": "http://host/TCKT-F",
            "fully_compliant_requirements": "Fully ok",
            "not_compliant_requirements": ""
        },
        {
            "ticket_url": "http://host/TCKT-R",
            "fully_compliant_requirements": "Looks good",
            "not_compliant_requirements": "",
            "requires_further_human_verification": "please review"
        },
    ]

    result = ticket_markdown_logic("MIX", "", value=value, gfm_supported=False)

    assert fake_settings.set_calls, "Expected settings.set to be called"
    last_key, last_val = fake_settings.set_calls[-1]
    # Because there's a mix of 'Fully compliant' and 'PR Code Verified' and no Not/Partially, the else branch should set to 'PR Code Verified'
    assert last_val["compliance_level"] == "PR Code Verified"
    assert "### MIX Ticket compliance analysis ✅" in result
    assert "TCKT-F" in result and "Fully compliant" in result
    assert "TCKT-R" in result and "PR Code Verified" in result
