"""Check compact serialization against the formal extractor's output schema."""

import importlib
import os
from pathlib import Path
from random import Random
from types import SimpleNamespace

import pytest

from llm_dependent.python.common import RegionSpan
from llm_dependent.python.flow.models import FlowEdge
from llm_dependent.python.flow.payload import build_payload


@pytest.mark.parametrize("seed", range(12))
@pytest.mark.parametrize("include_control", [False, True])
def test_payload_matches_formal(seed, include_control):
    root = os.environ.get("LDH_FORMAL_ROOT")
    if not root:
        pytest.skip("set LDH_FORMAL_ROOT for reference checks")
    import common

    directory = str(Path(root) / "src/common")
    if directory not in common.__path__:
        common.__path__.append(directory)
    formal = importlib.import_module("common.llm_dependent.python.flow.payload")
    random = Random(seed)
    spans = [
        RegionSpan(f"module_{i % 3}.py", i // 2 + 1, i // 2 + 2, str(i % 2))
        for i in range(18)
    ]
    spans.append(RegionSpan("module_0.py", 1, 2, "other-tag"))
    edges = {
        FlowEdge(
            span=random.choice(spans),
            source_spans=tuple(random.sample(spans, random.randrange(6))),
            dependence_type=random.choice(["assignment", "return", "caller"]),
        )
        for _ in range(seed * 5)
    }
    facts = SimpleNamespace(sources=set(random.sample(spans, seed)), data_edges=edges)
    stats = SimpleNamespace(converged=True, iterations=3, max_iterations=12)
    regions = (
        [
            SimpleNamespace(
                info=SimpleNamespace(file=span.file, qualname=f"method_{i % 2}"),
                control_span=span,
            )
            for i, span in enumerate(reversed(spans))
        ]
        if include_control
        else None
    )
    assert build_payload("fixture", facts, stats, regions) == formal.build_payload(
        "fixture", facts, stats, regions
    )
