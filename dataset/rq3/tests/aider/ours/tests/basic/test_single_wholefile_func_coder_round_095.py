import collections
import types

import pytest

from aider.coders import single_wholefile_func_coder as swfmod

# We call the unbound method SingleWholeFileFunctionCoder.render_incremental_response
# with a lightweight fake self object so we don't need to construct the full class.
# This lets us deterministically control .partial_response_content and .parse_partial_args.


def _call_render_with(fake_self):
    # unbound function call: pass fake_self as self
    func = swfmod.SingleWholeFileFunctionCoder.render_incremental_response
    return func(fake_self, final=False)


def test_render_incremental_response_empty_args_round_095():
    class Fake:
        pass

    fake = Fake()
    # ensure partial_response_content is falsy -> branch where it's not appended
    fake.partial_response_content = ""  # falsy

    # parse_partial_args returns an empty dict -> triggers `if not args: return ""`
    fake.parse_partial_args = lambda: {}

    out = _call_render_with(fake)
    # When args is empty, function should return empty string regardless of partial content being empty
    assert out == ""


def test_render_incremental_response_with_partial_and_multiple_args_round_095():
    class Fake:
        pass

    fake = Fake()
    # truthy partial content should be prepended
    fake.partial_response_content = "PARTIAL"

    # Use OrderedDict to ensure deterministic iteration order
    fake.parse_partial_args = lambda: collections.OrderedDict([
        ("alpha", "1"),
        ("beta", "2"),
    ])

    out = _call_render_with(fake)

    # Build expected string following the implementation:
    # start with partial, then for each key,value: prepend "\n", then "{k}:\n", then the value
    expected = "PARTIAL"
    expected += "\n" + "alpha:" + "\n" + "1"
    expected += "\n" + "beta:" + "\n" + "2"

    assert out == expected
