import os
import pytest

from gpt_researcher.retrievers.pubmed_central.pubmed_central import PubMedCentralSearch


def test_no_api_key_round_140(monkeypatch, capsys):
    """When NCBI_API_KEY is not set, __init__ should print a warning and api_key should be falsy."""
    # Ensure the environment variable is absent
    monkeypatch.delenv('NCBI_API_KEY', raising=False)
    # Also ensure PUBMED_DB does not interfere (use default behavior)
    monkeypatch.delenv('PUBMED_DB', raising=False)

    instance = PubMedCentralSearch(query='test-query')

    captured = capsys.readouterr()
    # The constructor prints this warning when api key is missing
    assert "Warning: NCBI_API_KEY not set. Requests will be rate-limited." in captured.out
    # api_key should be the value returned by os.getenv when unset (None) or otherwise falsy
    assert not instance.api_key


def test_with_api_key_round_140(monkeypatch, capsys):
    """When NCBI_API_KEY is set, no warning should be printed and api_key should be preserved."""
    monkeypatch.setenv('NCBI_API_KEY', 'fake-key-123')
    # Explicitly set PUBMED_DB to ensure deterministic behavior for any subsequent logic
    monkeypatch.setenv('PUBMED_DB', 'pmc')

    instance = PubMedCentralSearch(query='another-query')

    captured = capsys.readouterr()
    # No warning should be printed when the API key is present
    assert "Warning: NCBI_API_KEY not set. Requests will be rate-limited." not in captured.out
    # api_key should match the environment value we set
    assert instance.api_key == 'fake-key-123'
