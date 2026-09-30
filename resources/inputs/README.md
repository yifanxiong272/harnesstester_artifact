# Input Files

This directory holds prepared extraction/Augment inputs for the ten bundled checkouts. For a new checkout, create the files below; regions and coverage must describe the same revision.

| File | Used by | How to obtain it |
| --- | --- | --- |
| `source_files.json` | Extraction and coverage collection | List the product source files. |
| `regions.json` | Augment | Use the [extractor's main output](../../src/llm_dependent/README.md). |
| `coverage.json` | Augment | Use the [coverage collector's output](../../src/collect_coverage/README.md). |
| `base_input.json` | Augment | Reference the checkout and the two outputs above. |

Probe uses a [case or target-selection input](../../src/probe/README.md#target-selection). Python project directories also contain `requirements.txt` for dependency installation.

## source_files.json

```json
{"files": ["package/__init__.py", "package/agent.py"]}
```

`files` is a nonempty array of unique, existing checkout-relative source paths defining the analysis scope. Use `/` separators and include unexecuted source files within that scope. TypeScript uses the same format with its JavaScript/TypeScript paths. Extraction uses the explicit list. Existing `{"locations": [{"file": "package/agent.py"}]}` inputs are also accepted; `files` takes precedence when both fields are present.

## base_input.json

Python:

```json
{
  "project": "my-project",
  "project_root": "../checkout",
  "ldh": {"regions_json": "regions.json"},
  "general_cov": {"coverage_json": "coverage/coverage.json"},
  "runtime": {
    "python": "../checkout/.venv/bin/python",
    "coverage_source": "package",
    "test_pythonpath": []
  }
}
```

TypeScript uses the same required fields except `runtime`, which is omitted. Its test packages and coverage provider are configured in [projects.json](../../SETUP.md#new-projects).

| Field | Meaning |
| --- | --- |
| `project` | Registered project ID. |
| `project_root` | Prepared checkout path. |
| `ldh.regions_json` | Extractor output path. |
| `general_cov.coverage_json` | Baseline coverage path. |
| `runtime.python` | Python test interpreter. |
| `runtime.coverage_source` | Python coverage source packages/directories, comma-separated if needed. |
| `runtime.test_pythonpath` | Optional additional import paths; default `[]`. |

File paths resolve relative to `base_input.json`; absolute paths also work. `runtime.coverage_source` names importable packages or checkout-relative directories, not paths relative to the input file. `test_pythonpath` entries are relative to the checkout.

## regions.json

Keep the complete extractor output. Its `sources` and `data_dependence` arrays identify regions through `location.filepath`, `location.start_line`, and `location.end_line`. Source paths are checkout-relative; line spans are one-based and inclusive.

## coverage.json

Use the [collectors](../../src/collect_coverage/README.md) to produce the required format, including unexecuted source files.

### Python

A branch-enabled coverage.py JSON report supplies the following fields under each checkout-relative source path:

```json
{
  "files": {
    "package/agent.py": {
      "executed_lines": [1, 2, 3, 4],
      "missing_lines": [5],
      "executed_branches": [[3, 4]],
      "missing_branches": [[3, 5]]
    }
  }
}
```

Keep all four arrays, using `[]` when empty. Branch pairs are source/destination line numbers; preserve negative exit destinations. Other native coverage.py metadata may remain.

### TypeScript

```json
{
  "project": "openclaw",
  "files": {
    "src/example.ts": {
      "lines": {"total": [[1, 8]], "covered": [[1, 4]]},
      "branches": [{"line": 3, "total": 2, "covered": 1}]
    }
  },
  "test_coverage": {
    "src/example.ts": {
      "src/example.test.ts": {
        "lines": [[1, 4]],
        "branch_lines": [[3, 3]]
      }
    }
  }
}
```

| Field | Meaning |
| --- | --- |
| `project` | Same project ID as the base input. |
| `files[path].lines.total` | Executable statement-start lines. |
| `files[path].lines.covered` | Covered statement-start lines. |
| `files[path].branches` | Total and covered branch-arm counts grouped by start line. |
| `test_coverage[source][test].lines` | Source lines covered by that test file. |
| `test_coverage[source][test].branch_lines` | Branch-location attribution for that test file, rather than branch-outcome counts. |

All source/test paths are checkout-relative. Ranges are positive, sorted, disjoint, and inclusive: `[[2, 4], [8, 8]]` represents lines 2, 3, 4, and 8. Each branch record has a unique line, positive `total`, and `0 <= covered <= total`. The collector supplies executable totals from the package suite and covered counts and attribution from the explicitly listed test files. Omit the optional `seed_coverage` cache to use runtime measurement.
