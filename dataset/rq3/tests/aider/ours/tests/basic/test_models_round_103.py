import math
import types
import pytest

import aider.models as models

Model = models.Model


def _make_model_with_size(width, height):
    """Create a Model instance without running its __init__ and
    attach a deterministic get_image_size method that records the
    filename argument.
    """
    m = object.__new__(Model)
    called = {}

    def get_image_size(fname):
        called['fname'] = fname
        return (width, height)

    # Patch the instance method used by token_count_for_image
    m.get_image_size = get_image_size
    return m, called


def test_token_count_for_image_small_square_round_103():
    # Case: image smaller than 2048 in both dimensions -> no initial downscale.
    # Start size: 512x512 -> scaled so shortest side is 768 -> 768x768
    # tiles_width = ceil(768/512) = 2, tiles_height = 2 => num_tiles = 4
    # token_cost = 4*170 + 85 = 765
    m, called = _make_model_with_size(512, 512)
    fname = "small.png"
    cost = m.token_count_for_image(fname)

    assert called['fname'] == fname
    assert cost == 765


def test_token_count_for_image_large_downscale_round_103():
    # Case: image larger than 2048 in one dimension -> initial downscale applies.
    # Start size: 4096x2048
    # max_dimension = 4096 -> scale_factor = 2048/4096 = 0.5 -> becomes 2048x1024
    # then shortest side scaled to 768: min_dimension=1024 -> scale_factor=768/1024=0.75
    # width = int(2048*0.75) = 1536, height = int(1024*0.75) = 768
    # tiles_width = ceil(1536/512) = 3, tiles_height = ceil(768/512) = 2 => num_tiles = 6
    # token_cost = 6*170 + 85 = 1105
    m, called = _make_model_with_size(4096, 2048)
    fname = "big.png"
    cost = m.token_count_for_image(fname)

    assert called['fname'] == fname
    assert cost == 1105
