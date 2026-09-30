from types import SimpleNamespace
from gpt_researcher.agent import GPTResearcher


def test_adds_mcp_to_list_retrievers_round_125():
    # existing list of retrievers should receive 'mcp' appended
    cfg = SimpleNamespace(retrievers=["alpha", "beta"])
    fake_self = SimpleNamespace(cfg=cfg)
    mcp_payload = [{"url": "http://example-mcp"}]

    # call unbound function with a lightweight fake self
    GPTResearcher._process_mcp_configs(fake_self, mcp_payload)

    assert fake_self.cfg.retrievers == ["alpha", "beta", "mcp"]
    # mcp_configs stored exactly as passed
    assert fake_self.mcp_configs is mcp_payload


def test_no_duplicate_when_mcp_already_present_round_125():
    # when 'mcp' already present, it must not be added again
    existing_list = ["mcp", "alpha"]
    cfg = SimpleNamespace(retrievers=existing_list)
    fake_self = SimpleNamespace(cfg=cfg)

    GPTResearcher._process_mcp_configs(fake_self, [])

    # same list object preserved and 'mcp' occurs only once
    assert fake_self.cfg.retrievers is existing_list
    assert fake_self.cfg.retrievers.count("mcp") == 1
    assert fake_self.mcp_configs == []


def test_string_retrievers_parsed_and_appended_round_125():
    # string retrievers (comma-separated with spaces/empty parts) should be parsed
    cfg = SimpleNamespace(retrievers="alpha, beta, ,gamma")
    fake_self = SimpleNamespace(cfg=cfg)
    payload = [{"k": "v"}]

    GPTResearcher._process_mcp_configs(fake_self, payload)

    assert isinstance(fake_self.cfg.retrievers, list)
    assert fake_self.cfg.retrievers == ["alpha", "beta", "gamma", "mcp"]
    assert fake_self.mcp_configs == payload


def test_empty_retrievers_attribute_sets_mcp_round_125():
    # existing attribute but falsy (empty list) should trigger the else branch
    cfg = SimpleNamespace(retrievers=[])
    fake_self = SimpleNamespace(cfg=cfg)
    GPTResearcher._process_mcp_configs(fake_self, ["cfg"])

    assert fake_self.cfg.retrievers == ["mcp"]
    assert fake_self.mcp_configs == ["cfg"]


def test_missing_retrievers_attribute_sets_mcp_round_125():
    # missing retrievers attribute on cfg should also set retrievers to ['mcp']
    cfg = SimpleNamespace()  # no retrievers attribute
    fake_self = SimpleNamespace(cfg=cfg)

    GPTResearcher._process_mcp_configs(fake_self, [])

    assert fake_self.cfg.retrievers == ["mcp"]
    assert fake_self.mcp_configs == []
