"""Check released annotation joins and result indexes."""

from collections import Counter
import csv
import json
from pathlib import Path
import re


RESULTS = Path(__file__).resolve().parents[1] / "dataset"


def rows(name):
    with (RESULTS / name).open(newline="") as stream:
        return list(csv.DictReader(stream))


def test_study_results_directory_layout():
    assert {path.name for path in RESULTS.iterdir() if path.is_dir()} == {
        "rq1", "rq2", "rq3", "rq4",
    }
    assert {path.name for path in (RESULTS / "rq4").iterdir()} == {"historical"}


def test_original_and_final_labels():
    final = rows("rq2/branches.csv")
    original = rows("rq2/original.csv")
    assert len(final) == len(original) == 700
    assert set(final[0]) == {
        "project", "branch_id", "source_url",
        "component_intention", "judgment_pattern", "llm_value_form",
    }
    assert set(original[0]) == set(final[0]) - {"source_url"}
    by_id = {row["branch_id"]: row for row in final}
    assert len(by_id) == 700
    assert {row["branch_id"] for row in original} == set(by_id)
    assert len({row["project"] for row in final}) == 10
    for row in final:
        assert re.fullmatch(r"https://github\.com/[^/]+/[^/]+/blob/[0-9a-f]{40}/.+#L\d+(?:-L\d+)?", row["source_url"])
        assert all(row[key] for key in ("component_intention", "judgment_pattern", "llm_value_form"))
    for row in original:
        assert row["project"] == by_id[row["branch_id"]]["project"]
        labels = [row[key] for key in ("component_intention", "judgment_pattern", "llm_value_form")]
        assert all(labels) or not any(labels)
    assert sum(not row["component_intention"] for row in original) == 10
    supplement_ids = {
        "aider-ldcr-branch-supplement-a3188c3e48fa",
        "kimi-code-ldcr-branch-supplement-d4aa02cd1b5e",
        "kimi-code-ldcr-branch-supplement-ffe5b3e1721d",
    }
    for row in original:
        if row["branch_id"] in supplement_ids:
            for key in ("component_intention", "judgment_pattern", "llm_value_form"):
                assert row[key] == by_id[row["branch_id"]][key]


def test_coverage_belongs_to_confirmed_branches():
    accepted = {r["branch_id"] for r in rows("rq2/branches.csv")}
    coverage = rows("rq2/coverage.csv")
    assert len(coverage) == len(accepted) == 700
    assert {r["branch_id"] for r in coverage} == accepted
    assert Counter(r["original_coverage"] for r in coverage) == {
        "full_branch_covered": 179, "partial_branch_covered": 172,
        "uncovered_branch": 349,
    }
    assert Counter(r["augmented_coverage"] for r in coverage) == {
        "full_branch_covered": 349, "partial_branch_covered": 192,
        "uncovered_branch": 159,
    }
    by_id = {row["branch_id"]: row for row in coverage}
    for branch_id, expected in {
        "aider-ldcr-branch-supplement-a3188c3e48fa": (
            "partial_branch_covered", "partial_branch_covered",
        ),
        "kimi-code-ldcr-branch-supplement-d4aa02cd1b5e": (
            "partial_branch_covered", "full_branch_covered",
        ),
        "kimi-code-ldcr-branch-supplement-ffe5b3e1721d": (
            "uncovered_branch", "uncovered_branch",
        ),
    }.items():
        row = by_id[branch_id]
        assert (row["original_coverage"], row["augmented_coverage"]) == expected


