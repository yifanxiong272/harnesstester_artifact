/** Progress checkpoints and stopping policy for target probing. */

import path from "node:path";

import { writeJson } from "../support/json.mjs";
import { compactText, iterAssets } from "./reporting.mjs";
import { isDiscovery } from "./options.mjs";

export function revealCandidateCount(rows) {
  return iterAssets(rows).filter(
    (asset) => asset.bug_revealed || asset.status === "revealed",
  ).length;
}

export function candidateLimitReached(rows, options) {
  return (
    confirmedCandidateCount(rows, options.evaluationMode) >=
    Math.max(1, options.maxRevealCandidates)
  );
}

export function confirmedCandidateCount(rows, evaluationMode) {
  return isDiscovery(evaluationMode)
    ? iterAssets(rows).filter(
        (asset) =>
          asset.stable_failure_candidate ||
          asset.status === "stable_failure_candidate",
      ).length
    : revealCandidateCount(rows);
}

export function shouldStopAfterRow(
  rows,
  options,
  deferDiscoveryCandidateStop = false,
) {
  const row = rows.at(-1);
  if (!row) {
    return false;
  }
  if (
    candidateLimitReached(rows, options) &&
    !(deferDiscoveryCandidateStop && isDiscovery(options.evaluationMode))
  ) {
    return true;
  }
  const abort = workflowAbortForRows(rows, options.maxWorkflowErrors);
  if (abort) {
    row.workflow_abort = abort;
    return true;
  }
  return false;
}

function workflowAbortForRows(rows, threshold) {
  const limit = Math.max(0, Number(threshold || 0));
  if (limit <= 0) {
    return null;
  }
  const counts = new Map();
  for (const row of rows) {
    if (row.status !== "error" || !row.error) {
      continue;
    }
    const key = compactText(
      `${row.error.type || "Error"}: ${row.error.message || ""}`,
      240,
    );
    const count = (counts.get(key) || 0) + 1;
    counts.set(key, count);
    if (count >= limit) {
      return {
        reason: "repeated_sample_error",
        stop_reason: "workflow_error",
        error_key: key,
        threshold: limit,
      };
    }
  }
  return null;
}

export function shouldRunSoftExtension(
  packet,
  rows,
  softSamples,
  maxRevealCandidates = 1,
) {
  if (
    softSamples <= 0 ||
    confirmedCandidateCount(rows, packet.evaluation_mode) >=
      Math.max(1, maxRevealCandidates)
  ) {
    return false;
  }
  return (packet.target_units || []).length > 1;
}

/** Index completed result files and retain any budget exception. */
export function writeProgress(runDir, rows, error = null) {
  writeJson(path.join(runDir, "progress.json"), {
    samples: rows
      .filter((row) => row.sample_id)
      .map((row) => ({
        sample_id: row.sample_id,
        result_path: path.join(runDir, "samples", row.sample_id, "result.json"),
      })),
    ...(error ? { error: { type: error.name, message: error.message } } : {}),
  });
}
