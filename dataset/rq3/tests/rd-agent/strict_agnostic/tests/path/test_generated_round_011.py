import json
from types import SimpleNamespace
import pytest

from rdagent.scenarios.qlib.proposal import quant_proposal


class FakePrompt:
    def __init__(self, key):
        self.key = key

    def r(self, **kwargs):
        # deterministic, observable return values depending on args
        if 'trace' in kwargs:
            return f"{self.key}:trace_len={len(kwargs['trace'].hist)}"
        if 'experiment' in kwargs and 'feedback' in kwargs:
            exp = kwargs['experiment']
            fb = kwargs['feedback']
            act = getattr(exp.hypothesis, 'action', None)
            dec = getattr(fb, 'decision', None)
            return f"{self.key}:exp={act}:dec={dec}"
        return f"{self.key}:called"


class FakeAPIBackend:
    def build_messages_and_create_chat_completion(self, user_prompt, system_prompt, json_mode=True):
        # Always return a JSON string with action "factor" to exercise the factor branch deterministically
        return json.dumps({"action": "factor"})


class FakeController:
    def __init__(self):
        self.recorded = None
        self.prev_action = None

    def record(self, metric, prev_action):
        # store inputs so tests can assert the call happened
        self.recorded = (metric, prev_action)

    def decide(self, metric):
        # deterministic decision based on metric contents (if any)
        if isinstance(metric, dict) and metric.get('favor') == 'model':
            return 'model'
        return 'factor'


class FakeTrace:
    def __init__(self, scen=None):
        self.scen = scen
        self.hist = []
        # controller used in bandit branch
        self.controller = FakeController()


def setup_common_mocks(monkeypatch):
    # Replace T, APIBackend, Trace in the module under test with deterministic fakes
    monkeypatch.setattr(quant_proposal, 'T', lambda key: FakePrompt(key))
    monkeypatch.setattr(quant_proposal, 'APIBackend', FakeAPIBackend)
    monkeypatch.setattr(quant_proposal, 'Trace', FakeTrace)


def make_exp(action):
    # Minimal fake experiment object with nested hypothesis action attribute
    return SimpleNamespace(hypothesis=SimpleNamespace(action=action))


def make_feedback(decision: bool):
    return SimpleNamespace(decision=decision)


def test_bandit_with_history_round_011(monkeypatch):
    """
    Exercising the bandit branch when history exists.
    Asserts that controller.record was called and decide result is honored.
    """
    setup_common_mocks(monkeypatch)

    # Ensure module uses bandit selection
    monkeypatch.setattr(quant_proposal, 'QUANT_PROP_SETTING', SimpleNamespace(action_selection='bandit'))

    # Make a trace with a single historical experiment; extract_metrics will return a metric that favors model
    trace = FakeTrace('scenA')
    trace.hist.append((make_exp('factor'), make_feedback(decision=False)))

    # Patch extract_metrics_from_experiment so it returns a metric that leads controller.decide->'model'
    monkeypatch.setattr(quant_proposal, 'extract_metrics_from_experiment', lambda exp: {'favor': 'model'})

    # Instantiate generator and call prepare_context
    gen = quant_proposal.QlibQuantHypothesisGen(None)

    context, ok = gen.prepare_context(trace)

    # Assertions: method returns success flag True, generator targets set to the controller decision, and controller.record called
    assert ok is True
    assert getattr(gen, 'targets') == 'model'
    # Controller should have recorded metric and prev_action
    assert trace.controller.recorded is not None
    recorded_metric, recorded_prev_action = trace.controller.recorded
    assert isinstance(recorded_metric, dict) and recorded_metric.get('favor') == 'model'
    assert recorded_prev_action == 'factor'
    # When action is 'model' the RAG guidance contains mention of GRU/LSTM per implementation
    assert context['RAG'] is not None and 'GRU' in context['RAG']


def test_llm_empty_history_round_011(monkeypatch):
    """
    Exercising the LLM branch when there is no history. Ensures the APIBackend and prompt templates are used
    and that the returned action from the fake APIBackend controls the flow (we return 'factor').
    """
    setup_common_mocks(monkeypatch)

    monkeypatch.setattr(quant_proposal, 'QUANT_PROP_SETTING', SimpleNamespace(action_selection='llm'))

    trace = FakeTrace('scenB')
    # trace.hist remains empty to trigger the 'no previous hypothesis' quick paths

    gen = quant_proposal.QlibQuantHypothesisGen(None)

    context, ok = gen.prepare_context(trace)

    assert ok is True
    # Because our FakeAPIBackend returns action 'factor', the code should set the action to 'factor'
    assert getattr(gen, 'targets') == 'factor'
    # For short history (empty), RAG should be the easy/fast suggestion
    assert isinstance(context['RAG'], str) and 'easiest and fastest' in context['RAG']
    # Hypothesis_and_feedback should be the explicit message for no previous history
    assert context['hypothesis_and_feedback'].startswith("No previous hypothesis and feedback")
    # The output format prompt should reflect our fake T returns
    assert isinstance(context['hypothesis_output_format'], str) and 'hypothesis_output_format' in context['hypothesis_output_format']


def test_random_model_with_sota_round_011(monkeypatch):
    """
    Exercising the random selection branch where random.choice deterministically returns 'model'.
    Also verify SOTA model prompt is returned when applicable.
    """
    setup_common_mocks(monkeypatch)

    monkeypatch.setattr(quant_proposal, 'QUANT_PROP_SETTING', SimpleNamespace(action_selection='random'))

    # Force random.choice used inside module to return 'model'
    monkeypatch.setattr(quant_proposal.random, 'choice', lambda choices: 'model')

    # Build a trace with multiple entries including a model experiment that was accepted (decision True)
    trace = FakeTrace('scenC')
    trace.hist.append((make_exp('factor'), make_feedback(decision=False)))
    trace.hist.append((make_exp('model'), make_feedback(decision=True)))

    gen = quant_proposal.QlibQuantHypothesisGen(None)

    context, ok = gen.prepare_context(trace)

    assert ok is True
    # The action chosen should be 'model' because we forced random.choice
    assert getattr(gen, 'targets') == 'model'
    # Since there is an accepted model in history, SOTA_hypothesis_and_feedback should be produced via T(...).r()
    sota = context['SOTA_hypothesis_and_feedback']
    assert isinstance(sota, str) and 'sota_hypothesis_and_feedback' in sota
