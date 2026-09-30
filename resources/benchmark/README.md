# Historical Benchmark

Choose one of the 250 cases under `cases/<project>/` and run:

```bash
python3 run.py probe --case-id pr-agent-946c3e22 \
  --model gpt-5-mini
```

TypeScript uses the same command with a case such as `openclaw-2467a103`. Run from the repository root.

Follow [Ubuntu environment setup](../../SETUP.md#ubuntu). The command downloads both revisions and installs their dependencies, including pinned Node runtimes. Installation requires network access and any native build tools required by the project.

Preparation precedes the Probe time budget. Temporary checkouts and environments are removed on exit; tests and execution/installation records are retained. Override installation with `--python-bin` or `--setup-script`; see [Probe checkout options](../../src/probe/README.md#checkout-options).

## Cases

| Project | Cases |
| --- | ---: |
| OpenHands | 42 |
| Aider | 19 |
| SWE-agent | 7 |
| PR-Agent | 11 |
| GPT Researcher | 4 |
| Browser Use | 41 |
| RD-Agent | 16 |
| OpenClaw | 88 |
| Roo Code | 16 |
| Kimi Code | 6 |
| Total | 250 |

Files are stored at `cases/<project>/<case-id>.json`.

| Field | Contents |
| --- | --- |
| `case_id`, `project` | Case and project identifiers. |
| `repository`, `revisions` | Repository URL and exact buggy/fixed commits. |
| `patch_targets.target_units` | Target file, qualified name, kind, and inclusive buggy-side line range. |
| `validation` | Test command and generated-test directories where specified. |
| `dependencies.buggy`, `dependencies.fixed` | Paths to the corresponding dependency ZIP files, relative to the case JSON. |

## Dependencies

Each ZIP in `dependencies/<project>/` contains the revision's requirements, manifests, and lockfiles at their repository-relative paths. Supplemental locks are stored under `resolved/` inside the ZIP. Setup verifies the upstream files and uses the installation commands selected in `setup.json`, with `{dependencies}` referring to the temporary directory holding supplemental inputs. Existing locks retain their package-manager-specific installation commands; unlocked requirements are resolved at setup time.

To run a single case from a custom or extended benchmark following the same case schema, use `--cases-root /path/to/benchmark --case-id <case-id>` or `--case-json /path/to/case.json`. For these external cases, provide an existing Python environment with `--python-bin` or a dependency installation script with `--setup-script`.
