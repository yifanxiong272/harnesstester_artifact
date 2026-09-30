import path from "node:path";
import { CaseBudgetExceeded, limitTimeout } from "./deadline.mjs";
import { ensureDir, writeJson } from "../support/json.mjs";
import { promptPriorAttempts, promptPacket } from "../prompt/prompts.mjs";
import { PAIRED_REVEAL_EVALUATION } from "./options.mjs";
import { focusTargetPacket, softTargetPacket, unitIdentity } from "./focus.mjs";
import {
  candidateLimitReached,
  shouldRunSoftExtension,
  shouldStopAfterRow,
  writeProgress,
} from "./progress.mjs";
import {
  InvalidModelOutputError,
  generateTargetPlanAndContext,
  generateProbeAssets,
  priorAttemptLedger,
} from "./generation.mjs";
import { runSampleAssets } from "./candidate.mjs";
import { aggregateAssetRows } from "./reporting.mjs";

const DIRECT_PROMPT_STYLE = "direct";
const STRICT_PROMPT_STYLE = "strict";

export async function runGuidedCaseSamples(runtime, packet, runDir) {
  const options = runtime.options;
  const rows = [];
  const harnessRepairBudget = options.harnessRepairsPerSample;
  const lanes = [
    ["direct_probe", "direct", options.directSamples, DIRECT_PROMPT_STYLE],
    ["hard_core", "sample", options.samples, STRICT_PROMPT_STYLE],
    ["soft_extension", "soft", options.softSamples, STRICT_PROMPT_STYLE],
  ];
  for (const [lane, prefix, budget, promptStyle] of lanes) {
    if (lane === "hard_core" && candidateLimitReached(rows, options)) break;
    if (
      lane === "soft_extension" &&
      !shouldRunSoftExtension(packet, rows, budget, options.maxRevealCandidates)
    )
      break;
    for (let index = 1; index <= Math.max(0, budget); index += 1) {
      const sampleId = `${prefix}-${String(index).padStart(3, "0")}`;
      const row = await runLaneSample({
        runtime,
        packet:
          lane === "soft_extension"
            ? softTargetPacket(packet, index)
            : focusTargetPacket(packet, index, lane),
        sampleId,
        sampleDir: path.join(runDir, "samples", sampleId),
        priorAttempts: priorAttemptLedger(rows),
        promptStyle,
        harnessRepairBudget,
        lane,
      });
      rows.push(row);
      writeProgress(runDir, rows);
      if (shouldStopAfterRow(rows, options, lane === "direct_probe"))
        return rows;
    }
  }
  return rows;
}

export async function runLaneSample({ lane, ...sample }) {
  const { runtime, packet, sampleDir } = sample;
  limitTimeout();
  const resultPath = path.join(sampleDir, "result.json");
  const finish = (row) => {
    row.strategy = runtime.options.strategy;
    row.lane = lane;
    row.evaluation_mode = runtime.options.evaluationMode;
    writeJson(resultPath, row);
    return row;
  };
  try {
    return finish(
      await runTargetSample({
        ...sample,
        runtime: { ...runtime, packet },
        onProgress: finish,
      }),
    );
  } catch (error) {
    if (error instanceof CaseBudgetExceeded || error?.retryable) {
      throw error;
    }
    return finish(sampleError(sampleDir, error));
  }
}

export async function runTargetSample({
  runtime,
  packet,
  sampleId,
  sampleDir,
  priorAttempts,
  promptStyle,
  harnessRepairBudget,
  onProgress = null,
}) {
  ensureDir(sampleDir);
  writeJson(
    path.join(sampleDir, "prior-attempts.json"),
    promptPriorAttempts(priorAttempts),
  );
  writeJson(path.join(sampleDir, "prompt-packet.json"), promptPacket(packet));
  const focusUnit = packet.focus_target_unit || {};
  const base = sampleBaseRow(packet, sampleId, sampleDir, focusUnit);

  const planData = await generateTargetPlanAndContext({
    runtime,
    packet,
    sampleDir,
    priorAttempts,
    promptStyle,
  });
  packet.boundary_plan = planData.boundary_plan || [];

  let row;
  if (packet.boundary_plan.length === 0) {
    row = {
      ...base,
      status: "exhausted",
      bug_revealed: false,
      assets: [],
      exhausted_reason: planData.exhausted_reason,
    };
  } else {
    const probe = await generateProbeAssets({
      runtime,
      packet,
      plan: planData,
      sampleDir,
      priorAttempts,
      promptStyle,
    });
    const assetRows = await runSampleAssets({
      runtime,
      packet,
      plan: planData,
      sampleDir,
      assets: probe.assets,
      minimizationBudget: runtime.options.minimizeBuggyFailuresPerSample,
      harnessRepairBudget,
      onProgress: onProgress
        ? (rows) => onProgress(aggregateAssetRows(
            base, probe.path, rows, runtime.options.evaluationMode,
          ))
        : null,
    });
    row = aggregateAssetRows(
      base,
      probe.path,
      assetRows,
      runtime.options.evaluationMode,
    );
  }
  return row;
}

export function sampleBaseRow(packet, sampleId, sampleDir, focusUnit) {
  const row = {
    sample_id: sampleId,
    evaluation_mode: packet.evaluation_mode || PAIRED_REVEAL_EVALUATION,
    prompt_path: path.join(sampleDir, "implementation.prompt.md"),
    target_unit_ids: (packet.target_units || []).map((unit) => unit.unit_id),
  };
  if (focusUnit.unit_id) {
    row.focus_target_unit_id = String(focusUnit.unit_id);
    row.focus_target_unit = unitIdentity(focusUnit);
  }
  return row;
}

export function sampleError(sampleDir, error) {
  ensureDir(sampleDir);
  const payload = { type: error.name, message: error.message };
  writeJson(path.join(sampleDir, "error.json"), payload);
  return {
    sample_id: path.basename(sampleDir),
    status:
      error instanceof InvalidModelOutputError
        ? "invalid_model_output"
        : "error",
    error: payload,
  };
}
