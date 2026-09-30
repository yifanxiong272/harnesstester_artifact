import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

function coordinate(value) {
  return Number.isFinite(Number(value)) ? Number(value) : null;
}

function location(value = {}) {
  return {
    start_line: coordinate(value.start?.line),
    start_column: coordinate(value.start?.column),
    end_line: coordinate(value.end?.line),
    end_column: coordinate(value.end?.column),
  };
}

function locationKey(value) {
  return [
    value.start_line,
    value.start_column,
    value.end_line,
    value.end_column,
  ]
    .map((item) => item ?? "")
    .join(":");
}

function branchStructure(branch) {
  const parent = location(branch.loc);
  const arms = Array.isArray(branch.locations)
    ? branch.locations.map(location)
    : [];
  return {
    type: String(branch.type ?? "branch"),
    parent,
    arms,
    key: [
      String(branch.type ?? "branch"),
      locationKey(parent),
      ...arms.map(locationKey),
    ].join("|"),
  };
}

function branchEntries(fileCoverage) {
  const branchMap = fileCoverage.branchMap ?? {};
  return Object.entries(fileCoverage.b ?? {})
    .map(([runtimeId, counts]) => {
      const branch = branchMap[runtimeId] ?? {};
      return {
        runtimeId,
        counts: Array.isArray(counts) ? counts : [counts],
        structure: branchStructure(branch),
      };
    })
    .sort((left, right) => {
      const structureOrder = left.structure.key.localeCompare(
        right.structure.key,
      );
      return (
        structureOrder ||
        String(left.runtimeId).localeCompare(
          String(right.runtimeId),
          undefined,
          { numeric: true },
        )
      );
    });
}

function positive(value) {
  if (Array.isArray(value)) {
    return value.some(positive);
  }
  return Number(value ?? 0) > 0;
}

function armLine(parent, arm) {
  return arm.start_line ?? parent.start_line;
}

export function normalizeProjectPath(rawPath, projectRoot) {
  if (!rawPath) {
    return null;
  }
  const rootPath = path.resolve(projectRoot);
  const absolutePath = path.resolve(
    path.isAbsolute(rawPath) ? rawPath : path.join(rootPath, rawPath),
  );
  const root = fs.realpathSync.native(rootPath);
  const absolute = fs.existsSync(absolutePath)
    ? fs.realpathSync.native(absolutePath)
    : absolutePath;
  const relative = path.relative(root, absolute);
  if (!relative || relative === ".." || relative.startsWith(`..${path.sep}`)) {
    return null;
  }
  return relative.split(path.sep).join("/");
}

/**
 * Return source-stable branch arms from one Istanbul/V8 file coverage object.
 *
 * Numeric branch ids are instrumentation-local, so the identity uses source
 * locations, branch type, arm index, and a deterministic occurrence index for
 * structurally identical branch records. The same unchanged source therefore
 * produces the same slot id in baseline and generated-test coverage runs.
 */
export function branchArms(filepath, fileCoverage) {
  const occurrences = new Map();
  const arms = [];
  for (const entry of branchEntries(fileCoverage)) {
    const occurrence = occurrences.get(entry.structure.key) ?? 0;
    occurrences.set(entry.structure.key, occurrence + 1);
    const count = Math.max(entry.counts.length, entry.structure.arms.length);
    for (let index = 0; index < count; index += 1) {
      const arm = entry.structure.arms[index] ?? location();
      const signature = [
        filepath,
        entry.structure.type,
        locationKey(entry.structure.parent),
        occurrence,
        index,
        locationKey(arm),
      ].join("|");
      arms.push({
        slot_id: `br:${crypto.createHash("sha1").update(signature).digest("hex")}`,
        signature,
        line: armLine(entry.structure.parent, arm),
        branch_type: entry.structure.type,
        branch_location: entry.structure.parent,
        arm_location: arm,
        arm_index: index,
        occurrence,
        covered: positive(entry.counts[index] ?? 0),
      });
    }
  }
  return arms;
}
