# Augment

Generate tests to improve coverage of the LLM-dependent harness (LDH). Run commands from the repository root.

## Inputs

Provide model credentials through the environment or `--env-file`, a prepared test environment, and [base_input.json](../../resources/inputs/README.md#base_inputjson) referencing the checkout, `regions.json`, and `coverage.json` from the same revision. The bundled projects include these files; obtain new inputs through [extraction](../llm_dependent/README.md) and [coverage collection](../collect_coverage/README.md).

To use new regions, update `ldh.regions_json` in the base input.

## Run

For a [registered project](../../SETUP.md#new-projects) with custom inputs:

```bash
python3 run.py augment --project my-project \
  --base-input /path/to/inputs/base_input.json \
  --out-root /path/to/runs/augment \
  --time-budget-seconds 7200 --model gpt-5-mini
```

| Option | Use |
| --- | --- |
| `--rounds N` | Limit generation rounds; default `1` without a time budget. |
| `--time-budget-seconds N` | Limit run time; target exhaustion can end a run earlier. |
| `--project-root PATH` | Override the checkout path; inputs must match that checkout. |
| `--python-bin PATH` | Python only: override the test interpreter. |
| `--repair-context-requests N` | Allow up to N requested context items during repair; default `0`. |
| `--out-root PATH` | Output parent directory. |
| `--run-id NAME` | Name this run. |

Python may finish its active round after the time budget; TypeScript also bounds active calls by the remaining time.

## Contract-Agnostic

Add `--strategy contract_agnostic --acceptance-policy candidate_atomic` to the Augment command.

## Outputs

Each invocation writes `<out-root>/runs/<run-id>/`. The default parent is `outputs/<project>/augment/`.

| Path | Contents |
| --- | --- |
| `accepted/files/` | Retained generated test files. |
| `results.json` | Accepted test paths/selectors, round outcomes, and coverage deltas. |
| `coverage.json` | Accumulated coverage state, not the input-format coverage report. |
| `progress.json` | Checkpoints, elapsed time, configuration, and stopping reason. |

Keep outputs outside the checkout. To replay accepted tests, restore files at their recorded relative paths in a matching checkout. For Python, execute the retained nodeids listed in `results.json`.
