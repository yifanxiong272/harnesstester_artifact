import types
import json
from browser_use.agent.views import AgentHistory


def test_probe_001():
    # Deterministic secrets and mapping
    secret1 = "secret123"
    secret2 = "nested_secret"

    # sensitive_data values may be strings or dicts per the public signature; include both forms
    sensitive_data = {
        secret1: "[REDACTED]",
        secret2: {"redaction": "[REDACTED2]"},
    }

    # Payload embeds secrets in multiple places, including a nested list (list inside a list)
    payload = {
        "public": "value",
        "nested_list": [[secret1]],                # list inside list -> target boundary
        "nested_dict": {"inner": secret2},       # dict branch should be redacted
        "mixed": ["ok", {"k": secret1}, [[secret2]]],
    }

    # Monkeypatch the public entrypoint model_dump so it exercises the real private filter
    original_model_dump = AgentHistory.model_dump

    def model_dump_stub(self, sensitive_data=None, **kwargs):
        # Create a minimal dummy 'self' that has the two filtering methods bound from the real class.
        # This avoids needing to construct a full AgentHistory instance while still exercising
        # the target methods from the real class implementation.
        class Dummy:
            pass

        d = Dummy()
        # Bind the class methods to the dummy instance so calls inside the implementation resolve
        d._filter_sensitive_data_from_string = types.MethodType(
            AgentHistory._filter_sensitive_data_from_string, d
        )
        d._filter_sensitive_data_from_dict = types.MethodType(
            AgentHistory._filter_sensitive_data_from_dict, d
        )
        # Call the real private filter against our crafted payload
        return d._filter_sensitive_data_from_dict(payload, sensitive_data)

    AgentHistory.model_dump = model_dump_stub
    try:
        # Call the public entrypoint. We pass None as the usual instance because the stub ignores it.
        result = AgentHistory.model_dump(None, sensitive_data=sensitive_data)
    finally:
        # Restore original to avoid side effects for other tests
        AgentHistory.model_dump = original_model_dump

    # Observable representation of the returned structure
    dumped = json.dumps(result, ensure_ascii=False)

    # Primary oracle: no sensitive literal should appear verbatim in the output
    for secret in (secret1, secret2):
        assert secret not in dumped, (
            f"Sensitive literal {secret!r} found in dumped output: {dumped}"
        )
