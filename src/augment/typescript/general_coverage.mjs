import { branchArms, normalizeProjectPath } from "./branch_coverage.mjs";
import { readJson } from "./json.mjs";

function positive(value) {
  if (Array.isArray(value)) {
    return value.some((item) => positive(item));
  }
  return Number(value ?? 0) > 0;
}

/** Normalize one validation run into source-stable guidance facts. */
export function normalizeObservedCoverage({ coverageJson, projectRoot }) {
  const raw = readJson(coverageJson);
  const files = {};
  for (const [rawPath, fileCoverage] of Object.entries(raw)) {
    if (!fileCoverage || typeof fileCoverage !== "object") {
      continue;
    }
    const filepath = normalizeProjectPath(
      fileCoverage.path ?? rawPath,
      projectRoot,
    );
    if (!filepath) {
      continue;
    }
    const executedLines = new Set();
    for (const [statementId, count] of Object.entries(fileCoverage.s ?? {})) {
      if (!positive(count)) {
        continue;
      }
      const location = fileCoverage.statementMap?.[statementId];
      const line = Number(location?.start?.line ?? 0);
      if (line > 0) {
        executedLines.add(line);
      }
    }
    const slots = branchArms(filepath, fileCoverage);
    const coveredSlots = slots
      .filter((slot) => slot.covered)
      .map((slot) => slot.slot_id);
    if (executedLines.size > 0 || coveredSlots.length > 0) {
      files[filepath] = {
        executed_lines: [...executedLines].sort((a, b) => a - b),
        branch_slots: slots.map((slot) => ({ ...slot, covered: undefined })),
        covered_branch_slots: coveredSlots.sort(),
      };
    }
  }
  return { files };
}

function expandRanges(ranges) {
  const lines = new Set();
  for (const range of ranges ?? []) {
    if (!Array.isArray(range) || range.length !== 2) {
      continue;
    }
    for (let line = Number(range[0]); line <= Number(range[1]); line += 1) {
      if (Number.isInteger(line) && line > 0) {
        lines.add(line);
      }
    }
  }
  return [...lines].sort((left, right) => left - right);
}

function coveredBranchCount(branch) {
  const generated = new Set(branch.generated_covered_slots ?? []);
  return Math.min(
    Number(branch.total ?? 0),
    Math.max(Number(branch.baseline_covered ?? 0), generated.size),
  );
}

/** Normalize per-file whole-project coverage facts used by generation. */
export function loadGeneralCoverage(facts) {
  const measuredFiles = facts?.files;
  if (
    !measuredFiles ||
    typeof measuredFiles !== "object" ||
    Array.isArray(measuredFiles)
  ) {
    throw new Error("General coverage facts must provide a files object");
  }

  const files = {};
  for (const [filepath, item] of Object.entries(measuredFiles)) {
    if (!filepath || !item || typeof item !== "object" || Array.isArray(item)) {
      throw new Error(`General coverage contains an invalid file record: ${filepath}`);
    }
    const totalLines = expandRanges(item.lines?.total);
    const totalLineSet = new Set(totalLines);
    // The official facts can retain executed lines for source files excluded
    // from the executable denominator. They are observations, not denominator
    // members, so only the intersection is eligible for project coverage.
    const coveredLines = expandRanges(item.lines?.covered).filter((line) =>
      totalLineSet.has(line),
    );
    const branchLines = new Set();
    const branches = (item.branches ?? []).map((branch) => {
      const line = Number(branch.line);
      const total = Number(branch.total ?? 0);
      const covered = Number(branch.covered ?? 0);
      if (
        !Number.isInteger(line) ||
        line <= 0 ||
        !Number.isInteger(total) ||
        total <= 0 ||
        !Number.isInteger(covered) ||
        covered < 0 ||
        covered > total ||
        branchLines.has(line)
      ) {
        throw new Error(
          `General coverage contains an invalid branch record: ${filepath}:${line}`,
        );
      }
      branchLines.add(line);
      return {
        line,
        total,
        baseline_covered: covered,
        generated_covered_slots: [],
      };
    });
    files[filepath] = {
      total_lines: totalLines,
      covered_lines: coveredLines,
      branches: branches.sort((left, right) => left.line - right.line),
    };
  }

  return { files };
}

