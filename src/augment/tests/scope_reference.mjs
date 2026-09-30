import {
  branchArms,
  normalizeProjectPath,
} from "../typescript/branch_coverage.mjs";

function positive(value) {
  return Array.isArray(value) ? value.some(positive) : Number(value ?? 0) > 0;
}

/** Reference projection used to check preparation against raw branch-arm facts. */
export function buildAugmentScope(regions, coverage, { project, projectRoot }) {
  const scope = new Map();
  for (const { location } of [...regions.sources, ...regions.data_dependence]) {
    const { filepath, start_line: start, end_line: end } = location;
    if (!scope.has(filepath)) scope.set(filepath, new Set());
    for (let line = start; line <= end; line += 1)
      scope.get(filepath).add(line);
  }
  const files = new Map();
  for (const [rawPath, record] of Object.entries(coverage)) {
    if (
      !record ||
      typeof record !== "object" ||
      !record.statementMap ||
      !record.branchMap
    ) {
      throw new Error(
        "reference coverage must contain a complete Istanbul/V8 file coverage map",
      );
    }
    const filepath = normalizeProjectPath(record.path ?? rawPath, projectRoot);
    if (!scope.has(filepath)) continue;
    if (files.has(filepath))
      throw new Error(`duplicate coverage file: ${filepath}`);
    files.set(filepath, record);
  }

  const targets = [];
  for (const [filepath, lines] of [...scope].sort(([a], [b]) =>
    a.localeCompare(b),
  )) {
    const measured = files.get(filepath);
    if (!measured)
      throw new Error(
        `baseline coverage is missing LDH source file: ${filepath}`,
      );
    const total = new Set();
    const covered = new Set();
    for (const [id, location] of Object.entries(measured.statementMap)) {
      const line = location.start?.line;
      if (!lines.has(line)) continue;
      total.add(line);
      if (positive(measured.s?.[id])) covered.add(line);
    }
    const arms = branchArms(filepath, measured).filter((arm) =>
      lines.has(arm.line),
    );
    if (total.size || arms.length) {
      targets.push({
        filepath,
        uncovered_lines: [...total]
          .filter((line) => !covered.has(line))
          .sort((a, b) => a - b),
        uncovered_branch_slots: arms
          .filter((arm) => !arm.covered)
          .map((arm) => arm.slot_id)
          .sort(),
      });
    }
  }
  return {
    project,
    scope: "ldh_executable_files",
    unit: "source_file",
    branch_precision: "canonical-branch-arm",
    targets,
  };
}
