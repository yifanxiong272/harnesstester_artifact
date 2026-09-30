from types import SimpleNamespace
from browser_use.agent.views import AgentHistoryList


def test_probe_001_no_crash_on_empty_result_list():
    """Boundary: boundary-001

    Construct an AgentHistoryList without running __init__ and set history to
    a list whose last element has result == []. Calling final_result() should
    not raise and should return None.
    """

    # Construct instance without heavy initialization
    inst = AgentHistoryList.__new__(AgentHistoryList)

    # Bypass pydantic's __setattr__ (which requires internal init state) and
    # directly set the attribute on the instance to avoid AttributeError.
    object.__setattr__(inst, 'history', [SimpleNamespace(result=[])])

    # Exercise the public entrypoint; if it raises, the test will fail (reveals bug)
    result = inst.final_result()

    # Primary oracle: final_result must return None and not raise
    assert result is None, f"expected None when last history entry has empty result list, got: {result!r}"