/** Return the current whole-project coverage slice for one file target. */
export function generalCoverageForFile(state, filepath) {
  const file = state.files?.[filepath];
  if (!file) {
    throw new Error(`General coverage is missing source file: ${filepath}`);
  }
  const covered = new Set(file.covered_lines);
  return {
    filepath,
    total_lines: [...file.total_lines],
    covered_lines: [...file.covered_lines],
    uncovered_lines: file.total_lines.filter((line) => !covered.has(line)),
    branch_gaps: file.branches
      .map((branch) => {
        const coveredOutcomes = coveredBranchCount(branch);
        return {
          line: branch.line,
          total_outcomes: branch.total,
          covered_outcomes: coveredOutcomes,
          uncovered_outcomes: branch.total - coveredOutcomes,
        };
      })
      .filter((branch) => branch.uncovered_outcomes > 0),
  };
}

/** Compare file targets using the shared static ordinary-coverage priority. */
export function compareCoverageFiles(left, right) {
  return (
    right.uncovered_count - left.uncovered_count ||
    left.coverage_ratio - right.coverage_ratio ||
    right.denominator - left.denominator ||
    left.filepath.localeCompare(right.filepath)
  );
}

/** Rank an allowed source-file set from immutable round-zero coverage. */
export function rankCoverageFiles(state, allowedFiles) {
  return [...allowedFiles]
    .map((filepath) => {
      const file = state.files?.[filepath];
      if (!file) {
        throw new Error(`General coverage is missing source file: ${filepath}`);
      }
      const totalBranches = file.branches.reduce(
        (sum, branch) => sum + branch.total,
        0,
      );
      const coveredBranches = file.branches.reduce(
        (sum, branch) => sum + coveredBranchCount(branch),
        0,
      );
      const denominator = file.total_lines.length + totalBranches;
      const uncoveredCount =
        denominator - file.covered_lines.length - coveredBranches;
      return {
        filepath,
        uncovered_count: uncoveredCount,
        denominator,
        coverage_ratio:
          denominator > 0 ? (denominator - uncoveredCount) / denominator : 1,
      };
    })
    .filter((target) => target.denominator > 0 && target.uncovered_count > 0)
    .sort(compareCoverageFiles)
    .map((target, index) => ({ ...target, rank: index + 1 }));
}

/** Return the provable ordinary-coverage gain for one observed source file. */
export function acceptedCoverageGainForFile(state, acceptedCoverage, filepath) {
  const file = state.files?.[filepath];
  const observed = acceptedCoverage.files?.[filepath];
  if (!file || !observed) {
    return { filepath, new_covered_lines: [], branch_updates: [] };
  }

  const totalLines = new Set(file.total_lines);
  const coveredLines = new Set(file.covered_lines);
  const newLines = (observed.executed_lines ?? []).filter(
    (line) => totalLines.has(line) && !coveredLines.has(line),
  );
  const slotById = new Map(
    (observed.branch_slots ?? []).map((slot) => [slot.slot_id, slot]),
  );
  const observedByLine = new Map();
  for (const slotId of observed.covered_branch_slots ?? []) {
    const line = Number(slotById.get(slotId)?.line);
    if (!Number.isInteger(line)) continue;
    const slots = observedByLine.get(line) ?? new Set();
    slots.add(slotId);
    observedByLine.set(line, slots);
  }
  const branchUpdates = file.branches
    .map((branch) => {
      const previous = coveredBranchCount(branch);
      const generated = new Set(branch.generated_covered_slots ?? []);
      for (const slotId of observedByLine.get(branch.line) ?? []) {
        generated.add(slotId);
      }
      const next = Math.min(
        branch.total,
        Math.max(branch.baseline_covered, generated.size),
      );
      return {
        line: branch.line,
        new_covered_outcomes: next - previous,
      };
    })
    .filter((branch) => branch.new_covered_outcomes > 0);
  return {
    filepath,
    new_covered_lines: [...newLines].sort((left, right) => left - right),
    branch_updates: branchUpdates,
  };
}

