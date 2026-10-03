from aider.repo import GitRepo
from aider.io import InputOutput
from aider.utils import GitTemporaryDirectory
import git


def test_probe_001():
    """Probe: a whitespace-only model reply should be treated as absent and the next model used.

    This test constructs two deterministic stub models and a temporary git repo, then
    calls GitRepo.get_commit_message. The first stub returns only whitespace; the
    second returns a visible message. The invariant is that whitespace-only replies
    are considered empty after trimming and should not short-circuit the model loop.
    """

    class StubModel:
        def __init__(self, name, response):
            self.name = name
            self.system_prompt_prefix = None
            self._response = response
            # info left empty so max_input_tokens is falsy and the model won't be skipped
            self.info = {}
            self._calls = []

        def token_count(self, messages):
            # record messages for deterministic evidence and return small token count
            self._calls.append(("token_count", messages))
            return 1

        def simple_send_with_retries(self, messages):
            # record that we were asked and return the predetermined response
            self._calls.append(("send", messages))
            return self._response

    # First model returns only whitespace (should be treated as no reply after stripping)
    m1 = StubModel("model-1", "   \n")
    # Second model returns a visible non-empty commit message
    m2 = StubModel("model-2", "a correct commit")

    # Use a temporary git repo so GitRepo __init__ finds a repository deterministically
    with GitTemporaryDirectory():
        # ensure a git.Repo exists in the temp dir (GitTemporaryDirectory test helper provides this)
        _ = git.Repo()

        # Construct GitRepo with our stub models
        repo = GitRepo(InputOutput(), None, None, models=[m1, m2])

        # Invoke the declared public entrypoint
        result = repo.get_commit_message("dummy diff", "dummy context")

    # Primary oracle: the returned message must equal the second model's message
    assert result == "a correct commit", (
        f"Invariant violated: expected to skip whitespace-only reply and return second model's message, got: {result!r}"
    )

    # Observable evidence: both models should have been queried via simple_send_with_retries
    send_calls = sum(
        1
        for m in (m1, m2)
        for c in getattr(m, "_calls", [])
        if c[0] == "send"
    )
    assert send_calls == 2, f"Expected both models to be queried (2 sends) but found {send_calls}"
