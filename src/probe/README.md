# Probe

Generate tests for a historical buggy/fixed case or selected source files at a latest revision. Run commands from the repository root.

## Requirements

Provide model credentials and [register new projects](../../SETUP.md#new-projects). Bundled cases use [automatic environment setup](../../resources/benchmark/README.md). Other inputs require pytest and subject dependencies for Python, or project-local TypeScript, Vitest, and subject dependencies for TypeScript.

## Historical Case

Use `--case-id ID` for `resources/benchmark/cases/<project>/<case-id>.json`, `--cases-root PATH` for a custom or extended benchmark following the same case schema, and `--case-json PATH` for one specific case. With `--cases-root`, place cases at `PATH/cases/<project>/<case-id>.json` or `PATH/<case-id>/case.json`. Historical case fields are `project`, `case_id`, `revisions.buggy`, `revisions.fixed`, and `patch_targets.target_units` ([benchmark case schema](../../resources/benchmark/README.md)); automatic checkout also needs `repository` or `--repository`.

For existing prepared checkouts:

```bash
python3 run.py probe --project pr-agent \
  --case-json /path/to/case.json \
  --buggy-root /path/to/buggy --fixed-root /path/to/fixed \
  --python-bin /path/to/prepared/bin/python --model gpt-5-mini
```

For TypeScript, omit `--python-bin`. Use prepared checkouts at the revisions recorded in the case.

## Latest Revision

Use `--repository URL --revision FULL_COMMIT_SHA --target FILE` for automatic download and complete-file selection; repeat `--target` for more files. For an existing checkout, supply a target-selection file:

```bash
python3 run.py probe --project my-project \
  --case-json /path/to/targets.json --latest-root /path/to/checkout \
  --model gpt-5-mini
```

Python uses the checkout's `.venv/bin/python` unless `--python-bin` is supplied.

## Target Selection

For latest-revision selection, create `targets.json` with source coordinates from that revision:

```json
{
  "project": "my-project",
  "case_id": "selected_target",
  "repository": "https://github.com/OWNER/REPO",
  "revisions": {"latest": "FULL_COMMIT_SHA"},
  "target_units": [
    {
      "unit_id": "u1",
      "filepath": "package/module.py",
      "qualname": "Agent.run",
      "kind": "method",
      "start_line": 20,
      "end_line": 45
    }
  ],
  "validation": {"generated_test_roots": ["tests/generated/probe"]}
}
```

Paths are checkout-relative; line bounds are one-based and inclusive. TypeScript uses the same fields with its source coordinates. Choose a generated-test directory discovered by the project's test configuration. Historical cases use the same target-unit fields under `patch_targets.target_units`, with coordinates from the buggy revision. TypeScript can specify `validation.test_command` to override the registered Vitest command.

## Checkout Options

Automatic download requires Git and full commit hashes; remote repositories also require network access. Bundled cases install their recorded dependencies with revision-specific runtimes. Latest revisions and external cases require `--python-bin PATH` for a prepared Python environment or `--setup-script PATH` for installation. These options also override bundled installation; `--python-bin` applies to both historical revisions unless `--fixed-python-bin PATH` selects a separate fixed-side Python environment. Setup scripts cannot be combined with prepared checkout roots.

The script runs inside each downloaded checkout with `PROBE_PROJECT`, `PROBE_REVISION_KIND` (`buggy`, `fixed`, or `latest`), and `PROBE_REVISION` set. Use `set -euo pipefail` and that revision's installation commands. Python scripts can create `.venv/bin/python`; TypeScript scripts must install or link the required package dependencies. Preserve tracked source/configuration files during setup.

Download and setup precede the Probe time budget. Temporary downloaded checkouts are removed on exit; generated tests and run records are retained.

## Run Options

The default strategy is `target_probe_ldh`: LLM-dependent harness (LDH).

| Option | Use |
| --- | --- |
| `--model NAME` | Select the generation model. |
| `--env-file PATH` | Read model credentials and endpoint settings from a file. |
| `--case-time-budget-seconds N` | Case time budget; default `1800`. |
| `--direct-samples N` | Direct-generation sample limit; default `10`. |
| `--samples N` | Planned-generation sample limit; default `10`. |
| `--soft-samples N` | Conditional whole-target sample limit; default `2`. |
| `--out-root PATH` | Choose the output parent directory. |
| `--run-id NAME` | Name this run. |

Runs can finish before the time limit when sample limits are reached, candidates are found, or workflow errors repeat.

For one sample:

```bash
python3 run.py probe --case-id pr-agent-946c3e22 \
  --direct-samples 1 --samples 0 --soft-samples 0 --model gpt-5-mini
```

## Contract-Agnostic

Add `--strategy target_probe_contract_agnostic` to a historical-case or latest-revision command.

## Outputs

Runs are saved under `<out-root>/<run-id>/`; the default parent is `outputs/<project>/probe/`.

Automatic checkout also saves `prepare.log` and `checkouts.json` under `<out-root>/preparation/<run-id>/`.

| Path | Contents |
| --- | --- |
| `manifest.json` | Selected revisions and run configuration. |
| `progress.json` | Index of completed samples and any case-budget error. |
| Sample `result.json` files | Candidate outcomes and paths to execution evidence. |
| Proposal and variant records | Generated test paths/source and subsequent variants. |

Keep outputs outside checkouts. Review historical candidates for a valid oracle and the selected defect; review latest-revision failures for a product defect.
