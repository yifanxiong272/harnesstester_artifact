import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from rdagent.log.ui.utils import trace_figure


def test_trace_figure_path_round_019(monkeypatch):
    """Path branch: ensure spiral-layout branch is exercised and idx2loop_id + merge_loops coloring applied.

    Patches nx.draw to capture the computed pos and node_color, and patches nx.is_path to force the path branch.
    """
    captured = {}

    def fake_draw(G, pos, with_labels=True, arrows=True, node_color=None, node_size=None, font_size=None, ax=None):
        # capture the position mapping and colors for assertions
        captured['pos'] = dict(pos)
        captured['node_color'] = list(node_color)
        captured['nodes'] = list(G)

    # Force the path branch to execute
    monkeypatch.setattr('rdagent.log.ui.utils.nx.draw', fake_draw)
    monkeypatch.setattr('rdagent.log.ui.utils.nx.is_path', lambda G, nodes: True)

    class DummyTrace:
        def __init__(self):
            # idx2loop_id ensures get_display_name follows the idx2loop_id branch for index 1
            self.idx2loop_id = {1: 99}
            # dag_parent: node0 root, node1 child of 0, node2 child of 1 -> a linear path
            self.dag_parent = [[], [0], [1]]

        def get_parents(self, i):
            return self.dag_parent[i]

    trace = DummyTrace()
    fig = trace_figure(trace, merge_loops=[1])

    # Assertions: ensure draw was called and positions captured
    assert 'pos' in captured, "nx.draw was not called or pos not captured"
    pos = captured['pos']

    # Expect the display names: index 0 -> L0, index 1 -> L99 (1), index 2 -> L2
    expected_nodes = {'L0', 'L99 (1)', 'L2'}
    assert set(pos.keys()) == expected_nodes

    # The node_color should include exactly one 'tomato' since merge_loops=[1]
    node_colors = captured['node_color']
    assert node_colors.count('tomato') == 1
    # And other colors should be 'skyblue'
    assert all(c in ('tomato', 'skyblue') for c in node_colors)

    plt.close(fig)


def test_trace_figure_nonpath_round_019(monkeypatch):
    """Non-path branch: exercise grouping by ancestor-level, sorting roots numerically and children by parent average.

    Patches nx.draw to capture the computed pos so we can assert expected coordinates.
    """
    captured = {}

    def fake_draw(G, pos, with_labels=True, arrows=True, node_color=None, node_size=None, font_size=None, ax=None):
        captured['pos'] = dict(pos)
        captured['node_color'] = list(node_color) if node_color is not None else None

    # Force the non-path branch
    monkeypatch.setattr('rdagent.log.ui.utils.nx.draw', fake_draw)
    monkeypatch.setattr('rdagent.log.ui.utils.nx.is_path', lambda G, nodes: False)

    class DummyTrace2:
        def __init__(self):
            # node0 and node1 are roots, node2 is child of both -> tests parent_avg_pos and child placement
            self.dag_parent = [[], [], [0, 1]]

        def get_parents(self, i):
            return self.dag_parent[i]

    trace = DummyTrace2()
    fig = trace_figure(trace, merge_loops=[])

    assert 'pos' in captured, "nx.draw was not called or pos not captured"
    pos = captured['pos']

    # Root nodes (level 0) should be placed at x positions 0 and 1 (in numeric order)
    assert 'L0' in pos and 'L1' in pos and 'L2' in pos
    assert pos['L0'][0] == 0
    assert pos['L1'][0] == 1

    # Child L2 should be placed below (y = -lvl) and centered under parents: avg parent x = 0.5
    # Expected x for single child of that level is avg_x + 0 => 0.5
    assert abs(pos['L2'][0] - 0.5) < 1e-6
    # Level for node 2 is len(get_parents(2)) == 2 => y should be -2
    assert pos['L2'][1] == -2

    plt.close(fig)
