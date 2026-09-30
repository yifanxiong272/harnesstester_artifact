"""One shared wall-clock deadline for a case's model and validation work."""

from __future__ import annotations

import time
from contextvars import ContextVar, Token
from pathlib import Path

from common.utils.python.json_io import write_json

DEFAULT_CASE_TIME_BUDGET_SECONDS = 1800


class CaseBudgetExceeded(RuntimeError):
    """Stop the case without treating the budget gate as a failed test."""


class CaseTimeBudgetExceeded(CaseBudgetExceeded, TimeoutError):
    """The case budget expired, not a test or provider failure."""


_deadline: ContextVar[float | None] = ContextVar("case_deadline", default=None)


def start_case_budget(run_dir: Path, seconds: float) -> Token:
    deadline = None
    if seconds > 0:
        record_path = run_dir / "time-budget.json"
        started_at = time.time()
        record = {"started_at": started_at, "deadline_at": started_at + seconds}
        write_json(record_path, record)
        # Record wall-clock timestamps; enforce the shared deadline monotonically.
        deadline = time.monotonic() + (record["deadline_at"] - time.time())
    return _deadline.set(deadline)


def end_case_budget(token: Token) -> None:
    _deadline.reset(token)


def limit_timeout(seconds: float = float("inf")) -> float:
    deadline = _deadline.get()
    if deadline is None:
        return seconds
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise CaseTimeBudgetExceeded("case time budget exhausted")
    return min(seconds, remaining)
