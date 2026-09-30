#!/usr/bin/env python3
"""Minimal Python-only helpers for LLM-dependent harness (LDH) extraction."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegionSpan:
    file: str
    start: int
    end: int
    tag: str
    detail: str | None = None
    qualname: str | None = None


def normalize_span(
    file: str,
    start: int,
    end: int,
    tag: str,
    detail: str | None = None,
    qualname: str | None = None,
) -> RegionSpan:
    return RegionSpan(
        file=file,
        start=int(start),
        end=int(end),
        tag=tag,
        detail=detail,
        qualname=qualname,
    )
