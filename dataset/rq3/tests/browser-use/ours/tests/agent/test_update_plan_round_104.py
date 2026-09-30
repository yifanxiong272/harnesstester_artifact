import types
from types import SimpleNamespace

import pytest

from browser_use.agent.service import Agent
from browser_use.agent.views import PlanItem

# We call the unbound method with a lightweight fake `self` object.
# This avoids initializing the full Agent and any external dependencies.

def test_no_planning_round_104():
    """If planning is disabled, the method should return without mutating state or calling logger.info."""
    called = {"info": False}

    fake_self = SimpleNamespace()
    fake_self.settings = SimpleNamespace(enable_planning=False)
    # state.plan should remain unchanged
    fake_self.state = SimpleNamespace(plan=["unchanged"], current_plan_item_index=0, plan_generation_step=None, n_steps=0)

    def info_should_not_be_called(*args, **kwargs):
        called["info"] = True

    fake_self.logger = SimpleNamespace(info=info_should_not_be_called)

    # model_output with no fields set
    model_output = SimpleNamespace(plan_update=None, current_plan_item=None)

    # Call the method
    Agent._update_plan_from_model_output(fake_self, model_output)

    # Assertions
    assert fake_self.state.plan == ["unchanged"]
    assert called["info"] is False


def test_plan_update_created_round_104():
    """When plan_update is provided and n_steps == 0 the plan should be created and logger should mention 'created'."""
    messages = []

    fake_self = SimpleNamespace()
    fake_self.settings = SimpleNamespace(enable_planning=True)
    fake_self.state = SimpleNamespace(plan=None, current_plan_item_index=None, plan_generation_step=None, n_steps=0)
    fake_self.logger = SimpleNamespace(info=lambda msg: messages.append(msg))

    model_output = SimpleNamespace(plan_update=["step one", "step two"], current_plan_item=None)

    Agent._update_plan_from_model_output(fake_self, model_output)

    # The state.plan should be a list of PlanItem instances with the correct text
    assert isinstance(fake_self.state.plan, list)
    assert [p.text for p in fake_self.state.plan] == ["step one", "step two"]

    # When n_steps == 0, the message should say 'created'
    assert any("created" in m for m in messages), f"expected 'created' in logger messages, got: {messages}"

    # The first PlanItem should be marked as 'current'
    assert fake_self.state.plan[0].status == "current"
    assert fake_self.state.current_plan_item_index == 0
    assert fake_self.state.plan_generation_step == fake_self.state.n_steps


def test_plan_update_updated_round_104():
    """When plan_update is provided and n_steps > 0 the log should say 'updated'."""
    messages = []

    fake_self = SimpleNamespace()
    fake_self.settings = SimpleNamespace(enable_planning=True)
    fake_self.state = SimpleNamespace(plan=None, current_plan_item_index=None, plan_generation_step=None, n_steps=5)
    fake_self.logger = SimpleNamespace(info=lambda msg: messages.append(msg))

    model_output = SimpleNamespace(plan_update=["only step"], current_plan_item=None)

    Agent._update_plan_from_model_output(fake_self, model_output)

    # One PlanItem created
    assert len(fake_self.state.plan) == 1
    assert fake_self.state.plan[0].text == "only step"

    # When n_steps > 0, the message should say 'updated'
    assert any("updated" in m for m in messages), f"expected 'updated' in logger messages, got: {messages}"

    # The first PlanItem should be marked current
    assert fake_self.state.plan[0].status == "current"
    assert fake_self.state.current_plan_item_index == 0


def test_current_plan_item_advance_and_clamp_round_104():
    """Advance the current plan index (clamped to last index) and mark intermediate steps as done; final step becomes 'current'."""
    fake_self = SimpleNamespace()
    fake_self.settings = SimpleNamespace(enable_planning=True)

    # Create a plan with three PlanItem instances; set initial statuses
    p0 = PlanItem(text="a")
    p1 = PlanItem(text="b")
    p2 = PlanItem(text="c")
    # Initialize statuses in a way the code will update
    p0.status = "current"
    p1.status = "pending"
    p2.status = None

    fake_self.state = SimpleNamespace(plan=[p0, p1, p2], current_plan_item_index=0, plan_generation_step=None, n_steps=1)
    fake_self.logger = SimpleNamespace(info=lambda msg: None)

    # Provide a too-large index; it should clamp to len(plan)-1 == 2
    model_output = SimpleNamespace(plan_update=None, current_plan_item=10)

    Agent._update_plan_from_model_output(fake_self, model_output)

    # Indices 0 and 1 (range(0,2)) should be marked 'done'
    assert fake_self.state.plan[0].status == "done"
    assert fake_self.state.plan[1].status == "done"

    # The clamped last index should be marked 'current'
    assert fake_self.state.plan[2].status == "current"
    assert fake_self.state.current_plan_item_index == 2


def test_current_plan_item_negative_clamp_round_104():
    """Negative current_plan_item should clamp to 0. Backward moves do not mark previously-current steps as done (loop empty)."""
    fake_self = SimpleNamespace()
    fake_self.settings = SimpleNamespace(enable_planning=True)

    p0 = PlanItem(text="first")
    p1 = PlanItem(text="second")
    p0.status = "pending"
    p1.status = "current"

    fake_self.state = SimpleNamespace(plan=[p0, p1], current_plan_item_index=1, plan_generation_step=None, n_steps=2)
    fake_self.logger = SimpleNamespace(info=lambda msg: None)

    model_output = SimpleNamespace(plan_update=None, current_plan_item=-5)

    Agent._update_plan_from_model_output(fake_self, model_output)

    # Negative clamps to 0 and sets plan[0].status to 'current'
    assert fake_self.state.plan[0].status == "current"
    # Since the code doesn't mark backward steps as done, plan[1] remains 'current'
    assert fake_self.state.plan[1].status == "current"
    assert fake_self.state.current_plan_item_index == 0
