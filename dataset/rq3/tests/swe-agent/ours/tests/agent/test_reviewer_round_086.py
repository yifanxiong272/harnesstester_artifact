import types
from types import SimpleNamespace
import sweagent.agent.reviewer as reviewer_mod


class FakeTrajFormatter:
    def __init__(self, config):
        # record the config passed so test can assert it
        self.init_arg = config


def fake_get_logger(name, emoji=None):
    # return a deterministic structure capturing the inputs
    return {"name": name, "emoji": emoji}


def test_reviewer_init_sets_attrs_round_086(monkeypatch):
    """Ensure Reviewer.__init__ stores config and model, constructs the
    trajectory formatter with config.traj_formatter, and sets the logger.
    """
    # Patch symbols where Reviewer resolves them to avoid running real logic
    monkeypatch.setattr(reviewer_mod, "TrajectoryFormatter", FakeTrajFormatter)
    monkeypatch.setattr(reviewer_mod, "get_logger", fake_get_logger)

    # prepare a minimal config object with the expected attribute
    cfg = SimpleNamespace(traj_formatter="TF-CONFIG")
    fake_model = object()

    # instantiate Reviewer under test
    r = reviewer_mod.Reviewer(config=cfg, model=fake_model)

    # Observable assertions: attributes are stored and the formatter/logger were used
    assert r._config is cfg
    assert r._model is fake_model
    assert isinstance(r._traj_formatter, FakeTrajFormatter)
    assert r._traj_formatter.init_arg == "TF-CONFIG"

    # confirm logger was created with the reviewer name and the emoji contains
    # the expected Unicode codepoints (avoid comparing escaped representations)
    assert r.logger["name"] == "reviewer"
    emoji = r.logger["emoji"]
    assert isinstance(emoji, str)
    # contains person emoji U+1F9D1 and scales U+2696
    assert "\U0001F9D1" in emoji
    assert "\u2696" in emoji
