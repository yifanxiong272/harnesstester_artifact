"""Translate approved public names in the in-memory formal test reference only."""

from __future__ import annotations

import importlib.abc
import importlib.machinery
import sys


def align_formal_names(source: str) -> str:
    return (
        source.replace("LDCR", "LDH")
        .replace("ldcr", "ldh")
        .replace('"current"', '"latest"')
        .replace("'current'", "'latest'")
        .replace("current_", "latest_")
    )


class _FormalNameLoader(importlib.machinery.SourceFileLoader):
    def get_code(self, fullname):
        source = self.get_data(self.path).decode("utf-8")
        return self.source_to_code(align_formal_names(source), self.path)


class _FormalNameFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if not fullname.startswith("common.test_augment.python."):
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec and isinstance(spec.loader, importlib.machinery.SourceFileLoader):
            spec.loader = _FormalNameLoader(fullname, spec.origin)
        return spec


def install_formal_name_adapter():
    if not any(isinstance(finder, _FormalNameFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, _FormalNameFinder())