def test_category_totals_and_transitions():
    branches = {row["branch_id"]: row for row in rows("rq2/branches.csv")}
    coverage = rows("rq2/coverage.csv")
    summaries = rows("rq2/taxonomy_summary.csv")
    assert len(summaries) == 15
    for row in summaries:
        count = sum(branch[row["dimension"]] == row["category"] for branch in branches.values())
        assert count == int(row["count"])
        assert abs(float(row["share"]) - count / len(branches)) < 0.000001
    transitions = Counter((row["original_coverage"], row["augmented_coverage"]) for row in coverage)
    assert transitions == {
        ("full_branch_covered", "full_branch_covered"): 179,
        ("partial_branch_covered", "partial_branch_covered"): 125,
        ("partial_branch_covered", "full_branch_covered"): 47,
        ("uncovered_branch", "uncovered_branch"): 159,
        ("uncovered_branch", "partial_branch_covered"): 67,
        ("uncovered_branch", "full_branch_covered"): 123,
    }


def test_branch_coverage_gains():
    coverage = rows("rq2/coverage.csv")
    before = Counter(r["original_coverage"] for r in coverage)
    after = Counter(r["augmented_coverage"] for r in coverage)
    assert after["full_branch_covered"] - before["full_branch_covered"] == 170
    assert before["uncovered_branch"] - after["uncovered_branch"] == 190


def test_rq2_table_set():
    assert {path.name for path in (RESULTS / "rq2").glob("*.csv")} == {
        "branches.csv", "original.csv", "coverage.csv", "taxonomy_summary.csv",
    }


def test_rq1_mutation_outcomes():
    mutation = rows("rq1/mutation.csv")
    assert len(mutation) == len({row["project"] for row in mutation}) == 10
    assert set(mutation[0]) == {
        "project", "denominator", "killed", "survived", "no_coverage", "timeout_crash",
    }
    expected = {
        "openhands": 59, "aider": 19, "swe-agent": 255, "pr-agent": 3,
        "gpt-researcher": 4, "browser-use": 5, "rd-agent": 2,
        "openclaw": 1781, "roo-code": 18, "kimi-code": 79,
    }
    for row in mutation:
        assert int(row["timeout_crash"]) == expected[row["project"]]
        assert sum(int(row[field]) for field in (
            "killed", "survived", "no_coverage", "timeout_crash",
        )) == int(row["denominator"])


def test_augment_figure_set_and_test_metadata():
    figures = {path.name for path in (RESULTS / "rq3/figures").iterdir() if path.is_file()}
    assert figures == {
        f"{stem}.{suffix}"
        for stem in (
            "ldh_coverage_gain", "project_coverage_gain", "mutation_score_gain",
            "semantic_coverage_gain", "fine_grained_ablation",
        )
        for suffix in ("pdf", "png")
    }
    for suffix in ("pdf", "png"):
        semantic = RESULTS / f"rq3/figures/semantic_coverage_gain.{suffix}"
        reference = RESULTS / f"rq2/figures/branch_coverage_gain_by_taxonomy.{suffix}"
        assert semantic.read_bytes() == reference.read_bytes()
    tests = rows("rq3/tests.csv")
    assert "mutation_path" not in tests[0]
    assert Counter(row["coverage_replay"] for row in tests) == {"passed": 3560, "failed": 7, "unrecorded": 3022}
    assert sum(bool(row["mutation_limitation"]) for row in tests) == 4
    nodeids = [nodeid for row in tests for nodeid in json.loads(row["mutation_nodeids"])]
    assert len(nodeids) == 3049
    assert all("::" in nodeid for nodeid in nodeids)


def test_retained_tests_exist():
    for directory, index, expected in (
        ("rq3", "tests.csv", 6589),
        ("rq4/historical", "records.csv", 101),
    ):
        entries = rows(f"{directory}/{index}")
        assert len(entries) == expected
        for row in entries:
            path = Path(row["test"])
            assert not path.is_absolute() and ".." not in path.parts
            assert (RESULTS / directory / path).is_file(), path