function observedLines(coverage, filepath) {
  return new Set(
    (coverage.files?.[filepath]?.executed_lines ?? []).map(Number),
  );
}

/** Build the source-file line baseline produced by its selected seed test. */
export function targetLineCoverageFromObservation(
  generalCoverage,
  observedCoverage,
  filepath,
) {
  const totalLines = generalCoverageForFile(
    generalCoverage,
    filepath,
  ).total_lines;
  const observed = observedLines(observedCoverage, filepath);
  const coveredLines = totalLines.filter((line) => observed.has(line));
  const covered = new Set(coveredLines);
  return {
    filepath,
    total_lines: totalLines,
    covered_lines: coveredLines,
    uncovered_lines: totalLines.filter((line) => !covered.has(line)),
  };
}

/** Return lines newly reached relative to one target's local coverage union. */
export function targetLineCoverageGain(targetCoverage, observedCoverage) {
  const total = new Set(targetCoverage.total_lines);
  const covered = new Set(targetCoverage.covered_lines);
  return [...observedLines(observedCoverage, targetCoverage.filepath)]
    .filter((line) => total.has(line) && !covered.has(line))
    .sort((left, right) => left - right);
}

/** Merge accepted test coverage into the target-local source-line union. */
export function applyObservedCoverageToTargetLineCoverage(
  targetCoverage,
  observedCoverage,
) {
  const newLines = targetLineCoverageGain(targetCoverage, observedCoverage);
  const covered = new Set([...targetCoverage.covered_lines, ...newLines]);
  targetCoverage.covered_lines = [...covered].sort((left, right) => left - right);
  targetCoverage.uncovered_lines = targetCoverage.total_lines.filter(
    (line) => !covered.has(line),
  );
  return {
    covered_lines: newLines,
    covered_branch_outcomes: 0,
  };
}

/**
 * Merge one generated test's coverage into the general guidance state.
 *
 * Coverage facts expose baseline branch counts rather than canonical ids. We
 * therefore compare the baseline count with the generated canonical-arm union
 * instead of assuming that the two sets are disjoint. This conservative merge
 * never reports an unproven branch gain. Exact LDH measurement is performed
 * by the post-run projection scripts.
 */
export function applyAcceptedCoverageToGeneralCoverage(
  state,
  acceptedCoverage,
) {
  const updates = [];
  for (const [filepath, observed] of Object.entries(
    acceptedCoverage.files ?? {},
  )) {
    const file = state.files?.[filepath];
    if (!file) {
      continue;
    }

    const gain = acceptedCoverageGainForFile(state, acceptedCoverage, filepath);

    const coveredLines = new Set(file.covered_lines);
    const newLines = gain.new_covered_lines;
    for (const line of newLines) {
      coveredLines.add(line);
    }
    file.covered_lines = [...coveredLines].sort((left, right) => left - right);

    const branches = new Map(
      file.branches.map((branch) => [branch.line, branch]),
    );
    const slotById = new Map(
      (observed.branch_slots ?? []).map((slot) => [slot.slot_id, slot]),
    );
    for (const slotId of observed.covered_branch_slots ?? []) {
      const slot = slotById.get(slotId);
      const branch = branches.get(Number(slot?.line));
      if (!branch) {
        continue;
      }
      branch.generated_covered_slots = [
        ...new Set([...(branch.generated_covered_slots ?? []), slotId]),
      ].sort();
    }

    const branchUpdates = gain.branch_updates;
    if (newLines.length > 0 || branchUpdates.length > 0) {
      updates.push({
        filepath,
        new_covered_lines: [...newLines].sort((left, right) => left - right),
        branch_updates: branchUpdates,
      });
    }
  }

  return {
    new_covered_lines: updates.reduce(
      (sum, update) => sum + update.new_covered_lines.length,
      0,
    ),
    new_covered_branch_outcomes: updates.reduce(
      (sum, update) =>
        sum +
        update.branch_updates.reduce(
          (count, branch) => count + branch.new_covered_outcomes,
          0,
        ),
      0,
    ),
    files: updates,
  };
}
