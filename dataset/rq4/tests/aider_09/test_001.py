from aider.repo import GitRepo
from aider.io import InputOutput
from aider.utils import GitTemporaryDirectory
import git


class DummyModel:
    """Minimal model-like object used to deterministically exercise get_commit_message loop.

    Attributes expected by GitRepo.get_commit_message:
      - name: used for spinner text
      - system_prompt_prefix: optionally prepended to system content
      - info: dict that may contain 'max_input_tokens'
      - token_count(messages): returns an int
      - simple_send_with_retries(messages): returns the model reply (string)
    """

    def __init__(self, name, reply, system_prompt_prefix=None, max_input_tokens=None):
        self.name = name
        self._reply = reply
        self.system_prompt_prefix = system_prompt_prefix
        self.info = {}
        if max_input_tokens is not None:
            self.info["max_input_tokens"] = max_input_tokens
        # record messages passed for assertions
        self.sent_messages = []

    def token_count(self, messages):
        # Deterministic small token count so max_input_tokens checks do not skip models
        return 1

    def simple_send_with_retries(self, messages):
        # Record the exact messages received and return the configured reply
        self.sent_messages.append(messages)
        return self._reply


def test_probe_001_whitespace_model_response_is_ignored_and_next_model_used():
    """Invariant: whitespace-only LLM responses should be treated as absent.

    The original generated test attempted to construct a GitRepo outside of any
    git repository and raised FileNotFoundError in the constructor. Repair by
    creating a deterministic temporary git repo (GitTemporaryDirectory) so the
    real GitRepo initializer succeeds while keeping all model interactions
    in-process and deterministic.
    """

    # Arrange: two models; first returns only whitespace, second returns a message
    first = DummyModel("model-1", "   ")
    second = DummyModel("model-2", "  a good commit message  ")

    # Ensure we are inside a git repo so GitRepo.__init__ does not raise
    with GitTemporaryDirectory():
        # create an actual repo in the temp directory
        git.Repo()

        # Use the real GitRepo entrypoint; pass a real InputOutput to satisfy __init__.
        repo = GitRepo(InputOutput(), None, None, models=[first, second])

        # Act
        result = repo.get_commit_message("dummy diffs", "dummy context")

        # Primary oracle: the function must return the second model's stripped message
        assert result == "a good commit message", (
            "Expected get_commit_message to ignore a whitespace-only first reply and "
            f"return the second model's stripped message, but got: {result!r}"
        )

        # Additional observable checks (supporting evidence): both models should have been invoked exactly once
        assert len(first.sent_messages) == 1, "First model was not invoked exactly once"
        assert len(second.sent_messages) == 1, "Second model was not invoked exactly once"
