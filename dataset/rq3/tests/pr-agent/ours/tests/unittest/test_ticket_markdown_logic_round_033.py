import pytest

import pr_agent.algo.utils as utils


class LoggerMock:
    def __init__(self):
        self.debug_calls = []
        self.exception_calls = []

    def debug(self, msg, **kwargs):
        # store message and kwargs for assertions
        self.debug_calls.append((msg, kwargs))

    def exception(self, msg):
        self.exception_calls.append(msg)


class SettingsMock:
    def __init__(self):
        self.set_calls = []

    def set(self, key, value):
        self.set_calls.append((key, value))


def _apply_mocks(logger_mock, settings_mock):
    # Patch the symbols where ticket_markdown_logic resolves them
    utils.get_logger = lambda: logger_mock
    utils.get_settings = lambda: settings_mock


def test_skip_empty_requirements_round_033():
    logger = LoggerMock()
    settings = SettingsMock()
    _apply_mocks(logger, settings)

    # Ticket with no compliant or non-compliant text -> should be skipped
    ticket_value = [
        {
            'ticket_url': ' http://example.com/123 ',
            'fully_compliant_requirements': '',
            'not_compliant_requirements': '',
            'requires_further_human_verification': ''
        }
    ]

    original = "Initial text"
    out = utils.ticket_markdown_logic('🔔', original, ticket_value, gfm_supported=True)

    # No changes should be made to markdown text when the ticket had no requirements
    assert out == original

    # The logger.debug should have been called to indicate no requirements
    assert any("Ticket compliance has no requirements" in call[0] for call in logger.debug_calls)
    # Check artifact contains stripped ticket url
    found = False
    for _, kwargs in logger.debug_calls:
        artifact = kwargs.get('artifact', {})
        if artifact.get('ticket_url') == 'http://example.com/123':
            found = True
    assert found


def test_partially_compliant_gfm_round_033():
    logger = LoggerMock()
    settings = SettingsMock()
    _apply_mocks(logger, settings)

    ticket_value = [
        {
            'ticket_url': 'https://example.com/PR-1',
            'fully_compliant_requirements': 'Requirement A satisfied',
            'not_compliant_requirements': 'Requirement B missing',
            'requires_further_human_verification': ''
        }
    ]

    out = utils.ticket_markdown_logic('E', '', ticket_value, gfm_supported=True)

    # For a single Partially compliant ticket, the aggregate should be Partially compliant
    # and the returned markdown should be a table row (gfm_supported True)
    assert '<tr><td>' in out
    # The black circle emoji for Partially compliant should be present
    assert '\ud83d\udd36' in out or '🔵' in out or 'Ticket compliance analysis' in out
    # Explanation should include both compliant and non-compliant sections
    assert 'Compliant requirements' in out
    assert 'Non-compliant requirements' in out

    # Settings should have been updated with the aggregated compliance level
    assert any(call[0] == 'config.extra_statistics' and call[1].get('compliance_level') == 'Partially compliant' for call in settings.set_calls)


def test_mixed_fully_and_not_compliant_non_gfm_round_033():
    logger = LoggerMock()
    settings = SettingsMock()
    _apply_mocks(logger, settings)

    ticket_value = [
        {
            'ticket_url': 'https://example.com/PR-fully',
            'fully_compliant_requirements': 'All good',
            'not_compliant_requirements': '',
            'requires_further_human_verification': ''
        },
        {
            'ticket_url': 'https://example.com/PR-not',
            'fully_compliant_requirements': '',
            'not_compliant_requirements': 'Broken',
            'requires_further_human_verification': ''
        }
    ]

    out = utils.ticket_markdown_logic('T', '', ticket_value, gfm_supported=False)

    # Non-GFM path uses headings
    assert out.startswith('###') or 'Ticket compliance analysis' in out
    # Since there's a mix of Fully compliant and Not compliant the overall should be Partially compliant
    assert any(call[0] == 'config.extra_statistics' and call[1].get('compliance_level') == 'Partially compliant' for call in settings.set_calls)
    # Both ticket shortnames should appear
    assert 'PR-fully' in out
    assert 'PR-not' in out


def test_pr_code_verified_round_033():
    logger = LoggerMock()
    settings = SettingsMock()
    _apply_mocks(logger, settings)

    ticket_value = [
        {
            'ticket_url': 'https://example.com/PR-verify',
            'fully_compliant_requirements': 'ok',
            'not_compliant_requirements': '',
            'requires_further_human_verification': 'manual check required'
        }
    ]

    out = utils.ticket_markdown_logic('V', '', ticket_value, gfm_supported=True)

    # The ticket should appear and the explanation should mention human verification
    assert 'Requires further human verification' in out
    # Because the only entry is PR Code Verified, the aggregate should be PR Code Verified
    assert any(call[0] == 'config.extra_statistics' and call[1].get('compliance_level') == 'PR Code Verified' for call in settings.set_calls)


def test_exception_in_ticket_processing_round_033():
    logger = LoggerMock()
    settings = SettingsMock()
    _apply_mocks(logger, settings)

    class BadTicket:
        def get(self, *args, **kwargs):
            raise RuntimeError('boom')

    ticket_value = [BadTicket()]

    out = utils.ticket_markdown_logic('X', 'prefix', ticket_value, gfm_supported=True)

    # On exception, output should remain the original
    assert out == 'prefix'
    # And the logger.exception should have been called
    assert any('Failed to process ticket compliance' in msg or 'boom' in msg or logger.exception_calls for msg in logger.exception_calls)
