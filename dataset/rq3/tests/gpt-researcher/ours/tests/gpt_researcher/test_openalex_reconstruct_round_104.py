import pytest

from gpt_researcher.retrievers.openalex.openalex import OpenAlexSearch


def test_none_and_empty_round_104():
    # Falsy inputs should return None (covers line 110 -> 111)
    assert OpenAlexSearch._reconstruct_abstract(None) is None
    assert OpenAlexSearch._reconstruct_abstract({}) is None


def test_single_word_single_index_round_104():
    # Single word at position 0 reconstructs to that single token
    inverted = {"hello": [0]}
    assert OpenAlexSearch._reconstruct_abstract(inverted) == "hello"


def test_multiple_words_with_empty_indexes_round_104():
    # One word has an empty index list (inner loop skipped for that entry),
    # other entries produce positions that must be sorted by position.
    inverted = {"empty": [], "world": [1], "hello": [0]}
    # After gathering positions and sorting by index: 0->hello,1->world
    assert OpenAlexSearch._reconstruct_abstract(inverted) == "hello world"


def test_unsorted_indexes_round_104():
    # Index lists may be unsorted; positions are sorted globally by index
    inverted = {"a": [2, 0, 1], "b": [3]}
    # Collected positions (2,a),(0,a),(1,a),(3,b) sorted -> (0,a),(1,a),(2,a),(3,b)
    assert OpenAlexSearch._reconstruct_abstract(inverted) == "a a a b"
