import sys
import importlib
from types import SimpleNamespace, ModuleType
import builtins
import math
import numpy as np

# Fake torch implementation sufficient for this unit under test
class FakeTensor:
    def __init__(self, array):
        self.array = np.array(array)

    def __mul__(self, other):
        if isinstance(other, FakeTensor):
            return FakeTensor(self.array * other.array)
        return FakeTensor(self.array * other)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __add__(self, other):
        if isinstance(other, FakeTensor):
            return FakeTensor(self.array + other.array)
        return FakeTensor(self.array + other)

    def __sub__(self, other):
        if isinstance(other, FakeTensor):
            return FakeTensor(self.array - other.array)
        return FakeTensor(self.array - other)

    def __neg__(self):
        return FakeTensor(-self.array)

    def unsqueeze(self, dim):
        arr = np.expand_dims(self.array, axis=dim)
        return FakeTensor(arr)

    def squeeze(self, dim=None):
        if dim is None:
            return FakeTensor(np.squeeze(self.array))
        arr = np.squeeze(self.array, axis=dim)
        return FakeTensor(arr)

    def flatten(self):
        return FakeTensor(self.array.flatten())

    def unique(self):
        return FakeTensor(np.unique(self.array))

    def tolist(self):
        return self.array.tolist()

    def size(self, dim=None):
        if dim is None:
            return self.array.shape
        # mimic PyTorch .size(dim) behaviour for negative dims
        if dim < 0:
            dim = self.array.ndim + dim
        return self.array.shape[dim]

    def clamp(self, min=None, max=None):
        return FakeTensor(np.clip(self.array, a_min=min, a_max=max))

    def __getitem__(self, idx):
        res = self.array[idx]
        # if scalar, return python float/int for easier comparisons
        if np.isscalar(res):
            if isinstance(res, (np.floating, float)):
                return float(res)
            return int(res)
        return FakeTensor(res)

    def argmax(self):
        return int(np.argmax(self.array))

    def argmin(self):
        return int(np.argmin(self.array))

    def numpy(self):
        return self.array

    def __repr__(self):
        return f"FakeTensor({self.array!r})"


class FakeTorch(ModuleType):
    def __init__(self):
        super().__init__("torch")
        self.float32 = np.float32

    def tensor(self, data, dtype=None):
        # Ensure deterministic numpy arrays
        return FakeTensor(np.array(data, dtype=float))

    def tanh(self, x):
        if isinstance(x, FakeTensor):
            return FakeTensor(np.tanh(x.array))
        return FakeTensor(np.tanh(np.array(x, dtype=float)))

    def softmax(self, x, dim=1):
        # x is FakeTensor
        arr = x.array
        # compute softmax along given dim
        exp = np.exp(arr - np.max(arr, axis=dim, keepdims=True))
        s = exp / np.sum(exp, axis=dim, keepdims=True)
        return FakeTensor(s)

    def multinomial(self, probs, num_samples):
        # probs: FakeTensor with shape (rows, cols)
        arr = probs.array
        rows, cols = arr.shape
        # deterministic sampling: take top-k indices per row, but if num_samples > cols, wrap-around
        sampled = np.zeros((rows, num_samples), dtype=int)
        for r in range(rows):
            # argsort descending
            order = np.argsort(-arr[r])
            # if num_samples <= cols take first num_samples
            for k in range(num_samples):
                sampled[r, k] = order[k % cols]
        return FakeTensor(sampled)


# Fake APIBackend used by the module under test
class FakeAPIBackend:
    def create_embedding(self, texts):
        # deterministic embeddings: map each text to a small vector based on character codes
        embeddings = []
        for i, t in enumerate(texts):
            base = sum(ord(ch) for ch in t) % 10
            embeddings.append([base + 0.1 * (j + 1) for j in range(3)])
        return embeddings


# Helper to inject fake torch and patch the target module
def _import_target_module_with_fakes():
    # ensure our fake torch is used by imports inside the function under test
    fake_torch = FakeTorch()
    sys.modules['torch'] = fake_torch
    # now import the module under test
    mod = importlib.import_module('rdagent.scenarios.data_science.proposal.exp_gen.proposal')
    # patch APIBackend with our fake implementation
    setattr(mod, 'APIBackend', FakeAPIBackend)
    return mod


