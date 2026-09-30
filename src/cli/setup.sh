#!/usr/bin/env bash
# Install one bundled subject's dependencies in its local environment.
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
project=${1:?Usage: python3 run.py setup --project PROJECT}
subject="$root/resources/subjects/$project"
python=${PYTHON:-3.12.13}
version=
case "$project" in
  openhands) version=1.6.0 ;;
  rd-agent) version=0.8.0 ;;
  aider) version=0.86.2 ;;
  browser-use|gpt-researcher|pr-agent|swe-agent) ;;
  openclaw|roo-code|kimi-code) python= ;;
  *) printf 'Unknown project: %s\n' "$project" >&2; exit 2 ;;
esac
if [[ ! -d "$subject" ]]; then
  printf 'Bundled subject not found: %s\n' "$subject" >&2
  exit 2
fi

if [[ -n "$python" ]]; then
  venv="$root/.venvs/$project"
  uv venv --no-project --seed --allow-existing --python "$python" "$venv"
  "$venv/bin/python" -m pip install --disable-pip-version-check --no-deps \
    -r "$root/resources/inputs/$project/requirements.txt"
  # Source archives carry the release version independently of Git history.
  if [[ -n "$version" ]]; then
    export SETUPTOOLS_SCM_PRETEND_VERSION="$version"
  fi
  "$venv/bin/python" -m pip install --disable-pip-version-check --no-deps -e "$subject"
  "$venv/bin/python" -c 'import pytest, coverage; print("Test environment ready")'
else
  # Keep package-install hooks inside the subject, even in a parent Git checkout.
  export GIT_CEILING_DIRECTORIES="$subject"
  export HUSKY=0
  export SKIP_INSTALL_SIMPLE_GIT_HOOKS=1
  (
    cd "$subject"
    pnpm install --frozen-lockfile
  )
  if [[ "$project" == roo-code ]]; then
    # Roo's test packages need matching Istanbul providers beyond the upstream lockfile.
    packages=$(node - "$root" "$subject" <<'JS'
const fs = require("node:fs");
const path = require("node:path");
const { createRequire } = require("node:module");
const [root, subject] = process.argv.slice(2);
const config = JSON.parse(fs.readFileSync(path.join(root, "resources/projects.json")));
for (const { cwd } of config["roo-code"].augment.test_packages) {
  const load = createRequire(path.join(subject, cwd, "package.json"));
  console.log(cwd, load("vitest/package.json").version);
}
JS
    )
    while read -r package version; do
      tools="$root/.venvs/roo-code-coverage-$version"
      if [[ ! -f "$tools/node_modules/@vitest/coverage-istanbul/package.json" ]]; then
        npm install --prefix "$tools" --no-save --package-lock=false \
          "vitest@$version" "@vitest/coverage-istanbul@$version"
      fi
      mkdir -p "$subject/$package/node_modules/@vitest"
      ln -sfn "$tools/node_modules/@vitest/coverage-istanbul" \
        "$subject/$package/node_modules/@vitest/coverage-istanbul"
    done <<< "$packages"
  fi
  npm ci --prefix "$root/src/augment/typescript"
fi
