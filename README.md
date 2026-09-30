# LLM-dependent harness (LDH)

## Prerequisites

| Software | Version |
| --- | --- |
| Operating system | Ubuntu 22.04.5 LTS, x86_64 |
| Python | 3.12.13 |
| uv | 0.12.3 |
| Node.js | 24.15.0 |
| pnpm | 10.32.1 |

[Installation commands](SETUP.md#ubuntu). Run all commands below from the repository root.

| Directory | Contents |
| --- | --- |
| `src/` | Extraction, Augment, Probe, and their supporting tools. |
| `resources/` | Project checkouts, workflow inputs, and historical benchmark cases. |
| `dataset/` | Paper results, generated tests, and figures. |
| `outputs/` | Results from your runs. |

## Paper Projects

Source checkouts and inputs are included. Replace `pr-agent` with a project ID:

| Language | Project IDs |
| --- | --- |
| Python | `aider`, `browser-use`, `gpt-researcher`, `openhands`, `pr-agent`, `rd-agent`, `swe-agent` |
| TypeScript | `openclaw`, `roo-code`, `kimi-code` |

Install project dependencies once:

```bash
python3 run.py setup --project pr-agent
```

### Extraction

```bash
python3 run.py llm-dependent --project pr-agent
```

Output: `outputs/pr-agent/extraction/regions.json`.

### Augment Tests

Set credentials and generate tests using the included regions and coverage:

```bash
export OPENAI_API_KEY="YOUR_API_KEY"
python3 run.py augment --project pr-agent \
  --time-budget-seconds 7200 --model gpt-5-mini
```

For one round, replace `--time-budget-seconds 7200` with `--rounds 1`. Generated tests and coverage are saved under `outputs/<project>/augment/runs/`.

### Probe a Historical Case

Choose a case from [benchmark/cases](resources/benchmark/cases). With model credentials set, run:

```bash
python3 run.py probe --case-id pr-agent-946c3e22 \
  --case-time-budget-seconds 1800 --model gpt-5-mini
```

For TypeScript, use a case such as `openclaw-2467a103`. The command downloads both revisions and installs their dependencies according to the case's [environment requirements](resources/benchmark/README.md#dependencies) before starting Probe. Tests and outcomes are saved under `outputs/<project>/probe/`; temporary environments are removed afterward.

## New Projects

Install the project's test dependencies and [register it in projects.json](SETUP.md#new-projects).

### Extraction and Augment

1. List source paths in [source_files.json](resources/inputs/README.md#source_filesjson) and extract regions:

```bash
python3 run.py llm-dependent --project my-project \
  --project-root /path/to/checkout \
  --source-base /path/to/inputs/source_files.json \
  --out /path/to/inputs/regions.json
```

2. Collect baseline coverage. For Python:

```bash
/path/to/checkout/.venv/bin/python src/collect_coverage/python.py \
  --project-root /path/to/checkout \
  --source-files /path/to/inputs/source_files.json \
  --out-dir /path/to/inputs/coverage --timeout 900 -- tests/ -q
```

For TypeScript, specify test files in [collection.json](src/collect_coverage/README.md#typescript), then run:

```bash
node src/collect_coverage/typescript.mjs \
  --config /path/to/inputs/collection.json \
  --out-dir /path/to/inputs/coverage
```

3. Create [base_input.json](resources/inputs/README.md#base_inputjson) pointing to the checkout, regions, and coverage from the same revision, then run:

```bash
python3 run.py augment --project my-project \
  --base-input /path/to/inputs/base_input.json \
  --time-budget-seconds 7200 --model gpt-5-mini
```

### Probe a Latest Revision

Provide a registered project ID, repository, full commit hash, and target file; repeat `--target` for more files. Extraction and coverage inputs are not required.

For Python, use an environment containing the selected revision's dependencies:

```bash
python3 run.py probe --project my-project \
  --repository https://github.com/OWNER/REPO \
  --revision FULL_COMMIT_SHA --target package/module.py \
  --python-bin /path/to/prepared/bin/python --model gpt-5-mini
```

For TypeScript, provide a [dependency installation script](src/probe/README.md#checkout-options):

```bash
python3 run.py probe --project my-project \
  --repository https://github.com/OWNER/REPO \
  --revision FULL_COMMIT_SHA --target src/module.ts \
  --setup-script /path/to/setup_dependencies.sh --model gpt-5-mini
```

## Reference

[Augment options](src/augment/README.md), [Probe options](src/probe/README.md), [Input formats](resources/inputs/README.md), [Study results](dataset/README.md).
