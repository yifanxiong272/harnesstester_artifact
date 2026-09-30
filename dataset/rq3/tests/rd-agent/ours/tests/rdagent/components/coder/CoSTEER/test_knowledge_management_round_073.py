import types
import re
from types import SimpleNamespace

import pytest

from rdagent.components.coder.CoSTEER.knowledge_management import (
    CoSTEERRAGStrategyV2,
)

# Helper stub node with .content attribute to mimic graph nodes
class NodeStub:
    def __init__(self, content):
        self.content = content


analyze_error_fn = CoSTEERRAGStrategyV2.analyze_error


def make_self_with_nodes(node_list):
    """Create a fake self with knowledgebase.graph.get_all_nodes_by_label_list stubbed."""
    graph = SimpleNamespace(get_all_nodes_by_label_list=lambda labels: list(node_list))
    kb = SimpleNamespace(graph=graph)
    self = SimpleNamespace(knowledgebase=kb)
    return self


def test_execution_no_match_round_073():
    # execution feedback that does not match the detailed traceback regex -> Undefined Error
    dummy = make_self_with_nodes([])
    single_feedback = "some totally unrelated error output that doesn't match"
    result = analyze_error_fn(dummy, single_feedback, feedback_type="execution")
    assert result == ["Undefined Error"]


def test_value_feedback_no_nodes_round_073():
    # value feedback should use the value_check_types pattern and return matches when no nodes exist
    dummy = make_self_with_nodes([])
    # choose one of the alternatives from value_check_types
    msg = "No sufficient correlation found when shifting up"
    result = analyze_error_fn(dummy, msg, feedback_type="value")
    # re.findall should capture the exact substring
    assert result == [msg]


def test_execution_nodes_duplicate_pop_round_073():
    # when regex matches and graph has multiple nodes none of which match the constructed error content,
    # the code will append the same content multiple times and then pop duplicates, final single entry expected
    # craft a traceback-like single_feedback that fits the regex in the implementation
    single_feedback = 'File "foo.py", line 10, in bar\n    x = 1/0\nZeroDivisionError: division by zero'
    # expected error content created by the method
    expected_error_content = "ErrorType: ZeroDivisionError\nError line: x = 1/0"

    # two nodes with contents different from expected_error_content cause content to be appended twice
    nodes = [NodeStub("other_a"), NodeStub("other_b")]
    dummy = make_self_with_nodes(nodes)

    result = analyze_error_fn(dummy, single_feedback, feedback_type="execution")

    # final deduplicated list should contain exactly one copy of the error content string
    assert result == [expected_error_content]


def test_execution_node_match_round_073():
    # when a node content equals the constructed error content, the node object itself should be returned
    single_feedback = 'File "mod.py", line 42, in func\n    data = open(\"x\")\nIOError: cannot open file'
    expected_error_content = "ErrorType: IOError\nError line: data = open(\"x\")"

    # create a node whose content matches the expected_error_content
    matching_node = NodeStub(expected_error_content)
    # also include another non-matching node to exercise the branch that appends content string for non-matches
    other_node = NodeStub("not matching")
    dummy = make_self_with_nodes([matching_node, other_node])

    result = analyze_error_fn(dummy, single_feedback, feedback_type="execution")

    # The matching node should appear in the returned list (as the actual node object)
    # and duplicates should be handled; ensure returned list contains the node and not its string content
    assert any(hasattr(item, 'content') and item is matching_node for item in result), "Matching node not present"
    # also ensure there are no duplicate identical last-element pops remaining
    # (final list should not contain the same object twice)
    assert len(result) == len(list(dict.fromkeys(result)))
