import crypto from "node:crypto";
import fs from "node:fs";

import { projectSourceFile } from "../prompt/context.mjs";
import { selectExistingTest } from "../test_seed.mjs";

function hash(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function targetId(filepath) {
  const digest = crypto.createHash("sha1").update(filepath).digest("hex");
  return `source-file:${digest.slice(0, 16)}`;
}

function sourceFileTarget({ filepath, rank, source, seedTest }) {
  const id = targetId(filepath);
  const endLine = Math.max(1, source.split(/\r?\n/u).length);
  return {
    objective_id: id,
    unit_id: id,
    filepath,
    start_line: 1,
    end_line: endLine,
    rank,
    seed_test: seedTest,
  };
}

/**
 * Build the immutable source-file coverage queue.
 *
 * `fileRanking` is the LDH-bearing file set ordered once by the shared
 * round-zero ordinary-coverage comparator. LDH locations are not copied into
 * targets or model packets.
 */
export function buildCoverageTargetManifest({
  projectRoot,
  generalTestScores,
  fileRanking,
  testPackages,
}) {
  const allowlist = fileRanking.map((target) => String(target.filepath ?? ""));
  if (
    allowlist.some((filepath) => !filepath) ||
    new Set(allowlist).size !== allowlist.length
  ) {
    throw new Error(
      "Coverage file ranking must contain unique non-empty filepaths",
    );
  }

  const unpairedFiles = [];
  const rankingByFile = new Map(
    fileRanking.map((target) => [String(target.filepath), target]),
  );
  const targets = [];
  for (const filepath of allowlist) {
    const sourceFile = projectSourceFile(projectRoot, filepath);
    if (sourceFile.status !== "found") {
      throw new Error(`Coverage target source is unavailable: ${filepath}`);
    }
    const source = fs.readFileSync(sourceFile.file, "utf8");
    const selected = selectExistingTest(
      testPackages,
      filepath,
      generalTestScores?.[filepath],
    );
    if (!selected) {
      unpairedFiles.push(filepath);
      continue;
    }
    const seedFile = projectSourceFile(projectRoot, selected.test_file);
    if (seedFile.status !== "found") {
      throw new Error(
        `Selected existing test is unavailable: ${selected.test_file}`,
      );
    }
    const seedTest = {
      ...selected,
      sha256: hash(fs.readFileSync(seedFile.file)),
    };
    targets.push(
      sourceFileTarget({
        filepath,
        rank: targets.length + 1,
        source,
        seedTest,
      }),
    );
  }
  const pairedRanking = targets.map((target) => ({
    ...structuredClone(rankingByFile.get(target.filepath)),
    rank: target.rank,
    seed_test: structuredClone(target.seed_test),
  }));
  return { file_ranking: pairedRanking, unpaired_files: unpairedFiles, targets };
}
