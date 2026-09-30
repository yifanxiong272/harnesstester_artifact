import { loadGeneralCoverage } from "../general_coverage.mjs";
import { safeRelativePath } from "../paths.mjs";
import { parseSeedCoverage } from "./seed_coverage.mjs";

/** Count unique measured lines from sorted, disjoint inclusive ranges. */
function lineCount(ranges) {
  if (!Array.isArray(ranges)) throw new Error("Test coverage must contain line ranges");
  let count = 0;
  let previous = 0;
  for (const range of ranges) {
    if (!Array.isArray(range) || range.length !== 2 ||
        !range.every(Number.isInteger) || range[0] <= previous || range[1] < range[0]) {
      throw new Error("Test coverage ranges must be positive, sorted, and disjoint");
    }
    count += range[1] - range[0] + 1;
    previous = range[1];
  }
  return count;
}

/** Derive the workflow's file scope and seed scores from measured input facts. */
export function prepareInputs(regions, coverage, project) {
  if (coverage.project !== project || !Array.isArray(regions.sources) ||
      !Array.isArray(regions.data_dependence)) {
    throw new Error(`Regions and coverage must describe project ${project}`);
  }
  const generalCoverage = loadGeneralCoverage(coverage);
  const regionsByFile = new Map();
  for (const { location } of [...regions.sources, ...regions.data_dependence]) {
    const { filepath, start_line: start, end_line: end } = location ?? {};
    if (!safeRelativePath(filepath) || !Number.isInteger(start) || start < 1 ||
        !Number.isInteger(end) || end < start) {
      throw new Error("LDH regions contain an invalid source location");
    }
    if (!regionsByFile.has(filepath)) regionsByFile.set(filepath, []);
    regionsByFile.get(filepath).push([start, end]);
  }
  const ldhFiles = new Set();
  for (const [filepath, ranges] of regionsByFile) {
    const measured = generalCoverage.files[filepath];
    if (!measured) throw new Error(`Coverage inputs are missing target file ${filepath}`);
    const inRegion = line => ranges.some(([start, end]) => start <= line && line <= end);
    const covered = new Set(measured.covered_lines);
    if (measured.total_lines.some(line => inRegion(line) && !covered.has(line)) ||
        measured.branches.some(branch => inRegion(branch.line) && branch.baseline_covered < branch.total)) {
      ldhFiles.add(filepath);
    }
  }

  if (!coverage.test_coverage || typeof coverage.test_coverage !== "object" ||
      Array.isArray(coverage.test_coverage)) {
    throw new Error("Coverage inputs must include test_coverage attributed to existing test files");
  }
  const generalTestScores = {};
  for (const [filepath, tests] of Object.entries(coverage.test_coverage)) {
    if (!safeRelativePath(filepath) || !tests || typeof tests !== "object" || Array.isArray(tests)) {
      throw new Error(`Invalid test coverage source: ${filepath}`);
    }
    generalTestScores[filepath] = Object.entries(tests).map(([testFile, observation]) => {
      if (!safeRelativePath(testFile)) throw new Error(`Invalid test coverage path: ${testFile}`);
      return {
        test_file: testFile,
        score: lineCount(observation?.lines) + lineCount(observation?.branch_lines),
      };
    }).filter(item => item.score > 0);
  }
  return {
    ldhFiles,
    generalCoverage,
    generalTestScores,
    seedCoverage: parseSeedCoverage(coverage.seed_coverage ?? null, project),
  };
}
