import path from "node:path";
import { parseArgs } from "node:util";
import { readJson } from "./json.mjs";

const OPTIONS = {
  project: { type: "string" },
  language: { type: "string" },
  "base-input": { type: "string" },
  "project-root": { type: "string" },
  "out-root": { type: "string" },
  rounds: { type: "string", default: "1" },
  "time-budget-seconds": { type: "string", default: "0" },
  "run-id": { type: "string" },
  provider: { type: "string", default: "openai" },
  model: { type: "string" },
  strategy: { type: "string", default: "contract_directed" },
  "acceptance-policy": { type: "string", default: "passing_subset" },
  "env-file": { type: "string" },
  "timeout-seconds": { type: "string", default: "600" },
  "repair-context-requests": { type: "string", default: "0" },
  quiet: { type: "boolean" },
  help: { type: "boolean", short: "h" },
};

export function parseAugmentArgs(scriptName, argv = process.argv.slice(2)) {
  const { values } = parseArgs({ args: argv, options: OPTIONS });
  if (values.help) {
    console.log(
      `Usage: ${scriptName} --project <name> --base-input <file> [options]\n` +
        Object.entries(OPTIONS)
          .map(
            ([name, option]) =>
              `  --${name}${option.type === "string" ? " <value>" : ""}` +
              (option.default === undefined ? "" : ` (default: ${option.default})`),
          )
          .join("\n"),
    );
    return null;
  }
  if (!values.project) throw new Error("--project is required");
  if (!values["base-input"]) throw new Error("--base-input is required");
  if (values.language && values.language !== "typescript") {
    throw new Error("Use python3 run.py augment --project NAME for Python projects");
  }
  return values;
}

export async function runAugmentCli({
  values,
  defaultOutRoot,
  measureTestFileCoverage,
  validateGeneratedTest,
  testPackages,
}) {
  const baseInputFile = path.resolve(values["base-input"]);
  if (readJson(baseInputFile).project !== values.project) {
    throw new Error("base input project does not match --project");
  }
  const { runCoverageModelBacked } = await import("./run/workflow.mjs");
  const result = await runCoverageModelBacked({
    baseInputFile,
    projectRoot: values["project-root"],
    outRoot: path.resolve(values["out-root"] ?? defaultOutRoot),
    runId: values["run-id"],
    rounds: Number(values.rounds),
    timeBudgetSeconds: Number(values["time-budget-seconds"]),
    provider: values.provider,
    model: values.model,
    envFile: values["env-file"],
    timeoutSeconds: Number(values["timeout-seconds"]),
    repairContextRequests: Number(values["repair-context-requests"]),
    strategy: values.strategy,
    acceptancePolicy: values["acceptance-policy"],
    measureTestFileCoverage,
    validateGeneratedTest,
    testPackages,
  });
  if (!values.quiet) console.log(result.runDir);
  return result;
}
