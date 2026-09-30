import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

import { ensureDir } from "./json.mjs";
import { validateGeneratedTestPath } from "./prompt/proposal.mjs";
import {
  TOP_LEVEL_SUITE_ID,
  targetBinding,
  targetLoader,
  testSuites,
  vitestNamespace,
  withoutEmptyTestSuites,
  withoutSeedTestRegistrations,
} from "./test_seed.mjs";
import { parseTypeScript } from "./typescript_ast.mjs";

const IGNORED_NAMES = new Set([
  ".git",
  ".stryker-tmp",
  ".tmp",
  ".vitest",
  "coverage",
  "node_modules",
  "dist",
  "dist-runtime",
]);

const SYMLINK_NAMES = ["node_modules", "dist", "dist-runtime"];
const COPY_MODE = fs.constants.COPYFILE_FICLONE;

function copyFilter(src) {
  const name = path.basename(src);
  if (IGNORED_NAMES.has(name)) {
    return false;
  }
  return !name.endsWith(".log");
}

/** Resolve existing symlinks while preserving a not-yet-created path suffix. */
export function resolveOutputRoot(outRoot) {
  let parent = path.resolve(outRoot);
  const suffix = [];
  while (!fs.existsSync(parent)) {
    suffix.unshift(path.basename(parent));
    parent = path.dirname(parent);
  }
  return path.join(fs.realpathSync(parent), ...suffix);
}

export function createCurrentWorkspace({ frozenRoot, runDir }) {
  const currentRoot = path.join(runDir, "workspaces", "current");
  if (!fs.existsSync(currentRoot)) {
    ensureDir(path.dirname(currentRoot));
    fs.cpSync(frozenRoot, currentRoot, {
      recursive: true,
      dereference: false,
      filter: copyFilter,
      // Generated tests must run in an isolated project tree, but large TS
      // projects often contain binary assets. Copy-on-write keeps the same
      // filesystem semantics while avoiding a full physical copy when the
      // local filesystem supports it.
      mode: COPY_MODE,
    });
    for (const name of SYMLINK_NAMES) {
      const source = path.join(frozenRoot, name);
      const target = path.join(currentRoot, name);
      if (fs.existsSync(source) && !fs.existsSync(target)) {
        fs.symlinkSync(source, target, "dir");
      }
    }
  }
  return currentRoot;
}

export function createStagingWorkspace({ currentRoot, runDir, sampleId }) {
  const stagingRoot = path.join(runDir, "workspaces", "staging", sampleId);
  fs.rmSync(stagingRoot, { recursive: true, force: true });
  ensureDir(path.dirname(stagingRoot));
  fs.cpSync(currentRoot, stagingRoot, {
    recursive: true,
    dereference: false,
    filter: copyFilter,
    mode: COPY_MODE,
  });
  for (const name of SYMLINK_NAMES) {
    const source = path.join(currentRoot, name);
    const target = path.join(stagingRoot, name);
    if (fs.existsSync(source) && !fs.existsSync(target)) {
      fs.symlinkSync(fs.realpathSync(source), target, "dir");
    }
  }
  return stagingRoot;
}

function appendBlock(existing, code) {
  let separator = "";
  if (existing) {
    separator = existing.endsWith("\n") ? "\n" : "\n\n";
  }
  return `${existing}${separator}${code.trim()}\n`;
}

function referencesIdentifier(typescript, code, identifier) {
  const sourceFile = parseTypeScript(
    typescript,
    "generated.test.ts",
    String(code ?? ""),
  );
  let found = false;
  function visit(node) {
    if (found) return;
    if (typescript.isIdentifier(node) && node.text === identifier) {
      found = true;
      return;
    }
    typescript.forEachChild(node, visit);
  }
  visit(sourceFile);
  return found;
}

function indentedBlock(code, indent) {
  const lines = String(code ?? "")
    .trim()
    .split("\n");
  const margins = lines
    .filter((line) => line.trim())
    .map((line) => line.match(/^\s*/u)[0].length);
  const margin = margins.length > 0 ? Math.min(...margins) : 0;
  return lines
    .map((line) => (line.trim() ? `${indent}${line.slice(margin)}` : ""))
    .join("\n");
}

function insertTest(source, suiteId, code, typescript, filepath) {
  const suites = testSuites(typescript, filepath, source);
  if (suites.length === 0) {
    if (suiteId !== TOP_LEVEL_SUITE_ID) {
      throw new Error(`seed test has no suite: ${suiteId}`);
    }
    return appendBlock(source, code);
  }
  const suite = suites.find((item) => item.suite_id === suiteId);
  if (!suite) {
    throw new Error(`proposal selected an unknown seed suite: ${suiteId}`);
  }

  const closingBrace = suite.insertion_offset;
  const lineStart = source.lastIndexOf("\n", closingBrace - 1) + 1;
  const beforeBrace = source.slice(lineStart, closingBrace);
  const closingIndent = beforeBrace.match(/^\s*/u)[0];
  const test = indentedBlock(code, `${closingIndent}  `);
  if (beforeBrace.trim()) {
    return `${source.slice(0, closingBrace)}\n${test}\n${closingIndent}${source.slice(closingBrace)}`;
  }
  return `${source.slice(0, lineStart)}${test}\n${source.slice(lineStart)}`;
}

