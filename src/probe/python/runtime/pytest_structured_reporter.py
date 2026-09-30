#!/usr/bin/env python3
"""Pytest plugin that records structured validation facts for generated tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

REPORT_PATH_ENV = "TEST_AUGMENT_PYTEST_REPORT"
MAX_MESSAGE_CHARS = 4_000
MAX_LONGREPR_CHARS = 12_000
MAX_INTERNAL_ERRORS = 20
MAX_COLLECTION_REPORTS = 100
MAX_COLLECTED_NODEIDS = 500
MAX_TEST_REPORTS = 1_500


def _bounded_text(value: Any, limit: int) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _exception_record(call: pytest.CallInfo[Any]) -> dict[str, Any] | None:
    if call.excinfo is None:
        return None
    exception_type = call.excinfo.type
    try:
        is_assertion = issubclass(exception_type, AssertionError)
    except TypeError:
        is_assertion = False
    return {
        "module": str(getattr(exception_type, "__module__", "")),
        "name": str(
            getattr(
                exception_type, "__qualname__", getattr(exception_type, "__name__", "")
            )
        ),
        "message": _bounded_text(call.excinfo.value, MAX_MESSAGE_CHARS),
        "is_assertion": is_assertion,
    }


class StructuredReportPlugin:
    def __init__(self, report_path: Path) -> None:
        self.report_path = report_path
        self.collected_nodeids: list[str] = []
        self.collected_count = 0
        self.test_reports: list[dict[str, Any]] = []
        self.test_report_count = 0
        self.collection_reports: list[dict[str, Any]] = []
        self.collection_report_count = 0
        self.internal_errors: list[dict[str, str]] = []

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        self.collected_count = len(session.items)
        self.collected_nodeids = [
            item.nodeid for item in session.items[:MAX_COLLECTED_NODEIDS]
        ]

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item: pytest.Item, call: pytest.CallInfo[Any]):
        outcome = yield
        report = outcome.get_result()
        self.test_report_count += 1
        if len(self.test_reports) < MAX_TEST_REPORTS:
            self.test_reports.append(
                {
                    "nodeid": report.nodeid,
                    "phase": report.when,
                    "outcome": report.outcome,
                    "exception": _exception_record(call),
                    "longrepr": ""
                    if report.passed
                    else _bounded_text(report.longrepr, MAX_LONGREPR_CHARS),
                }
            )

    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        self.collection_report_count += 1
        if len(self.collection_reports) < MAX_COLLECTION_REPORTS:
            self.collection_reports.append(
                {
                    "nodeid": report.nodeid,
                    "outcome": report.outcome,
                    "longrepr": ""
                    if report.passed
                    else _bounded_text(report.longrepr, MAX_LONGREPR_CHARS),
                }
            )

    def pytest_internalerror(self, excrepr: Any, excinfo: Any) -> None:
        exception_type = getattr(excinfo, "type", None)
        if len(self.internal_errors) >= MAX_INTERNAL_ERRORS:
            return
        self.internal_errors.append(
            {
                "name": str(
                    getattr(
                        exception_type,
                        "__qualname__",
                        getattr(exception_type, "__name__", ""),
                    )
                ),
                "message": _bounded_text(
                    getattr(excinfo, "value", excrepr), MAX_MESSAGE_CHARS
                ),
                "longrepr": _bounded_text(excrepr, MAX_LONGREPR_CHARS),
            }
        )

    def pytest_sessionfinish(
        self, session: pytest.Session, exitstatus: int | pytest.ExitCode
    ) -> None:
        payload = {
            "schema": "test-augment-pytest-structured-report",
            "exit_status": int(exitstatus),
            "collected_count": self.collected_count,
            "collected_nodeids_truncated": self.collected_count
            > len(self.collected_nodeids),
            "collected_nodeids": self.collected_nodeids,
            "test_report_count": self.test_report_count,
            "test_reports_truncated": self.test_report_count > len(self.test_reports),
            "test_reports": self.test_reports,
            "collection_report_count": self.collection_report_count,
            "collection_reports_truncated": self.collection_report_count
            > len(self.collection_reports),
            "collection_reports": self.collection_reports,
            "internal_errors": self.internal_errors,
        }
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.report_path.with_name(
            f"{self.report_path.name}.tmp-{os.getpid()}"
        )
        temporary_path.write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        temporary_path.replace(self.report_path)


def pytest_configure(config: pytest.Config) -> None:
    raw_path = os.environ.get(REPORT_PATH_ENV)
    if raw_path:
        config.pluginmanager.register(
            StructuredReportPlugin(Path(raw_path)), "test-augment-structured-report"
        )
