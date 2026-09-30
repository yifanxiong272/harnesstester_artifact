from rdagent.scenarios.data_science.proposal.exp_gen import base

DSTrace = base.DSTrace


class FakeExp:
    def __init__(self, local_selection):
        # local_selection should match the shape used by DSTrace (tuple or NEW_ROOT)
        self.local_selection = local_selection


class FakeTrace:
    NEW_ROOT = ()

    def __init__(self, current_selection, dag_parent, uncommitted_experiments, hist):
        # store values to be used by DSTrace.get_sibling_exps
        self._current_selection = current_selection
        self.dag_parent = dag_parent
        self.uncommitted_experiments = uncommitted_experiments
        self.hist = hist

    def get_current_selection(self):
        return self._current_selection


def test_get_sibling_exps_with_current_selection_none_round_095():
    # Setup:
    # - current_selection is None => get_current_selection() is used and returns NEW_ROOT
    # - dag_parent: index 0 is NEW_ROOT (skipped), index 1 depends on parent 0, index 2 depends on parents 0 and 1
    #   After processing dag_parent, only index 2 remains in touched_node_set
    # - uncommitted_experiments contains two exps: one whose local_selection points to parent 2 (so it removes 2),
    #   and one with local_selection == NEW_ROOT (so it yields no parent removal)
    exp_parent_idx_target = 2
    exp1 = FakeExp(local_selection=(exp_parent_idx_target,))
    exp2 = FakeExp(local_selection=FakeTrace.NEW_ROOT)

    dag_parent = [
        FakeTrace.NEW_ROOT,  # idx 0 -> treated as root and skipped
        (0,),                # idx 1 -> parent 0 will be removed from touched_node_set
        (0, 1),              # idx 2 -> parents 0 and 1 will be removed, leaving 2
    ]

    hist = [
        ["hist0"],
        ["hist1"],
        ["hist2"],
    ]

    uncommitted = {10: exp1, 11: exp2}

    fake = FakeTrace(current_selection=FakeTrace.NEW_ROOT, dag_parent=dag_parent, uncommitted_experiments=uncommitted, hist=hist)

    # Call the method under test via the original DSTrace.get_sibling_exps function object
    result = DSTrace.get_sibling_exps(fake, None)

    # Oracle: both uncommitted experiments are returned (in insertion order via dict.items())
    # and no hist entries remain because exp1 removed the last touched node (2)
    assert result == [exp1, exp2]


def test_get_sibling_exps_with_explicit_selection_excludes_leaf_round_095():
    # Setup:
    # - explicit current_selection not equal to NEW_ROOT -> ignore_leaf_idx should contain the first element
    # - dag_parent length 2: idx 0 is NEW_ROOT (skipped), idx 1 has parent 0 -> leaves {1}
    # - no uncommitted_experiments -> siblings are taken from hist for remaining touched nodes except ignored leaf
    dag_parent = [
        FakeTrace.NEW_ROOT,  # idx 0
        (0,),                # idx 1
    ]

    # hist values for indices
    hist_val0 = {
        "id": "c0"
    }
    hist_val1 = {
        "id": "c1"
    }
    hist = [[hist_val0], [hist_val1]]

    # choose a current selection that points at idx 1 so it will be ignored
    explicit_selection = (1,)

    fake = FakeTrace(current_selection=explicit_selection, dag_parent=dag_parent, uncommitted_experiments={}, hist=hist)

    result = DSTrace.get_sibling_exps(fake, explicit_selection)

    # After dag processing, touched_node_set contains {1}. Because 1 is in ignore_leaf_idx, it should be excluded.
    # Since there are no uncommitted experiments and the only touched node is ignored, result should be empty list.
    assert result == []
