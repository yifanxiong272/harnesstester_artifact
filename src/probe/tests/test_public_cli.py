"""Exercise copied artifact entrypoints with a local fixed-response model."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import ssl
import subprocess
import sys
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ARTIFACT_ROOT = Path(__file__).resolve().parents[3]
PROJECTS = json.loads((ARTIFACT_ROOT / "resources/projects.json").read_text())


@pytest.mark.parametrize("language", ["python", "typescript"])
@pytest.mark.parametrize(
    "option",
    [
        "--case-cost-budget-usd",
        "--input-usd-per-million",
        "--cached-input-usd-per-million",
        "--output-usd-per-million",
        "--project-root",
    ],
)
def test_cli_rejects_removed_options(tmp_path, language, option):
    command = [sys.executable, str(ARTIFACT_ROOT / "run.py")]
    result = subprocess.run(
        [
            *command,
            "probe",
            "--project",
            "pr-agent" if language == "python" else "openclaw",
            "--case-json",
            "case.json",
            "--buggy-root",
            "buggy",
            "--fixed-root",
            "fixed",
            option,
            "1",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert option in result.stderr
    assert (
        "unrecognized arguments" in result.stderr or "Unknown option" in result.stderr
    )
    assert not list(tmp_path.iterdir())


def test_python_entry_rejects_typescript_probe(tmp_path):
    result = subprocess.run(
        [
            sys.executable, str(ARTIFACT_ROOT / "src/cli/runner.py"), "probe",
            "--project", "openclaw", "--language", "typescript",
            "--case-json", "case.json", "--buggy-root", "buggy",
            "--fixed-root", "fixed", "--out-root", "output",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "Use python3 run.py probe" in result.stderr
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("language,project", [("python", "pr-agent"), ("typescript", "openclaw")])
@pytest.mark.parametrize("roots", [[], ["--buggy-root", "old"], ["--latest-root", "latest", "--fixed-root", "fixed"]])
def test_cli_rejects_incomplete_or_mixed_revisions(tmp_path, language, project, roots):
    entry = [sys.executable, str(ARTIFACT_ROOT / "run.py")]
    result = subprocess.run(
        [*entry, "probe", "--project", project, "--case-json", "missing.json", *roots],
        cwd=tmp_path, text=True, capture_output=True, timeout=10,
    )
    assert result.returncode != 0
    expected = ("--latest-root", "--buggy-root", "--fixed-root") if roots else ("missing.json",)
    assert any(flag in result.stderr for flag in expected)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("project", sorted(PROJECTS))
@pytest.mark.parametrize(
    "strategy", ["target_probe_ldh", "target_probe_contract_agnostic"]
)
@pytest.mark.parametrize("discovery", [False, True])
def test_standalone_public_cli(tmp_path, project, strategy, discovery):
    exercise_public_cli(tmp_path, project, strategy, discovery)


@pytest.mark.parametrize("project", ["pr-agent", "openclaw"])
@pytest.mark.parametrize("strategy", ["target_probe_ldh", "target_probe_contract_agnostic"])
@pytest.mark.parametrize("selection", ["paired", "bundled", "bundled_setup", "latest_json", "latest_file"])
def test_automatic_checkout_public_cli(tmp_path, project, strategy, selection):
    exercise_public_cli(tmp_path, project, strategy, selection not in ("paired", "bundled", "bundled_setup"), automatic=selection)


def exercise_public_cli(tmp_path, project, strategy, discovery, automatic=None):
    config = PROJECTS[project]
    language = config["language"]
    if language == "typescript" and not os.environ.get("PROBE_TEST_NODE_MODULES"):
        pytest.skip("provide prepared TypeScript/Vitest node_modules")
    original = ARTIFACT_ROOT
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    for name in ("cli", "common", "probe"):
        shutil.copytree(
            original / "src" / name,
            artifact / "src" / name,
            ignore=shutil.ignore_patterns("__pycache__", "tests"),
        )
    (artifact / "resources").mkdir()
    for name in ("resources/projects.json", "run.py"):
        shutil.copy2(original / name, artifact / name)
    ts = language == "typescript"
    source = f"{config['source_roots'][0]}/arithmetic.{'ts' if ts else 'py'}"
    command = config["probe"]["test_command"] if ts else []
    vitest_root = command[command.index("--root") + 1] if "--root" in command else "."
    generated_root = (
        (Path(vitest_root) / "test/generated/benchmarkbr").as_posix()
        if ts
        else "tests/generated/benchmarkbr"
    )
    test_file = f"{generated_root}/test_advance{'.test.ts' if ts else '.py'}"
    module = Path(source).with_suffix("").as_posix()
    specifier = os.path.relpath(module, Path(test_file).parent).replace(os.sep, "/")
    test_code = (
        'import { expect, it } from "vitest";\n'
        f'import {{ advance }} from "{specifier}";\n'
        'it("advance", () => { expect(advance(0)).toBe(2); });\n'
        if ts
        else f"from {module.replace('/', '.')} import advance\n\n"
        "def test_advance():\n    assert advance(0) == 2\n"
    )
    roots = {}
    revisions = (("latest", 1),) if discovery else (("buggy", 1), ("fixed", 2))
    for kind, value in revisions:
        root = tmp_path / kind
        target = root / source
        target.parent.mkdir(parents=True)
        target.write_text(
            f"export function advance(value: number) {{\n  return value + {value};\n}}\n"
            if ts
            else f"def advance(value):\n    return value + {value}\n"
        )
        if ts:
            # Roo Code's bundled Vitest config uses its CommonJS package scope.
            package_type = "commonjs" if project == "roo-code" else "module"
            (root / "package.json").write_text(json.dumps({"type": package_type}))
            config_path = root / (
                command[command.index("--config") + 1]
                if "--config" in command
                else f"{vitest_root}/vitest.config.ts"
            )
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                'export default { test: { include: ["test/**/*.test.ts"] } };\n'
            )
            (root / "node_modules").symlink_to(
                Path(os.environ["PROBE_TEST_NODE_MODULES"]).resolve(),
                target_is_directory=True,
            )
        else:
            # A regular fixture package must take precedence over installed subjects.
            (target.parent / "__init__.py").write_text("")
            (root / "pytest.ini").write_text("[pytest]\n")
        roots[kind] = root
    case = {
        "case_id": "arithmetic",
        "revisions": {"buggy": "before", "fixed": "after"},
        "validation": {"generated_test_roots": [generated_root]},
        "patch_targets": {
            "target_units": [
                {
                    "unit_id": "u1",
                    "filepath": source,
                    "qualname": "advance",
                    "kind": "function",
                    "start_line": 1,
                    "end_line": 3 if ts else 2,
                }
            ]
        },
    }
    case_path = tmp_path / "case.json"
    if discovery:
        case["target_units"] = case.pop("patch_targets")["target_units"]
        case["revisions"] = {"latest": "frozen-latest"}
    setup_script = tmp_path / "setup_dependencies.sh"
    if automatic:
        repository = tmp_path / "repository"
        repository.mkdir()

        def git(*args):
            return subprocess.check_output(["git", "-C", str(repository), *args], text=True).strip()

        git("init", "-q")
        git("config", "user.name", "Artifact Fixture")
        git("config", "user.email", "fixture@example.test")
        for kind, root in roots.items():
            shutil.copytree(root, repository, dirs_exist_ok=True, ignore=shutil.ignore_patterns("node_modules"))
            git("add", ".")
            # Rehash copied files even when their size and preserved timestamps match.
            git("add", "--renormalize", ".")
            git("-c", "commit.gpgsign=false", "commit", "-qm", kind)
            case["revisions"][kind] = git("rev-parse", "HEAD")
        case["project"] = project
        case["repository"] = str(repository)
        case_path = (
            artifact / "resources/benchmark/cases" / project / "arithmetic.json"
            if automatic in ("bundled", "bundled_setup")
            else tmp_path / "release" / "arithmetic" / "case.json"
        )
        case_path.parent.mkdir(parents=True)
        if automatic in ("bundled", "bundled_setup"):
            case["dependencies"] = {}
            filename = "package.json" if ts else "pytest.ini"
            for kind, root in roots.items():
                archive_path = artifact / "resources/benchmark/dependencies" / project / f"{kind}.zip"
                archive_path.parent.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(archive_path, "w") as archive:
                    archive.writestr(filename, (root / filename).read_bytes())
                case["dependencies"][kind] = Path(os.path.relpath(archive_path, case_path.parent)).as_posix()
            if automatic == "bundled_setup":
                install = (
                    [["ln", "-s", str(Path(os.environ["PROBE_TEST_NODE_MODULES"]).resolve()), "node_modules"]]
                    if ts else [
                        [sys.executable, "-m", "venv", ".venv"],
                        # Copy only pytest's packages into the fixture runtime; sandboxed
                        # validation cannot read a .pth link to the parent test environment.
                        [sys.executable, "-c", "\n".join([
                            "import importlib.metadata as m, shutil, subprocess",
                            "from pathlib import Path",
                            "destination = Path(subprocess.check_output(['.venv/bin/python', '-c', 'import sysconfig; print(sysconfig.get_path(\"purelib\"))'], text=True).strip())",
                            "for name in ('pytest', 'pluggy', 'packaging', 'iniconfig', 'pygments'):",
                            "    distribution = m.distribution(name)",
                            "    for entry in distribution.files:",
                            "        if '..' in entry.parts: continue",
                            "        target = destination / entry",
                            "        target.parent.mkdir(parents=True, exist_ok=True)",
                            "        shutil.copy2(distribution.locate_file(entry), target)",
                        ])],
                    ]
                )
                (artifact / "resources/benchmark/setup.json").write_text(json.dumps({
                    "profiles": {"fixture": install},
                    "snapshots": {f"{project}/{kind}.zip": "fixture" for kind in roots},
                }))
        if ts:
            setup_script.write_text(
                f"ln -s {shlex.quote(str(Path(os.environ['PROBE_TEST_NODE_MODULES']).resolve()))} node_modules\n"
            )
    case_path.write_text(json.dumps(case))
    requests = []

    class ModelHandler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            prompt = body["messages"][-1]["content"]
            requests.append(prompt)
            if len(requests) == 1:
                objects = [
                    json.loads(block)
                    for block in re.findall(r"```json\s*\n(.*?)\n```", prompt, re.S)
                ]
                packet = next(obj for obj in objects if "public_target_routes" in obj)
                entry = packet["public_target_routes"]["targets"][0]["entrypoints"][0][
                    "entrypoint_id"
                ]
                response = {
                    "boundary_plan": [
                        {
                            "boundary_id": "boundary-001",
                            "target_unit_ids": [packet["target_units"][0]["unit_id"]],
                            "route": {"entrypoint_id": entry},
                            "probe": {
                                "test_intent": "advance by two",
                                "activation_conditions": ["zero input"],
                            },
                            "invariant": {
                                "independent_oracle": "zero advances to two",
                                "supporting_evidence": "fixture arithmetic contract",
                                "expected_observation": "two",
                                "oracle_mode": "assertion",
                            },
                            "oracle_family": "increment",
                            "novelty_from_prior": "first attempt",
                            "bug_hypothesis": "incorrect increment",
                        }
                    ],
                    "context_requests": [],
                }
            else:
                response = {
                    "assets": [
                        {
                            "asset_id": "asset-001",
                            "boundary_id": "boundary-001",
                            "input_construction": "zero",
                            "observable_oracle": "public return is two",
                            "primary_oracle": "public equality",
                            "mocking_plan": "none",
                            "test_file": test_file,
                            "append_code": test_code,
                        }
                    ]
                }
            encoded = json.dumps(
                {
                    "choices": [{"message": {"content": json.dumps(response)}}],
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 10,
                        "total_tokens": 20,
                        "prompt_tokens_details": {"cached_tokens": 4},
                        "completion_tokens_details": {"reasoning_tokens": 3},
                    },
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    cert, key = tmp_path / "certificate.pem", tmp_path / "key.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-days",
            "1",
            "-subj",
            "/CN=127.0.0.1",
            "-addext",
            "subjectAltName=IP:127.0.0.1",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), ModelHandler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        command = [sys.executable, str(artifact / "run.py")] + [
            "probe",
            "--project",
            project,
            "--strategy",
            strategy,
            *(
                ["--repository", str(repository), "--revision", case["revisions"]["latest"], "--target", source]
                if automatic == "latest_file" else
                ["--case-id", "arithmetic", "--cases-root", str(case_path.parent.parent)]
                if automatic == "paired" else
                ["--case-id", "arithmetic"]
                if automatic in ("bundled", "bundled_setup") else
                ["--case-json", str(case_path)]
            ),
            *([] if automatic else [item for kind, root in roots.items() for item in (f"--{kind}-root", str(root))]),
            "--out-root",
            str(tmp_path / "output"),
            "--run-id",
            "smoke",
            "--provider",
            "openai",
            "--direct-samples",
            "1",
            "--samples",
            "0",
            "--soft-samples",
            "0",
            "--minimize-buggy-failures-per-sample",
            "0",
            "--model-retries",
            "0",
        ]
        if not ts and automatic != "bundled_setup":
            command += ["--python-bin", sys.executable]
        elif ts and automatic and automatic != "bundled_setup":
            command += ["--setup-script", str(setup_script)]
        env = {
            key: value
            for key, value in os.environ.items()
            if key.upper()
            not in {"PYTHONPATH", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "BENCHMARK_RELEASE_ROOT"}
        }
        env.update(
            OPENAI_API_KEY="fixture",
            OPENAI_BASE_URL=f"https://127.0.0.1:{server.server_port}/v1",
            SSL_CERT_FILE=str(cert),
            NODE_EXTRA_CA_CERTS=str(cert),
        )
        result = subprocess.run(
            command,
            cwd=tmp_path,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
        )
        assert result.returncode == 0, result.stdout
        run_dir = tmp_path / "output/smoke"
        assert not (run_dir / "summary.json").exists()
        assert json.loads((run_dir / "preflight.json").read_text())["passed"]
        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert manifest["project"] == project
        assert manifest["strategy"] == strategy
        if config.get("repository_url"):
            assert manifest["repository_url"] == config["repository_url"]
        assert not any(
            "cost" in key.lower() or "usd" in key.lower() for key in manifest["options"]
        )
        assert not (run_dir / "cost-budget.json").exists()
        assert "packet_count" not in manifest
        for kind, root in roots.items():
            if automatic:
                assert not Path(manifest[f"{kind}_checkout"]["path"]).exists()
            else:
                assert manifest[f"{kind}_checkout"] == {"path": str(root.resolve())}
        if automatic:
            preparation = tmp_path / "output/preparation/smoke"
            assert json.loads((preparation / "checkouts.json").read_text())["revisions"] == case["revisions"]
            assert (preparation / "prepare.log").is_file()
            if automatic in ("bundled", "bundled_setup"):
                assert (preparation / "prepare.log").read_text().count("1 files matched") == 2
            if automatic == "bundled_setup":
                assert (preparation / "prepare.log").read_text().count("Environment profile: fixture") == 2
                assert "setup_profiles" in json.loads((preparation / "checkouts.json").read_text())
        packet = json.loads((run_dir / "packet.json").read_text())
        assert manifest["revisions"] == case["revisions"]
        mode = "single_revision_discovery" if discovery else "paired_reveal"
        assert manifest["evaluation_mode"] == packet["evaluation_mode"] == mode
        assert not {"case_id", "revision", "repository_url"} & packet.keys()
        if ts:
            assert packet["test_command"] == config["probe"]["test_command"]
            assert not {
                "project", "language", "runId", "runDir", "out", "case",
                "buggy", "fixed", "evaluationMode", "resume",
            } & manifest["options"].keys()
        else:
            assert not {"out_root", "run_id", "evaluation_mode"} & manifest["options"].keys()
            assert not {"case_id", "revision", "repository_url", "test_command"} & packet.keys()
            assert all('"test_command"' not in prompt for prompt in requests)
        assert packet["generated_test_roots"] == [generated_root]
        assert manifest["options"]["directSamples" if ts else "direct_samples"] == 1
        assert manifest["options"]["samples"] == 0
        assert manifest["options"]["softSamples" if ts else "soft_samples"] == 0
        progress = json.loads((run_dir / "progress.json").read_text())
        assert len(progress["samples"]) == 1
        checkpoint = json.loads(Path(progress["samples"][0]["result_path"]).read_text())
        assert checkpoint["strategy"] == strategy
        assert checkpoint["sample_id"] == "direct-001"
        assert checkpoint["evaluation_mode"] == mode
        assert checkpoint["stable_failure_candidate" if discovery else "bug_revealed"]
        assert checkpoint["assets"]
        for asset in checkpoint["assets"]:
            proposal = json.loads(Path(asset["proposal_path"]).read_text())
            assert proposal["append_code"] == test_code
            assert proposal["test_file"] == test_file
            if discovery:
                assert "buggy" not in asset and "fixed" not in asset
                assert asset["confirmation"]["stable"]
                assert len(asset["confirmation"]["runs"]) == 2
                assert all(run["latest"]["status"] == "assertion_failed" for run in asset["confirmation"]["runs"])
        if discovery:
            assert not (tmp_path / "fixed").exists()
            assert "fixed_checkout" not in manifest and "buggy_checkout" not in manifest
        assert len(requests) == 2
        responses = list(run_dir.rglob("*.raw.json"))
        assert len(responses) == len(requests)
        for response_path in responses:
            raw = json.loads(response_path.read_text())
            assert raw["provider"] == "openai"
            assert raw["model"]
            assert raw["response"]["usage"] == {
                "prompt_tokens": 10,
                "completion_tokens": 10,
                "total_tokens": 20,
                "prompt_tokens_details": {"cached_tokens": 4},
                "completion_tokens_details": {"reasoning_tokens": 3},
            }
        for root in roots.values():
            assert not (root / test_file).exists()
        assert not list((tmp_path / "output").rglob("validation-*"))
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
