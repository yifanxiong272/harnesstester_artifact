import sys
import types
import importlib
import pytest

# Import the module under test
import gpt_researcher.retrievers.duckduckgo.duckduckgo as dd_mod

class FakeDDGSuccess:
    def __init__(self):
        # record last call for assertions
        self.last_called = None

    def text(self, query, region='wt-wt', max_results=5):
        # Record the parameters and return a deterministic list of dicts
        self.last_called = {
            'query': query,
            'region': region,
            'max_results': max_results,
        }
        sample = [
            {'title': 't1', 'url': 'u1'},
            {'title': 't2', 'url': 'u2'},
            {'title': 't3', 'url': 'u3'},
        ]
        return sample[:max_results]

class FakeDDGRaises:
    def __init__(self):
        pass

    def text(self, query, region='wt-wt', max_results=5):
        # Deterministic exception to exercise the except branch
        raise Exception('boom')


def _install_fake_ddgs(fake_ddgs_cls):
    # Create a real module object and insert it into sys.modules so
    # "from ddgs import DDGS" inside Duckduckgo.__init__ will resolve to this.
    mod = types.ModuleType('ddgs')
    mod.DDGS = fake_ddgs_cls
    sys.modules['ddgs'] = mod
    return mod


def _remove_fake_ddgs():
    sys.modules.pop('ddgs', None)


def test_init_and_search_success_round_130(monkeypatch):
    # Patch the check_pkg used in the module to be a no-op to avoid environment dependencies
    monkeypatch.setattr(dd_mod, 'check_pkg', lambda pkg: None)

    # Install fake ddgs module that provides DDGS
    _install_fake_ddgs(FakeDDGSuccess)
    try:
        # Instantiate with explicit query_domains to cover that assignment
        dg = dd_mod.Duckduckgo('search term', query_domains=['example.com'])

        # Ensure attributes set in __init__ are correct (covers lines 10-14)
        assert isinstance(dg.ddg, FakeDDGSuccess)
        assert dg.query == 'search term'
        assert dg.query_domains == ['example.com']

        # Call search to exercise the success path (line 25)
        result = dg.search(max_results=1)
        assert isinstance(result, list)
        # The fake ddg returns deterministic items; ensure max_results honored
        assert result == [{'title': 't1', 'url': 'u1'}]

        # And verify the fake ddg received the expected arguments
        assert dg.ddg.last_called == {
            'query': 'search term',
            'region': 'wt-wt',
            'max_results': 1,
        }
    finally:
        _remove_fake_ddgs()


def test_search_handles_exception_round_130(monkeypatch, capsys):
    # Patch check_pkg to avoid environment dependency
    monkeypatch.setattr(dd_mod, 'check_pkg', lambda pkg: None)

    # Install fake ddgs that raises to exercise the except branch (lines 26-29)
    _install_fake_ddgs(FakeDDGRaises)
    try:
        dg = dd_mod.Duckduckgo('will fail')

        # When no query_domains provided, the __init__ sets it to None (line 14)
        assert dg.query_domains is None

        # Call search which will raise inside the ddg.text and should be caught
        result = dg.search(max_results=3)

        # Capture printed output and assert the error message was printed
        captured = capsys.readouterr()
        assert result == []
        assert 'Failed fetching sources' in captured.out
        # Ensure the original exception message is included in the printed line
        assert 'boom' in captured.out
    finally:
        _remove_fake_ddgs()
