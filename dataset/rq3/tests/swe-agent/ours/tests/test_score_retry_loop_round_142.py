from sweagent.agent.reviewer import ScoreRetryLoop


def test_n_attempts_empty_round_142():
    """If _submissions is an empty sequence, _n_attempts should be 0."""
    inst = object.__new__(ScoreRetryLoop)
    # set a minimal submissions container
    inst._submissions = []
    assert inst._n_attempts == 0


def test_n_attempts_varied_container_round_142():
    """_n_attempts returns the length of whatever sequence-like container is stored.

    Use different container types to ensure the implementation simply forwards to len().
    """
    inst = object.__new__(ScoreRetryLoop)
    inst._submissions = ("a", "b", "c", "d")  # tuple supports len()
    assert inst._n_attempts == 4


def test_n_attempts_custom_len_round_142():
    """Custom object with __len__ should be respected by _n_attempts."""

    class Dummy:
        def __len__(self):
            return 7

    inst = object.__new__(ScoreRetryLoop)
    inst._submissions = Dummy()
    assert inst._n_attempts == 7
