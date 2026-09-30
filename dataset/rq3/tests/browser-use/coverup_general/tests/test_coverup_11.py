# file: browser_use/browser/watchdogs/local_browser_watchdog.py:219-358
# asked: {"lines": [236, 237, 238, 240, 242, 245, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 301, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 317, 318, 320, 321, 322, 323, 325, 327, 330, 331, 332, 333, 334, 335, 336, 337, 338, 341, 344, 346, 347, 349, 350, 351, 352, 355, 356, 358], "branches": [[249, 250], [249, 261], [250, 251], [250, 252], [261, 262], [261, 280], [262, 263], [262, 264], [280, 281], [280, 301], [281, 282], [281, 283], [317, 318], [317, 320], [325, 327], [325, 358], [330, 331], [330, 341], [332, 333], [332, 338], [333, 332], [333, 334], [336, 332], [336, 337], [344, 346], [344, 355], [347, 325], [347, 349], [351, 325], [351, 352], [355, 325], [355, 356]]}
# gained: {"lines": [236, 237, 238, 240, 242, 245, 249, 261, 262, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 301, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 317, 318, 320, 321, 322, 323, 325, 327, 330, 331, 332, 333, 334, 335, 336, 337, 338, 341, 344, 346, 347, 349, 350, 351, 352, 355, 356, 358], "branches": [[249, 261], [261, 262], [261, 280], [262, 264], [280, 281], [280, 301], [281, 282], [317, 318], [317, 320], [325, 327], [325, 358], [330, 331], [330, 341], [332, 333], [332, 338], [333, 332], [333, 334], [336, 337], [344, 346], [344, 355], [347, 349], [351, 352], [355, 325], [355, 356]]}

import os
from pathlib import Path
import platform
import pytest

from browser_use.browser.watchdogs.local_browser_watchdog import LocalBrowserWatchdog
from browser_use.browser.profile import BrowserChannel


def _monkeypatch_platform(monkeypatch, system_name: str):
    monkeypatch.setattr(platform, "system", lambda: system_name)


def _make_file(p: Path, mode=0o644):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("stub")
    p.chmod(mode)


def test_find_installed_browser_path_linux_wildcard(monkeypatch, tmp_path):
    _monkeypatch_platform(monkeypatch, "Linux")
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))

    d1 = tmp_path / "chromium-1" / "chrome-linux-abc"
    f1 = d1 / "chrome"
    _make_file(f1)

    d2 = tmp_path / "chromium-2" / "chrome-linux-zzz"
    f2 = d2 / "chrome"
    _make_file(f2)

    result = LocalBrowserWatchdog._find_installed_browser_path(BrowserChannel.CHROMIUM)
    assert result is not None
    expected = str(f2)
    assert result == expected


def test_find_installed_browser_path_windows_env_substitution_direct(monkeypatch, tmp_path):
    _monkeypatch_platform(monkeypatch, "Windows")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    # Pattern as used in the watchdog code
    pattern = r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'

    # Replicate the function's expansion and env var substitution so we can create
    # the file at the exact path the function will check (including backslashes).
    expanded_pattern = Path(pattern).expanduser()
    pattern_str = str(expanded_pattern)
    for env_var in ['%LOCALAPPDATA%', '%PROGRAMFILES%', '%PROGRAMFILES(X86)%']:
        if env_var in pattern_str:
            env_key = env_var.strip('%').replace('(X86)', ' (x86)')
            env_value = os.environ.get(env_key, '')
            if env_value:
                pattern_str = pattern_str.replace(env_var, env_value)
    final_path = Path(pattern_str)

    # Create the file at that exact path (on POSIX this will create names containing backslashes,
    # which matches what the function will check).
    _make_file(final_path)

    result = LocalBrowserWatchdog._find_installed_browser_path(BrowserChannel.CHROME)
    assert result is not None
    assert result == str(final_path)


def test_find_installed_browser_path_unknown_os_returns_none(monkeypatch):
    _monkeypatch_platform(monkeypatch, "ZyOS")
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)

    result = LocalBrowserWatchdog._find_installed_browser_path(None)
    assert result is None
