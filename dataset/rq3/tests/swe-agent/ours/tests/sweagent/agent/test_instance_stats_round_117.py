import pytest

from sweagent.agent.models import InstanceStats


def test_instance_stats_add_round_117():
    # create two instances with distinct values (float + ints)
    a = InstanceStats(instance_cost=1.5, tokens_sent=10, tokens_received=5, api_calls=2)
    b = InstanceStats(instance_cost=2.25, tokens_sent=3, tokens_received=7, api_calls=1)

    # exercise __add__ which should sum all model fields
    c = a + b

    # returned object must be a fresh InstanceStats with summed values
    assert isinstance(c, InstanceStats)
    assert c.instance_cost == pytest.approx(3.75)
    assert c.tokens_sent == 13
    assert c.tokens_received == 12
    assert c.api_calls == 3

    # originals must remain unchanged
    assert a.instance_cost == pytest.approx(1.5)
    assert b.tokens_sent == 3


def test_instance_stats_sub_round_117():
    # create instances where some resulting fields will be negative
    a = InstanceStats(instance_cost=5.0, tokens_sent=20, tokens_received=15, api_calls=4)
    b = InstanceStats(instance_cost=1.0, tokens_sent=5, tokens_received=20, api_calls=1)

    # exercise __sub__ which should subtract all model fields
    d = a - b

    assert isinstance(d, InstanceStats)
    assert d.instance_cost == pytest.approx(4.0)
    assert d.tokens_sent == 15
    # tokens_received goes negative (15 - 20)
    assert d.tokens_received == -5
    assert d.api_calls == 3

    # ensure originals unchanged
    assert a.tokens_received == 15
    assert b.instance_cost == pytest.approx(1.0)
