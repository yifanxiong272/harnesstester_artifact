import types

import pytest

from sweagent.agent.reviewer import ChooserRetryLoop


def _make_loop_without_init():
    """Create a ChooserRetryLoop instance without running __init__ to avoid heavy dependencies.
    Tests will set only the attributes they need.
    """
    loop = object.__new__(ChooserRetryLoop)
    # Provide the minimal attribute the property and on_submit use
    loop._submissions = []
    return loop


def test_n_attempts_initial_and_on_submit_round_140():
    loop = _make_loop_without_init()

    # Initially there are no submissions
    assert loop._n_attempts == 0

    # on_submit should append an item and increase the attempts count deterministically
    loop.on_submit(object())
    assert loop._n_attempts == 1

    # Multiple submissions accumulate
    sentinel1 = ("s1", 1)
    sentinel2 = ("s2", 2)
    loop.on_submit(sentinel1)
    loop.on_submit(sentinel2)
    assert loop._n_attempts == 3


def test_n_attempts_reflects_list_mutation_round_140():
    loop = _make_loop_without_init()

    # Pre-populate the underlying list to simulate prior submissions
    loop._submissions = ["a", "b", "c"]
    assert loop._n_attempts == 3

    # Mutating the list is reflected by the property
    loop._submissions.pop()
    assert loop._n_attempts == 2

    # Extending the list increases the count
    loop._submissions.extend(["d", "e"])
    assert loop._n_attempts == 4