def test_prob_dis_torch_empty_history_round_051():
    mod = _import_target_module_with_fakes()

    # Create a lightweight self with required method
    def fake_cos_sim(A, B):
        # not called in this test because history is empty
        return FakeTensor([[0.0]])

    self = SimpleNamespace(_cosine_similarity_matrix_torch=fake_cos_sim)

    # empty extra_hypo_l should lead to early return [] (history empty)
    result = mod.DSProposalV2ExpGen._prob_dis_torch(
        self,
        current_sota_score_in_current_trace=0,
        extra_hypo_l=[],
        hypothesis_candidates={"a": {"hypothesis": "t1"}},
        competition={"metric": "acc"},
        path_length=5,
    )

    assert result == []


def test_prob_dis_torch_bigger_is_better_round_051():
    mod = _import_target_module_with_fakes()

    # build history of 4 hypotheses
    history_scores = [0.1, 0.9, 0.2, 0.8]
    history_objs = [SimpleNamespace(hypothesis=f"h{i}") for i in range(len(history_scores))]
    extra_hypo_l = list(zip(history_objs, history_scores))

    # create hypothesis candidates (targets) - 3 targets
    hypothesis_candidates = {
        't0': {'hypothesis': 'target0'},
        't1': {'hypothesis': 'target1'},
        't2': {'hypothesis': 'target2'},
    }

    # self._cosine_similarity_matrix_torch will produce a matrix shape (3 targets, 4 history)
    def fake_cos_sim(A, B):
        # A and B are FakeTensor instances; return a deterministic matrix
        # Values increasing along columns so argmax/argmin logic predictable
        num_targets = 3
        num_hist = 4
        mat = np.tile(np.linspace(0.1, 0.4, num_hist), (num_targets, 1))
        return FakeTensor(mat)

    self = SimpleNamespace(_cosine_similarity_matrix_torch=fake_cos_sim)

    # Force competition metric direction: bigger_is_better True
    mod.get_metric_direction = lambda competition: True

    # Call with current_sota_score_in_current_trace not equal -1 to exercise alpha/beta=1 path
    result = mod.DSProposalV2ExpGen._prob_dis_torch(
        self,
        current_sota_score_in_current_trace=0.5,
        extra_hypo_l=extra_hypo_l,
        hypothesis_candidates=hypothesis_candidates,
        competition={"metric": "acc"},
        path_length=10,
    )

    # First element must be the best_entry derived from history_scores argmax
    expected_best_idx = int(np.argmax(history_scores))
    assert result[0][0] == f"h{expected_best_idx}"
    # value should match original history score (float)
    assert abs(float(result[0][1]) - history_scores[expected_best_idx]) < 1e-6

    # Because history had 4 unique indices sampled, sliced results should be at most 3 entries
    assert 1 < len(result) <= 3


def test_prob_dis_torch_smaller_is_better_with_neg_sota_round_051():
    mod = _import_target_module_with_fakes()

    # history of 3 hypotheses
    history_scores = [0.5, 0.2, 0.8]
    history_objs = [SimpleNamespace(hypothesis=f"hh{i}") for i in range(len(history_scores))]
    extra_hypo_l = list(zip(history_objs, history_scores))

    hypothesis_candidates = {
        'a': {'hypothesis': 'X'},
        'b': {'hypothesis': 'Y'},
    }

    def fake_cos_sim(A, B):
        # small deterministic sim matrix
        return FakeTensor(np.array([[0.2, 0.1, 0.3], [0.25, 0.05, 0.4]]))

    self = SimpleNamespace(_cosine_similarity_matrix_torch=fake_cos_sim)

    # smaller-is-better branch
    mod.get_metric_direction = lambda competition: False

    # Trigger the special -1 SOTA case so beta becomes 0 (lines 965-966)
    result = mod.DSProposalV2ExpGen._prob_dis_torch(
        self,
        current_sota_score_in_current_trace=-1,
        extra_hypo_l=extra_hypo_l,
        hypothesis_candidates=hypothesis_candidates,
        competition={"metric": "loss"},
        path_length=3,
    )

    # For smaller-is-better the best entry is argmin of history_scores
    expected_best_idx = int(np.argmin(history_scores))
    assert result[0][0] == f"hh{expected_best_idx}"
    assert abs(float(result[0][1]) - history_scores[expected_best_idx]) < 1e-6
    # returned list should contain at least the best entry
    assert len(result) >= 1