function sha256(file) {
  return crypto
    .createHash("sha256")
    .update(fs.readFileSync(file))
    .digest("hex");
}

function acceptedSampleDirectory(root, sampleId) {
  if (
    typeof sampleId !== "string" ||
    !sampleId ||
    sampleId === "." ||
    sampleId === ".." ||
    /[\\/\0]/u.test(sampleId)
  ) {
    throw new Error(`invalid accepted sample id: ${sampleId}`);
  }
  return path.join(root, sampleId);
}

export function materializeProposal({
  projectRoot,
  proposal,
  seedTestFile,
  seedTestSha256,
  targetModuleImport,
  typescript,
}) {
  validateGeneratedTestPath(proposal.test_file, seedTestFile);
  if (!String(targetModuleImport ?? "").startsWith(".")) {
    throw new Error(
      "target module import must be relative to the generated test",
    );
  }
  const target = path.join(projectRoot, proposal.test_file);
  const seed = path.join(projectRoot, seedTestFile);
  if (!fs.existsSync(seed)) {
    throw new Error(`seed test is missing: ${seedTestFile}`);
  }
  if (sha256(seed) !== seedTestSha256) {
    throw new Error(
      `seed test changed after target selection: ${seedTestFile}`,
    );
  }
  if (fs.existsSync(target)) {
    throw new Error(`generated test already exists: ${proposal.test_file}`);
  }
  if (!typescript) {
    throw new Error("TypeScript compiler is required to materialize tests");
  }
  ensureDir(path.dirname(target));
  const seedSource = fs.readFileSync(seed, "utf8");
  const harness = withoutSeedTestRegistrations(
    typescript,
    seedTestFile,
    seedSource,
  );
  const namespace = vitestNamespace({
    test_file: seedTestFile,
    sha256: seedTestSha256,
  });
  const loader = targetLoader(
    { test_file: seedTestFile, sha256: seedTestSha256 },
    targetModuleImport,
  );
  const binding = targetBinding(
    { test_file: seedTestFile, sha256: seedTestSha256 },
    targetModuleImport,
  );
  const vitestImport = `import * as ${namespace} from "vitest";`;
  const targetImport = JSON.stringify(targetModuleImport);
  const targetBindingImport = `import * as ${binding} from ${targetImport};`;
  const targetLoaderCode = [
    `const ${loader} = async () => {`,
    `  ${namespace}.vi.doUnmock(${targetImport});`,
    `  ${namespace}.vi.resetModules();`,
    `  return import(${targetImport});`,
    "};",
  ].join("\n");
  const extended = insertTest(
    harness.source,
    proposal.suite_id,
    proposal.append_code,
    typescript,
    seedTestFile,
  );
  const withVitest = withoutEmptyTestSuites(
    typescript,
    seedTestFile,
    appendBlock(extended, vitestImport),
  );
  const withTargetBinding = referencesIdentifier(
    typescript,
    proposal.append_code,
    binding,
  )
    ? appendBlock(withVitest, targetBindingImport)
    : withVitest;
  fs.writeFileSync(target, appendBlock(withTargetBinding, targetLoaderCode));
  return {
    project_root: projectRoot,
    test_file: proposal.test_file,
    seed_test_file: seedTestFile,
    vitest_namespace: namespace,
    target_binding: binding,
    target_loader: loader,
    suite_id: proposal.suite_id,
    removed_seed_test_count: harness.removed_count,
    removed_seed_suite_call_count: harness.removed_suite_call_count,
    created_new_test_file: true,
    materialized_path: target,
  };
}

export function persistAcceptedGeneratedFileFromPath({
  runDir,
  currentRoot,
  sourceFile,
  sampleId,
  testFile,
}) {
  const currentTarget = path.join(currentRoot, testFile);
  const acceptedTarget = path.join(
    acceptedSampleDirectory(path.join(runDir, "accepted", "files"), sampleId),
    testFile,
  );
  ensureDir(path.dirname(currentTarget));
  ensureDir(path.dirname(acceptedTarget));
  fs.copyFileSync(sourceFile, currentTarget, COPY_MODE);
  fs.copyFileSync(sourceFile, acceptedTarget, COPY_MODE);
  return {
    accepted_file_snapshot: acceptedTarget,
  };
}

export function cleanupStaging(stagingRoot) {
  fs.rmSync(stagingRoot, { recursive: true, force: true });
}
