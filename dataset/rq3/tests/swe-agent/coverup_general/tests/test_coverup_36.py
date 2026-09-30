# file: sweagent/run/hooks/swe_bench_evaluate.py:40-55
# asked: {"lines": [40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 53, 54, 55], "branches": [[53, 54], [53, 55]]}
# gained: {"lines": [40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 53, 54, 55], "branches": [[53, 54], [53, 55]]}

import pytest
from pathlib import Path
from sweagent.run.hooks.swe_bench_evaluate import SweBenchEvaluate

def test_get_sb_call_basic(tmp_path):
    output_dir = tmp_path / "outdir"
    preds_path = tmp_path / "preds.json"
    # create the preds file path (no need to write contents)
    preds_path.write_text("{}")

    sbe = SweBenchEvaluate(output_dir=output_dir, subset="lite", split="testsplit")
    # make run_id predictable
    sbe._time_suffix = "TIMESUFFIX"

    args = sbe._get_sb_call(preds_path)

    expected = [
        "sb-cli",
        "submit",
        "swe-bench_lite",
        "testsplit",
        "--predictions_path",
        str(preds_path),
        "--run_id",
        f"{output_dir.name}_TIMESUFFIX",
        "--output_dir",
        str(output_dir / "sb-cli-reports"),
    ]

    assert args == expected
    # also verify the run_id property uses the output_dir name and the patched suffix
    assert sbe.run_id == f"{output_dir.name}_TIMESUFFIX"

def test_get_sb_call_submit_only_extends_flags(tmp_path):
    output_dir = tmp_path / "myout"
    preds_path = tmp_path / "preds2.json"
    preds_path.write_text("{}")

    sbe = SweBenchEvaluate(output_dir=output_dir, subset="verified", split="valid")
    sbe._time_suffix = "ABC123"

    args = sbe._get_sb_call(preds_path, submit_only=True)

    # base portion should be present
    base_expected = [
        "sb-cli",
        "submit",
        "swe-bench_verified",
        "valid",
        "--predictions_path",
        str(preds_path),
        "--run_id",
        f"{output_dir.name}_ABC123",
        "--output_dir",
        str(output_dir / "sb-cli-reports"),
    ]
    assert args[: len(base_expected)] == base_expected

    # the submit_only branch should have appended these exact flags in order
    assert args[len(base_expected):] == ["--wait_for_evaluation", "0", "--gen_report", "0", "--verify_submission", "0"]

    # ensure full length is base + 6 appended tokens
    assert len(args) == len(base_expected) + 6
