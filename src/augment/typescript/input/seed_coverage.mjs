import { safeRelativePath } from "../paths.mjs";

const SHA256 = /^[0-9a-f]{64}$/u;

function coveredLines(values, label) {
  if (
    !Array.isArray(values) ||
    values.some((value) => !Number.isInteger(value) || value <= 0)
  ) {
    throw new Error(`Seed coverage contains invalid lines: ${label}`);
  }
  const unique = [...new Set(values)].sort((left, right) => left - right);
  if (unique.length !== values.length) {
    throw new Error(`Seed coverage contains duplicate lines: ${label}`);
  }
  return unique;
}

/** Load portable per-seed, per-target line observations from a frozen suite. */
export function parseSeedCoverage(raw, project) {
  if (raw === null) return null;
  if (
    raw.project !== project ||
    !raw.observations ||
    typeof raw.observations !== "object" ||
    Array.isArray(raw.observations)
  ) {
    throw new Error(
      `Seed coverage is incompatible with project ${project}`,
    );
  }

  const observations = new Map();
  for (const [testFile, test] of Object.entries(raw.observations)) {
    if (
      !safeRelativePath(testFile) ||
      !SHA256.test(String(test?.sha256 ?? "")) ||
      !test.targets ||
      typeof test.targets !== "object" ||
      Array.isArray(test.targets)
    ) {
      throw new Error(
        `Seed coverage contains an invalid test: ${testFile}`,
      );
    }
    const targets = new Map();
    for (const [filepath, target] of Object.entries(test.targets)) {
      if (
        !safeRelativePath(filepath) ||
        !SHA256.test(String(target?.sha256 ?? ""))
      ) {
        throw new Error(
          `Seed coverage contains an invalid target: ${filepath}`,
        );
      }
      targets.set(filepath, {
        sha256: target.sha256,
        covered_lines: coveredLines(
          target.covered_lines,
          `${testFile} -> ${filepath}`,
        ),
      });
    }
    observations.set(testFile, { sha256: test.sha256, targets });
  }
  return { observations };
}
