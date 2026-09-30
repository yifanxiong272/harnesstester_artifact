#!/usr/bin/env python3
"""Read project configuration and resolve artifact-relative paths."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


ARTIFACT_ROOT = Path(__file__).resolve().parents[2]
PROJECTS_FILE = ARTIFACT_ROOT / "resources" / "projects.json"


def load_projects() -> dict[str, dict[str, Any]]:
    with PROJECTS_FILE.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise SystemExit(f"project registry must be an object: {PROJECTS_FILE}")
    return payload


def project_config(project: str, *, language: str | None = None) -> dict[str, Any]:
    projects = load_projects()
    if project not in projects:
        available = ", ".join(sorted(projects))
        raise SystemExit(f"unknown project {project!r}; choose one of: {available}")
    config = {"project": project, **projects[project]}
    if language and config.get("language") != language:
        raise SystemExit(
            f"{project} is a {config.get('language')} project; use the matching runner"
        )
    return config


def resolve_artifact_path(value: str | os.PathLike[str] | None) -> Path | None:
    if value is None:
        return None
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (ARTIFACT_ROOT / path).resolve()


def env_path(config: dict[str, Any], env_key: str, default_key: str) -> Path:
    override = os.environ.get(str(config.get(env_key, "")))
    if override:
        return Path(override).expanduser().resolve()
    if default_key not in config:
        raise SystemExit(f"missing --project-root or {config.get(env_key, 'PROJECT_ROOT')} environment variable")
    resolved = resolve_artifact_path(str(config[default_key]))
    assert resolved is not None
    return resolved


def project_root(config: dict[str, Any], override: Path | None = None) -> Path:
    if override:
        return override.expanduser().resolve()
    return env_path(config, "project_root_env", "project_root")
