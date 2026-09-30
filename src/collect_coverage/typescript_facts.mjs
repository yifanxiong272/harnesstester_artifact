/** Convert Vitest's Istanbul-format reports into file-keyed augmentation inputs. */
import { branchArms, normalizeProjectPath } from "../augment/typescript/branch_coverage.mjs";

function positive(value) {
  return Array.isArray(value) ? value.some(positive) : Number(value ?? 0) > 0;
}

function ranges(values) {
  const result = [];
  for (const value of [...values].sort((a, b) => a - b)) {
    const last = result.at(-1);
    if (last && last[1] + 1 === value) last[1] = value;
    else result.push([value, value]);
  }
  return result;
}

/** Merge by source-stable branch identity; test outcomes do not filter coverage. */
export class CoverageFacts {
  constructor(project, root, sources) {
    this.project = project;
    this.root = root;
    this.sources = new Set(sources);
    this.files = new Map();
    this.testCoverage = {};
  }

  add(report, { denominator = false, testFile = null } = {}) {
    if (!report || typeof report !== "object" || Array.isArray(report)) {
      throw new Error("coverage report must be an Istanbul file map");
    }
    for (const [rawPath, value] of Object.entries(report)) {
      const file = normalizeProjectPath(value?.path ?? rawPath, this.root);
      if (!this.sources.has(file)) continue;
      if (!value.statementMap || !value.s || !value.branchMap || !value.b) {
        throw new Error(`coverage maps missing for ${file}`);
      }
      if (!this.files.has(file)) this.files.set(file, {
        denominator: false, total: new Set(), covered: new Set(),
        arms: new Map(), coveredArms: new Set(),
      });
      const row = this.files.get(file);
      const executed = new Set();
      for (const [id, location] of Object.entries(value.statementMap)) {
        const line = Number(location.start?.line);
        if (!Number.isInteger(line) || line <= 0) continue;
        if (denominator) row.total.add(line);
        else if (positive(value.s[id])) {
          row.covered.add(line);
          executed.add(line);
        }
      }
      for (const arm of branchArms(file, value)) {
        if (!Number.isInteger(arm.line) || arm.line <= 0) continue;
        if (denominator) row.arms.set(arm.slot_id, arm.line);
        else if (arm.covered) row.coveredArms.add(arm.slot_id);
      }
      if (denominator) row.denominator = true;
      if (!testFile) continue;
      const branchLines = new Set();
      for (const [id, counts] of Object.entries(value.b)) {
        if (!positive(counts)) continue;
        const branch = value.branchMap[id] ?? {};
        const fallback = branch.loc?.start?.line;
        const locations = (branch.locations ?? []).filter(item => item && typeof item === "object");
        for (const loc of locations.length ? locations : [{}]) {
          const line = Number(loc.start?.line || fallback);
          if (Number.isInteger(line) && line > 0) branchLines.add(line);
        }
      }
      if (executed.size || branchLines.size) {
        this.testCoverage[file] ??= {};
        this.testCoverage[file][testFile] = { lines: ranges(executed), branch_lines: ranges(branchLines) };
      }
    }
  }

  finish() {
    // TypeScript declaration files contain no executable code.
    const missing = [...this.sources].filter(file =>
      !/\.d\.(?:ts|mts|cts)$/u.test(file) && !this.files.get(file)?.denominator);
    if (missing.length) throw new Error(`No executable denominator for: ${missing.join(", ")}`);
    const files = {};
    for (const file of this.sources) {
      const row = this.files.get(file);
      if (!row) {
        files[file] = { lines: { total: [], covered: [] }, branches: [] };
        continue;
      }
      if ([...row.covered].some(line => !row.total.has(line)) ||
          [...row.coveredArms].some(id => !row.arms.has(id))) {
        throw new Error(`Per-test coverage differs from the denominator instrumentation: ${file}`);
      }
      const branches = new Map();
      for (const [id, line] of row.arms) {
        if (!branches.has(line)) branches.set(line, { line, total: 0, covered: 0 });
        const branch = branches.get(line);
        branch.total += 1;
        branch.covered += Number(row.coveredArms.has(id));
      }
      files[file] = {
        lines: { total: ranges(row.total), covered: ranges(row.covered) },
        branches: [...branches.values()].sort((a, b) => a.line - b.line),
      };
    }
    return { project: this.project, files, test_coverage: this.testCoverage };
  }
}
