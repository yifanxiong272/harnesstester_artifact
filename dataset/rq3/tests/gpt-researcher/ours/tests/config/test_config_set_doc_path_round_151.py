import builtins
import pytest
from gpt_researcher.config.config import Config
from gpt_researcher.config.variables.default import DEFAULT_CONFIG


def test_set_doc_path_empty_round_151():
    """When DOC_PATH is falsy, validate_doc_path must NOT be called and doc_path remains that falsy value."""
    # Create instance without invoking heavy __init__ logic
    cfg = object.__new__(Config)

    # Prepare input where DOC_PATH is empty string (falsy)
    cfg._set_doc_path({'DOC_PATH': ''})

    # The method should set the attribute directly and skip validation
    assert hasattr(cfg, 'doc_path')
    assert cfg.doc_path == ''


def test_set_doc_path_validate_success_round_151():
    """When DOC_PATH is truthy and validate_doc_path succeeds, it should be called and doc_path preserved."""
    cfg = object.__new__(Config)

    called = {'count': 0}

    def fake_validate():
        called['count'] += 1
        # succeed silently
        return None

    # attach fake validator to the instance
    cfg.validate_doc_path = fake_validate

    cfg._set_doc_path({'DOC_PATH': '/some/path'})

    # validate_doc_path should have been invoked exactly once
    assert called['count'] == 1
    # doc_path should remain the value provided
    assert cfg.doc_path == '/some/path'


def test_set_doc_path_validate_error_round_151(capsys):
    """When validate_doc_path raises, the exception is caught, a warning printed, and default used."""
    cfg = object.__new__(Config)

    def raising_validate():
        raise ValueError("boom")

    cfg.validate_doc_path = raising_validate

    cfg._set_doc_path({'DOC_PATH': '/bad/path'})

    # After exception, doc_path should be replaced with the DEFAULT_CONFIG value
    assert cfg.doc_path == DEFAULT_CONFIG['DOC_PATH']

    # Verify printed warning contains the exception message and mentions default usage
    captured = capsys.readouterr()
    assert "Warning: Error validating doc_path" in captured.out
    assert "boom" in captured.out
    assert "Using default doc_path" in captured.out
