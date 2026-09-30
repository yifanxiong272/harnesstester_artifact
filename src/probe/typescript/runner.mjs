#!/usr/bin/env node
/** Adapt command-line arguments for one prepared TypeScript probe case. */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { loadModelEnv } from "./run/client.mjs";
import { runOptions, validateRunOptions, validateRunPathPart } from "./run/options.mjs";

const artifactRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../..",
);
const names = [
  "project",
  "language",
  "case-json",
  "buggy-root",
  "fixed-root",
  "latest-root",
  "out-root",
  "run-id",
  "model",
  "provider",
  "env-file",
  "model-timeout",
  "model-retries",
  "strategy",
  "direct-samples",
  "samples",
  "soft-samples",
  "assets-per-sample",
  "timeout",
  "context-requests",
  "harness-context-requests",
  "harness-repair-attempts",
  "harness-repairs-per-sample",
  "minimize-buggy-failures-per-sample",
  "minimization-preserve-attempts",
  "minimization-failure-excerpt-chars",
  "max-workflow-errors",
  "max-reveal-candidates",
  "reveal-confirmation-runs",
  "case-time-budget-seconds",
  "repair-context-requests",
  "repair-attempts",
  "max-reveals",
  "confirmations",
];
export function parseProbeArgs(argv = process.argv.slice(2)) {
  const { values } = parseArgs({
    args: argv,
    options: {
      ...Object.fromEntries(names.map((name) => [name, { type: "string" }])),
      help: { type: "boolean", short: "h" },
    },
  });
  if (values.help) {
    console.log(
      "Usage: python3 run.py probe --project NAME --case-json CASE (--latest-root PATH | --buggy-root PATH --fixed-root PATH) --out-root PATH\nOptions:\n" +
        names.map((name) => `  --${name} VALUE`).join("\n"),
    );
    return null;
  }
  const options = Object.fromEntries(
    Object.entries(values).map(([key, value]) => [
      key.replace(/-([a-z])/gu, (_, c) => c.toUpperCase()),
      value,
    ]),
  );
  const env = loadModelEnv(values["env-file"]);
  Object.assign(options, {
    model:
      values.model ||
      env.LLM_MODEL ||
      env.OPENAI_MODEL ||
      "gpt-5-mini",
    provider: values.provider || process.env.LLM_PROVIDER || "openai",
    strategy: values.strategy || "target_probe_ldh",
    modelTimeoutMs: Number(values["model-timeout"] ?? 120) * 1000,
  });
  for (const [alias, name] of Object.entries({
    "repair-context-requests": "harnessContextRequests",
    "repair-attempts": "harnessRepairAttempts",
    "max-reveals": "maxRevealCandidates",
    confirmations: "revealConfirmationRuns",
  }))
    if (values[alias] !== undefined) options[name] = Number(values[alias]);
  if (!["openai", "openrouter"].includes(options.provider)) {
    throw new Error(`unsupported model provider: ${options.provider}`);
  }
  if (values.language && values.language !== "typescript") {
    throw new Error("--language must match the TypeScript project");
  }
  validateRunOptions(runOptions(options));
  if (values["run-id"]) validateRunPathPart(values["run-id"], "run_id");
  return { values, options };
}

async function main() {
  const parsed = parseProbeArgs();
  if (!parsed) return;
  const { values, options } = parsed;
  const latest = values["latest-root"] !== undefined;
  if (
    latest &&
    (values["buggy-root"] !== undefined || values["fixed-root"] !== undefined)
  ) {
    throw new Error("use --latest-root or the --buggy-root/--fixed-root pair");
  }
  for (const key of [
    "project",
    "case-json",
    ...(latest ? ["latest-root"] : ["buggy-root", "fixed-root"]),
  ]) {
    if (!values[key]) throw new Error(`--${key} is required`);
  }
  const config = JSON.parse(
    fs.readFileSync(path.join(artifactRoot, "resources/projects.json"), "utf8"),
  )[values.project];
  if (config?.language !== "typescript")
    throw new Error(`unknown TypeScript project: ${values.project}`);
  const caseData = JSON.parse(fs.readFileSync(values["case-json"], "utf8"));
  if ((caseData.project ?? values.project) !== values.project) {
    throw new Error("--project does not match the selected case");
  }
  const runId = values["run-id"] || `${caseData.case_id}-${Date.now()}`;
  validateRunPathPart(runId, "run_id");
  const outRoot =
    values["out-root"] || path.join(artifactRoot, "outputs", values.project, "probe");
  const { runPreparedCase } = await import("./run/case.mjs");
  const result = await runPreparedCase({
    caseData,
    config: { ...config, project: values.project },
    options,
    buggyRoot: values["buggy-root"],
    fixedRoot: values["fixed-root"],
    latestRoot: values["latest-root"],
    runDir: path.join(outRoot, runId),
  });
  console.log(result);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await main();
}
