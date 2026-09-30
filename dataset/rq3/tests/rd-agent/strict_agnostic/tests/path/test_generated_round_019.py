import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pytest

from rdagent.log.ui.utils import trace_figure


class DummyTracePath:
    """Minimal trace-like object representing a simple path (chain) of nodes.

    dag_parent is a list where index is node id and value is list of parent ids.
    get_parents(i) returns the same parents list for compatibility with the real Trace.
    """

    def __init__(self, dag_parent):
        self.dag_parent = dag_parent

    def get_parents(self, idx):
        return list(self.dag_parent[idx])


class DummyTraceBranching:
    """Minimal trace-like object representing a branching DAG.

    Also optionally provides idx2loop_id so get_display_name produces the
    "L{loopid} ({idx})" format for specified indices.
    """

    def __init__(self, dag_parent, idx2loop_id=None):
        self.dag_parent = dag_parent
        self.idx2loop_id = idx2loop_id or {}

    def get_parents(self, idx):
        return list(self.dag_parent[idx])


def _node_labels_from_axis(ax):
    # networkx.draw(with_labels=True) adds text objects for each node
    return [t.get_text() for t in ax.texts]


def _node_colors_from_axis(ax):
    # the node collection is usually the first PathCollection in ax.collections
    if not ax.collections:
        return []
    return ax.collections[0].get_facecolors()


def test_trace_figure_path_round_019():
    # Create a simple linear chain of 6 nodes: 0 -> 1 -> 2 -> 3 -> 4 -> 5
    dag_parent = [[], [0], [1], [2], [3], [4]]
    trace = DummyTracePath(dag_parent)

    # Call the function under test
    fig = trace_figure(trace)

    try:
        assert isinstance(fig, matplotlib.figure.Figure)
        assert fig.axes, "figure should contain axes"
        ax = fig.axes[0]

        # The node collection should have one entry per node
        offsets = ax.collections[0].get_offsets()
        assert offsets.shape[0] == len(dag_parent)

        # There should be a facecolor per node
        facecolors = ax.collections[0].get_facecolors()
        assert facecolors.shape[0] == len(dag_parent)

        # Since we didn't pass merge_loops, all nodes should be the default color (skyblue)
        skyblue_rgba = mcolors.to_rgba("skyblue")
        # Compare first node color to expected skyblue color
        assert tuple(facecolors[0]) == pytest.approx(tuple(skyblue_rgba))
    finally:
        plt.close(fig)


def test_trace_figure_non_path_with_idx2loop_round_019():
    # Create a branching DAG:
    # 0 is root
    # 1 and 2 are children of 0 (siblings)
    # 3 is child of both 1 and 2
    # Provide idx2loop_id for index 2 so get_display_name returns "L{loopid} ({idx})"
    dag_parent = [[], [0], [0], [1, 2]]
    idx2loop_id = {2: 99}
    trace = DummyTraceBranching(dag_parent, idx2loop_id=idx2loop_id)

    # Mark loop index 2 as merged (should be colored 'tomato')
    fig = trace_figure(trace, merge_loops=[2])

    try:
        assert isinstance(fig, matplotlib.figure.Figure)
        ax = fig.axes[0]

        labels = _node_labels_from_axis(ax)
        # The special label for index 2 should appear
        expected_label_for_2 = f"L{idx2loop_id[2]} (2)"
        assert expected_label_for_2 in labels

        # Get colors and ensure the node with that label is colored tomato
        facecolors = _node_colors_from_axis(ax)
        assert facecolors.shape[0] == len(dag_parent)

        # Determine the index of the special label among the drawn nodes
        label_index = labels.index(expected_label_for_2)
        tomato_rgba = mcolors.to_rgba("tomato")

        # Compare the facecolor at the same index
        assert tuple(facecolors[label_index]) == pytest.approx(tuple(tomato_rgba))

    finally:
        plt.close(fig)