def test_testpilot_facades_cover_archived_imports():
    count = 0
    for project in ("openclaw", "roo-code", "kimi-code"):
        subject = RESULTS.parent / "resources/subjects" / project
        for mode in ("general", "scoped"):
            facade = RESULTS / "rq3/tests" / project / f"testpilot2_{mode}/facade"
            package = json.loads((facade / "package.json").read_text())
            loader = (facade / package["main"]).read_text()
            assert (facade / f"../../../../../../resources/subjects/{project}").resolve() == subject.resolve()
            assert "TESTPILOT_SUBJECT_ROOT" in loader
            assert "tsx/cjs" in loader
            assert "/Users/" not in loader
            mapping = json.loads((facade / "target-map.json").read_text())
            keys = {entry["key"] for entry in mapping}
            assert len(keys) == len(mapping)
            count += len(mapping)
            for entry in mapping:
                path = Path(entry["filepath"])
                assert not path.is_absolute() and ".." not in path.parts
                assert (subject / path).is_file(), (project, path)
            for test in (facade / "tests").glob("*.js"):
                assert set(re.findall(r"\bfile_\d+\b", test.read_text())) <= keys, test
    assert count == 2992


def test_historical_records_match_bundled_cases_and_tests():
    directory = RESULTS / "rq4/historical"
    records = rows("rq4/historical/records.csv")
    assert set(records[0]) == {
        "project", "case_id", "method", "result", "test", "test_file", "failed_nodeids",
    }
    indexed = {Path(row["test"]) for row in records}
    assert len(indexed) == len(records)
    files = {
        path.relative_to(directory) for path in directory.rglob("*")
        if path.is_file() and path.relative_to(directory).parts[0] != "FN"
    }
    assert files == indexed | {Path("records.csv")}
    for row in records:
        assert row["method"] in {"ours", "contract_agnostic", "qodo_cover"}
        assert row["result"] in {"AC", "FP"}
        assert Path(row["test"]).parts[:3] == (row["project"], row["method"], row["case_id"])
        case_path = RESULTS.parent / "resources/benchmark/cases" / row["project"] / f"{row['case_id']}.json"
        case = json.loads(case_path.read_text())
        assert (case["project"], case["case_id"]) == (row["project"], row["case_id"])
        assert case["repository"].startswith("https://github.com/")
        for revision in ("buggy", "fixed"):
            assert re.fullmatch(r"[0-9a-f]{40}", case["revisions"][revision])
        if row["test_file"]:
            path = Path(row["test_file"])
            assert not path.is_absolute() and ".." not in path.parts
            assert all(
                nodeid == row["test_file"] or nodeid.startswith((f"{row['test_file']}::", f"{row['test_file']} > "))
                for nodeid in json.loads(row["failed_nodeids"])
            )


def test_historical_case_outcomes_are_mutually_exclusive():
    records = rows("rq4/historical/records.csv")
    outcomes = {}
    for row in records:
        key = (row["project"], row["method"], row["case_id"])
        outcomes.setdefault(key, set()).add(row["result"])
    counts = Counter(
        (method, "AC" if "AC" in labels else "FP")
        for (_, method, _), labels in outcomes.items()
    )
    assert counts == {
        ("ours", "AC"): 43, ("ours", "FP"): 7,
        ("contract_agnostic", "AC"): 15, ("contract_agnostic", "FP"): 5,
        ("qodo_cover", "AC"): 2,
    }
    assert sum(counts.values()) == len(outcomes)
    assert Counter(row["result"] for row in records) == {"AC": 81, "FP": 20}
    assert outcomes[("browser-use", "ours", "browser-use-6bc1f798")] == {"AC", "FP"}


def test_dataset_excludes_generation_logs():
    log_patterns = ("*.log", "*.jsonl", "*.raw.json", "*.prompt.md")
    for pattern in log_patterns:
        assert not list(RESULTS.rglob(pattern))
    runtime_fields = {
        "cost_usd", "prompt_tokens", "completion_tokens", "input_tokens",
        "output_tokens", "total_tokens", "prompt", "conversation", "llm_usage",
    }
    for path in RESULTS.rglob("*.csv"):
        with path.open(newline="") as stream:
            assert not runtime_fields.intersection(next(csv.reader(stream))), path
