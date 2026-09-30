/** Run selected targets on prepared latest or paired revision checkouts. */
import fs from "node:fs";
import path from "node:path";
import { readJson, writeJson } from "../support/json.mjs";
import { buildTargetPacket } from "../input/target_packets.mjs";
import { promptPacket } from "../prompt/prompts.mjs";
import { preparedValidation } from "./session.mjs";
import { loadModelEnv } from "./client.mjs";
import { CaseBudgetExceeded, withCaseTimeBudget } from "./deadline.mjs";
import {
  PAIRED_REVEAL_EVALUATION,
  SINGLE_REVISION_DISCOVERY_EVALUATION,
  runOptions,
  validateRunOptions,
  validateRunPathPart,
} from "./options.mjs";
import {
  preflightTargetRun,
  runRevisionValidationPreflight,
} from "./preflight.mjs";
import { runGuidedCaseSamples } from "./workflow.mjs";
import { writeProgress } from "./progress.mjs";

function resolvedOutputPath(value) {
  const suffix = [];
  let parent = path.resolve(value);
  while (!fs.existsSync(parent)) {
    suffix.unshift(path.basename(parent));
    parent = path.dirname(parent);
  }
  return path.join(fs.realpathSync(parent), ...suffix);
}

export async function runPreparedCase({
  caseData,
  buggyRoot,
  fixedRoot,
  latestRoot,
  config,
  options,
  runDir,
}) {
  const normalized = runOptions(options);
  const discovery = latestRoot !== undefined && latestRoot !== null;
  if (discovery && (buggyRoot != null || fixedRoot != null)) {
    throw new Error(
      "latest and paired checkout inputs are mutually exclusive",
    );
  }
  if (!discovery && (!buggyRoot || !fixedRoot)) {
    throw new Error("provide a latest checkout or both buggy/fixed checkouts");
  }
  normalized.evaluationMode = discovery
    ? SINGLE_REVISION_DISCOVERY_EVALUATION
    : PAIRED_REVEAL_EVALUATION;
  validateRunOptions(normalized);
  const caseId = String(caseData.case_id);
  validateRunPathPart(caseId, "case_id");
  const roots = discovery
    ? { latest: fs.realpathSync(latestRoot) }
    : {
        buggy: fs.realpathSync(buggyRoot),
        fixed: fs.realpathSync(fixedRoot),
      };
  runDir = resolvedOutputPath(runDir);
  for (const [kind, root] of Object.entries(roots)) {
    if (!fs.statSync(root).isDirectory() || !caseData.revisions?.[kind])
      throw new Error(`missing ${kind} checkout or revision`);
    if (
      root === runDir ||
      runDir.startsWith(`${root}${path.sep}`) ||
      root.startsWith(`${runDir}${path.sep}`)
    ) {
      throw new Error("output and checkout directories must be disjoint");
    }
  }
  fs.mkdirSync(path.dirname(runDir), { recursive: true });
  fs.mkdirSync(runDir);
  try {
    await withCaseTimeBudget(
      runDir,
      normalized.caseTimeBudgetSeconds,
      async () => {
        const settings = { ...config.probe, ...caseData.validation };
        const packet = buildTargetPacket({
          project: config.project,
          strategy: normalized.strategy,
          projectRoot: Object.values(roots)[0],
          targetUnits:
            (discovery
              ? caseData.target_units
              : caseData.patch_targets?.target_units) || [],
          testCommand: settings.test_command || [
            "pnpm",
            "exec",
            "vitest",
            "run",
            "<generated-test-file>",
          ],
          generatedTestRoots: settings.generated_test_roots || [
            "test/generated/benchmarkbr",
          ],
        });
        packet.evaluation_mode = normalized.evaluationMode;
        const manifest = {
          case_id: caseId,
          project: config.project,
          revisions: Object.fromEntries(
            Object.keys(roots).map((kind) => [
              kind,
              String(caseData.revisions[kind]),
            ]),
          ),
          strategy: normalized.strategy,
          evaluation_mode: normalized.evaluationMode,
          options: Object.fromEntries(
            Object.entries(normalized).filter(
              ([key]) =>
                !["modelClient", "validationRunner", "evaluationMode"].includes(
                  key,
                ),
            ),
          ),
          source_roots: config.source_roots || [],
          ...Object.fromEntries(
            Object.entries(roots).map(([kind, root]) => [
              `${kind}_checkout`,
              { path: root },
            ]),
          ),
        };
        if (config.repository_url) {
          manifest.repository_url = String(config.repository_url);
        }
        const runtime = {
          caseData,
          roots,
          manifest,
          packet,
          env: loadModelEnv(normalized.envFile),
          options: {
            ...normalized,
            validationRunner: normalized.validationRunner || preparedValidation,
          },
        };
        writeJson(path.join(runDir, "manifest.json"), manifest);
        writeJson(path.join(runDir, "packet.json"), packet);
        writeJson(
          path.join(runDir, "prompt-packet.json"),
          promptPacket(packet),
        );
        const preflight = preflightTargetRun({ manifest, packet });
        if (preflight.passed) {
          const record = runRevisionValidationPreflight(runtime, runDir);
          preflight.validation = record;
          preflight.passed = record.passed;
          if (!record.passed)
            preflight.errors.push({
              check: "revision_validation_preflight",
              path: record.path,
            });
          else if (
            record.target_import?.attempted &&
            !record.target_import.passed
          ) {
            preflight.warnings.push({
              kind: "target_import_diagnostic_failed",
              path: record.path,
            });
          }
        }
        writeJson(path.join(runDir, "preflight.json"), preflight);
        const rows = preflight.passed
          ? await runGuidedCaseSamples(runtime, packet, runDir)
          : [];
        writeProgress(runDir, rows);
      },
    );
  } catch (error) {
    if (!(error instanceof CaseBudgetExceeded)) throw error;
    const samples = path.join(runDir, "samples");
    const rows = fs.existsSync(samples)
      ? fs
          .readdirSync(samples)
          .sort()
          .map((name) => path.join(samples, name, "result.json"))
          .filter((file) => fs.existsSync(file))
          .map(readJson)
      : [];
    writeProgress(runDir, rows, error);
  }
  return runDir;
}
