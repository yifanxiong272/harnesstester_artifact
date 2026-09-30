# Environment Setup

Run commands from the repository root.

## Ubuntu

Install Git, curl, tar, xz, and CA certificates. Then install Python and uv:

```bash
curl -LsSf https://astral.sh/uv/0.12.3/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.12.13 --default
```

For TypeScript:

```bash
mkdir -p "$HOME/.local/node"
curl -fsSL https://nodejs.org/dist/v24.15.0/node-v24.15.0-linux-x64.tar.xz \
  | tar -xJ -C "$HOME/.local/node" --strip-components=1
export PATH="$HOME/.local/node/bin:$PATH"
npm install --global --prefix "$HOME/.local/node" pnpm@10.32.1
```

Keep the exported paths in each shell used to run the artifact. Project installation requires network access and any native build tools required by its dependencies.

## Paper Projects

```bash
python3 run.py setup --project pr-agent
python3 run.py setup --project openclaw
```

Setup uses Python 3.12.13 for the seven Python projects and the installed Node.js 24.15.0 for the three TypeScript projects. Python environments are stored in `.venvs/<project>`; TypeScript dependencies are installed in the bundled checkout.

Use `PYTHON=/path/to/python python3 run.py setup --project PROJECT` to override the default Python interpreter.

## New Projects

Install the project's dependencies, then add an entry to [projects.json](resources/projects.json). Existing entries can be reused for revisions with the same source and test configuration.

### Python

Extraction needs a Python interpreter that supports the source syntax. Augment needs pytest, coverage.py, and the subject dependencies; Probe needs pytest and the subject dependencies.

```json
{
  "my-project": {
    "language": "python",
    "source_roots": ["package"]
  }
}
```

Set `source_roots` to the product's source directories. For Augment, select the interpreter and import paths in [base_input.json](resources/inputs/README.md#base_inputjson). For Probe, use `--python-bin` and, if needed, `--fixed-python-bin`.

Python Augment accepts optional `augment.constraints` for project-specific requirements such as a test subdirectory: `"augment": {"constraints": ["Place generated pytest files under tests/unittest/."]}`. Omit it or use `[]` for no additional constraints. Generated test files must be under `tests/`.

### TypeScript

Install TypeScript, Vitest, and the subject dependencies in the checkout. Augment and coverage collection also need a coverage provider matching the installed Vitest version. Install the Augment client once:

```bash
npm ci --prefix src/augment/typescript
```

```json
{
  "my-project": {
    "language": "typescript",
    "source_roots": ["src"],
    "augment": {
      "test_packages": [
        {"name": "root", "cwd": ".", "config": "vitest.config.ts", "coverageProvider": "v8"}
      ]
    },
    "probe": {
      "test_command": ["pnpm", "exec", "vitest", "run", "--config", "vitest.config.ts", "<generated-test-file>"]
    }
  }
}
```

Use the project's Vitest configuration and the same coverage provider for collection and Augment (`v8` by default, or `istanbul`). Package directories are checkout-relative; configuration paths are package-relative. Keep `<generated-test-file>` as the Probe command placeholder.

## Model Access

For Augment and Probe, set `OPENAI_API_KEY` in the environment or in a private file passed through `--env-file`; [.env.example](.env.example) shows the format. Select the model with `--model`, for example `--model gpt-5-mini`. Use `OPENAI_BASE_URL` for an OpenAI-compatible endpoint.

## Probe Checkout Setup

Bundled historical cases install their dependencies automatically, using revision-specific Python setup profiles and Node.js pins when present; these runtimes can differ from the bundled-checkout versions above. For automatic checkout of latest revisions and external cases, provide `--python-bin` for Python or `--setup-script` for either language; see [Probe checkout options](src/probe/README.md#checkout-options).
