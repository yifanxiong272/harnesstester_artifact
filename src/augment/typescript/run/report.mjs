import path from "node:path";
import { performance } from "node:perf_hooks";
import { generalCoverageForFile } from "../general_coverage.mjs";
import { writeJson } from "../json.mjs";

export function startTimer() {
  return { started_at: new Date().toISOString(), monotonic_ms: performance.now() };
}

export function finishTimer(timer) {
  return {
    started_at: timer.started_at,
    finished_at: new Date().toISOString(),
    duration_ms: Math.round((performance.now() - timer.monotonic_ms) * 1000) / 1000,
  };
}

/** Persist one latest coverage state and a compact per-round timeline. */
export function writeProgress({
  runDir,
  config,
  rows,
  checkpoints,
  generalCoverage,
  stopReason,
  elapsedMs,
}) {
  const totals = {
    covered_lines: 0,
    total_lines: 0,
    covered_branches: 0,
    total_branches: 0,
  };
  for (const [file, coverage] of Object.entries(generalCoverage.files)) {
    const gaps = generalCoverageForFile(generalCoverage, file);
    const total = coverage.branches.reduce((n, branch) => n + branch.total, 0);
    totals.covered_lines += coverage.covered_lines.length;
    totals.total_lines += coverage.total_lines.length;
    totals.total_branches += total;
    totals.covered_branches +=
      total - gaps.branch_gaps.reduce((n, gap) => n + gap.uncovered_outcomes, 0);
  }
  if (checkpoints.at(-1)?.round !== rows.length) {
    checkpoints.push({
      round: rows.length,
      elapsed_seconds: elapsedMs / 1000,
      ...totals,
    });
  }
  writeJson(path.join(runDir, "coverage.json"), generalCoverage);
  writeJson(path.join(runDir, "results.json"), rows);
  writeJson(path.join(runDir, "progress.json"), {
    ...config,
    stop_reason: stopReason,
    elapsed_seconds: elapsedMs / 1000,
    checkpoints,
  });
}
