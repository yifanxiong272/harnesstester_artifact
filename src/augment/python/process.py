from __future__ import annotations

import os
import signal
import subprocess
import time
from typing import Any


def start_process(command: list[str], **kwargs: Any) -> subprocess.Popen[str]:
    """Start a text subprocess in its own process group when supported."""

    return subprocess.Popen(
        command,
        start_new_session=os.name == "posix",
        **kwargs,
    )


def signal_process_tree(proc: subprocess.Popen[str], value: signal.Signals) -> None:
    """Signal a subprocess and descendants created in its isolated group."""

    try:
        if os.name == "posix":
            os.killpg(proc.pid, value)
        elif proc.poll() is None:
            proc.send_signal(value)
    except ProcessLookupError:
        pass
    except PermissionError:
        try:
            if proc.poll() is None:
                proc.send_signal(value)
        except (PermissionError, ProcessLookupError):
            pass


def terminate_process_tree(proc: subprocess.Popen[str], *, force: bool = False) -> None:
    """Stop the isolated group and reap its direct child with bounded waits."""

    if os.name != "posix":
        if proc.poll() is None:
            proc.kill()
    else:
        signal_process_tree(proc, signal.SIGKILL if force else signal.SIGTERM)
        if not force:
            deadline = time.monotonic() + 0.2
            try:
                while time.monotonic() < deadline:
                    proc.poll()
                    os.killpg(proc.pid, 0)
                    time.sleep(0.01)
                signal_process_tree(proc, signal.SIGKILL)
            except ProcessLookupError:
                pass
    proc.wait(timeout=1)
