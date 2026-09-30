# Coverage Collection

Collect Augment's `coverage.json` from existing Python or Vitest tests. Supply a prepared checkout and the same [source_files.json](../../resources/inputs/README.md#source_filesjson) used for extraction. Run collection before Augment, writing to a new directory outside the checkout. Commands inherit the current environment and project test configuration; bundled projects already include baseline coverage.

## Python

Run with the project's interpreter, pytest, and coverage.py. Arguments after `--` go to pytest:

```bash
/path/to/checkout/.venv/bin/python src/collect_coverage/python.py \
  --project-root /path/to/checkout \
  --source-files /path/to/inputs/source_files.json \
  --out-dir /path/to/inputs/coverage --timeout 900 -- tests/ -q
```

Use single-process pytest without a competing coverage plugin. For xdist or subprocess measurement, use the project's native coverage collection/combine commands and supply branch-enabled coverage.py JSON instead. Additional import paths can be set through `PYTHONPATH`.

Outputs: `coverage.json`, `run.json` with test status/timing, `test.log`, and `raw/` reports.

## TypeScript

Install Vitest and a matching `v8` or `istanbul` coverage provider in the checkout. Create `collection.json`:

```json
{
  "project": "my-project",
  "project_root": "../checkout",
  "source_files": "source_files.json",
  "command": ["pnpm", "exec", "vitest"],
  "timeout_seconds": 300,
  "denominator_timeout_seconds": 900,
  "packages": [
    {
      "cwd": ".",
      "config": "vitest.config.ts",
      "provider": "v8",
      "include": ["src/**/*.ts"],
      "tests": ["tests/example.test.ts", "tests/other.test.ts"]
    }
  ]
}
```

```bash
node src/collect_coverage/typescript.mjs \
  --config /path/to/inputs/collection.json \
  --out-dir /path/to/inputs/coverage
```

| Setting | Use |
| --- | --- |
| `project` | Registered project ID. |
| `project_root`, `source_files` | Paths relative to `collection.json`, or absolute paths. |
| `command` | Vitest launcher; default `["pnpm", "exec", "vitest"]`. |
| `timeout_seconds` | Per-test-file timeout; default `300`. |
| `denominator_timeout_seconds` | Per-package source-coverage measurement timeout; default `900`. |
| `packages[].cwd` | Package directory relative to the checkout; default `.`. |
| `packages[].config` | Optional Vitest configuration, relative to the package. |
| `packages[].provider` | `v8` or `istanbul`; default `v8`. Use the same provider for Augment. |
| `packages[].include`, `exclude` | Coverage globs, relative to the package. |
| `packages[].tests` | Nonempty list of test files, relative to the package; list each test once. |
| `packages[].args` | Optional additional Vitest arguments. |

Each package suite runs once to establish executable lines and branch arms; listed test files run separately to collect covered counts and per-test attribution. List every test file whose coverage should contribute.

Include unexecuted runtime source files from `source_files.json`. Provide the services and dependencies required by the package suite and listed test files.

Outputs: `coverage.json` with combined coverage from the listed tests and per-test attribution, `runs.json` with execution status/timing, and `raw/` reports and logs.

## Test Failures

Failing tests contribute the coverage they recorded. Inspect `run.json` or `runs.json` for test outcomes. If a required report is missing or invalid, correct the environment or test selection and rerun collection in a new output directory.

Create [base_input.json](../../resources/inputs/README.md#base_inputjson) and set `general_cov.coverage_json` to the collected report.
