#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class CodeExcerpt:
    path: str
    start_line: int
    end_line: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TestProposal:
    test_file: str
    append_code: str
    expected_nodeids: list[str] = field(default_factory=list)
    targeted_objective_ids: list[str] = field(default_factory=list)
    targeted_lines: list[str] = field(default_factory=list)
    mocking_strategy: str = ""
    oracle: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContextRequest:
    kind: str
    filepath: str
    qualname: str = ""
    reason: str = ""
    start_line: int | None = None
    end_line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
