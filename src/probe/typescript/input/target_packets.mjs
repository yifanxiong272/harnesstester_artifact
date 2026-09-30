import fs from "node:fs";
import path from "node:path";

import { moduleContracts } from "./module_contracts.mjs";
import { probeConstraints } from "./constraints.mjs";
import { publicTargetRoutes } from "./public_routes.mjs";
import { safeRelativePath } from "../support/path_safety.mjs";
import { walkFiles } from "../support/storage.mjs";
import { loadTargetUnits, sourceFileIndex } from "./target_units.mjs";
import {
  loadTypeScript,
  parseSource,
  walkAst,
  compactStatement,
  stringLiteralText,
  moduleReference,
  stripSourceExtension,
  SOURCE_EXTENSIONS,
} from "../support/typescript.mjs";
import {
  TARGET_PROBING_TRACK,
  normalizeTargetStrategy,
} from "../run/options.mjs";

const TEST_SUFFIXES = [".test", ".spec"];

function candidateTestFiles(projectRoot) {
  const files = ["test", "tests", "src", "extensions", "packages"].flatMap(
    (root) =>
      [
        ...walkFiles(path.join(projectRoot, root), {
          exclude: ["node_modules", "dist", "coverage", ".git"],
          sorted: true,
        }),
      ].filter((file) => isTestSourceFile(path.basename(file))),
  );
  return [...new Set(files)].sort();
}

export function existingTestContexts(
  projectRoot,
  units,
  { maxFiles = 2, maxChars = 8000 } = {},
) {
  const candidates = [];
  for (const file of candidateTestFiles(projectRoot)) {
    const rel = path.relative(projectRoot, file).replace(/\\/gu, "/");
    const match = highConfidenceTestMatch(projectRoot, file, rel, units);
    if (!match) {
      continue;
    }
    candidates.push([rel, match]);
  }
  return candidates
    .sort(
      ([leftPath, left], [rightPath, right]) =>
        left.rank - right.rank ||
        leftPath.length - rightPath.length ||
        leftPath.localeCompare(rightPath),
    )
    .slice(0, maxFiles)
    .map(([rel, match]) => {
      const text = fs.readFileSync(path.join(projectRoot, rel), "utf8");
      const excerpt = relevantTestExcerpt(
        projectRoot,
        rel,
        text,
        units,
        maxChars,
      );
      return {
        path: rel,
        reason: match.reason,
        content_excerpt: excerpt,
        selection_type: match.selection_type,
        confidence: "high",
        truncated: excerpt.length < text.length,
        target_unit_ids: match.target_unit_ids,
        target_filepaths: match.target_filepaths,
      };
    });
}

function highConfidenceTestMatch(projectRoot, testFile, relpath, units) {
  const imported = importMatch(projectRoot, testFile, units);
  if (imported.specifier) {
    return matchRecord({
      rank: 0,
      selection_type: "imports_target_module",
      reason: `test file statically imports target module \`${imported.specifier}\``,
      units: imported.units,
    });
  }
  const stemUnits = sameStemUnits(relpath, units);
  if (stemUnits.length > 0) {
    const stem = sourceStem(stemUnits[0].filepath);
    return matchRecord({
      rank: 1,
      selection_type: "same_directory_stem_test_file",
      reason: `same-directory test filename for target module stem \`${stem}\``,
      units: stemUnits,
    });
  }
  return null;
}

function matchRecord({ rank, selection_type, reason, units }) {
  return {
    rank,
    selection_type,
    reason,
    target_unit_ids: [...new Set(units.map((unit) => unit.unit_id))].sort(),
    target_filepaths: [...new Set(units.map((unit) => unit.filepath))].sort(),
  };
}

function sameStemUnits(relpath, units) {
  const basename = sourceStem(relpath);
  const lowered = basename.toLowerCase();
  for (const stem of targetStems(units)) {
    const item = stem.toLowerCase();
    const matchingUnits = units.filter(
      (unit) =>
        sourceStem(unit.filepath) === stem &&
        path.posix.dirname(unit.filepath) === path.posix.dirname(relpath),
    );
    if (matchingUnits.length === 0) {
      continue;
    }
    if (
      lowered === item ||
      lowered === `test-${item}` ||
      lowered === `test_${item}`
    ) {
      return matchingUnits;
    }
    if (
      (lowered.startsWith(`${item}.`) || lowered.startsWith(`${item}_`)) &&
      isTestSourceFile(relpath)
    ) {
      return matchingUnits;
    }
  }
  return [];
}

function relevantTestExcerpt(projectRoot, relpath, text, units, maxChars) {
  const ts = loadTypeScript(projectRoot);
  if (!ts || text.length <= maxChars) {
    return text.slice(0, maxChars);
  }
  const sourceFile = parseSource(ts, relpath, text);
  const targetNames = new Set(
    units
      .map((unit) =>
        String(unit.qualname || "")
          .split(".")
          .at(-1),
      )
      .filter(Boolean),
  );
  const imports = sourceFile.statements
    .filter((statement) => ts.isImportDeclaration(statement))
    .map((statement) => statement.getText(sourceFile));
  const tests = [];
  walkAst(ts, sourceFile, (node) => {
    if (ts.isCallExpression(node)) {
      const callee = ts.isIdentifier(node.expression)
        ? node.expression.text
        : "";
      if (["it", "test"].includes(callee)) {
        const block = node.getText(sourceFile);
        if ([...targetNames].some((name) => block.includes(name))) {
          tests.push(block);
          return false;
        }
      }
    }
  });
  const selected = [...imports, ...tests].join("\n\n");
  if (tests.length > 0) {
    return selected.slice(0, maxChars);
  }
  const needle = [...targetNames].find((name) => text.includes(name));
  if (!needle) {
    return text.slice(0, maxChars);
  }
  const index = text.indexOf(needle);
  const start = Math.max(0, index - Math.floor(maxChars / 3));
  return text.slice(start, start + maxChars);
}

function targetStems(units) {
  return [
    ...new Set(units.map((unit) => sourceStem(unit.filepath)).filter(Boolean)),
  ];
}

function importMatch(projectRoot, testFile, units) {
  const imports = new Set(
    moduleImportRecords(projectRoot, testFile).map((item) => item.specifier),
  );
  if (imports.size === 0) {
    return { specifier: "", units: [] };
  }
  const specifiers = targetImportSpecifiers(projectRoot, testFile, units);
  for (const { specifier, unit } of specifiers) {
    if (imports.has(specifier)) {
      return { specifier, units: [unit] };
    }
  }
  return { specifier: "", units: [] };
}

function targetImportSpecifiers(projectRoot, testFile, units) {
  const result = new Map();
  const testDir = path.posix.dirname(
    path.relative(projectRoot, testFile).replace(/\\/gu, "/"),
  );
  for (const unit of units) {
    const target = stripSourceExtension(unit.filepath);
    let rel = path.posix.relative(testDir, target);
    if (!rel.startsWith(".")) {
      rel = `./${rel}`;
    }
    for (const specifier of [rel, `${rel}.js`, `${rel}.ts`, `${rel}.tsx`]) {
      const key = `${specifier}\0${unit.unit_id}`;
      if (!result.has(key)) {
        result.set(key, { specifier, unit });
      }
    }
  }
  return [...result.values()].sort(
    (a, b) =>
      b.specifier.length - a.specifier.length ||
      a.specifier.localeCompare(b.specifier),
  );
}

function isTestSourceFile(filepath) {
  const stem = stripSourceExtension(path.posix.basename(filepath));
  return (
    SOURCE_EXTENSIONS.some((extension) => filepath.endsWith(extension)) &&
    TEST_SUFFIXES.some((suffix) => stem.endsWith(suffix))
  );
}

function sourceStem(filepath) {
  let stem = stripSourceExtension(path.posix.basename(filepath));
  for (const suffix of TEST_SUFFIXES) {
    if (stem.endsWith(suffix)) {
      stem = stem.slice(0, -suffix.length);
      break;
    }
  }
  return stem;
}

function moduleImports(projectRoot, files, { limit = 80 } = {}) {
  const imports = new Map();
  for (const filepath of files) {
    const rel = safeRelativePath(filepath);
    const full = path.join(projectRoot, rel);
    if (!fs.existsSync(full)) {
      continue;
    }
    for (const item of moduleImportRecords(projectRoot, full)) {
      const key = `${rel}\0${item.specifier}`;
      if (imports.has(key)) {
        continue;
      }
      imports.set(key, {
        filepath: rel,
        specifier: item.specifier,
        statement: item.statement,
      });
      if (imports.size >= limit) {
        return [...imports.values()];
      }
    }
  }
  return [...imports.values()];
}

function moduleImportRecords(projectRoot, file) {
  const ts = loadTypeScript(projectRoot);
  if (!ts) {
    return [];
  }
  const rel = path.relative(projectRoot, file).replace(/\\/gu, "/");
  const text = fs.readFileSync(file, "utf8");
  const sourceFile = parseSource(ts, rel, text);
  const records = [];
  walkAst(ts, sourceFile, (node) => {
    let specifier = moduleReference(ts, node);
    if (
      specifier === null &&
      ts.isImportEqualsDeclaration(node) &&
      ts.isExternalModuleReference(node.moduleReference)
    ) {
      specifier = stringLiteralText(ts, node.moduleReference.expression);
    }
    if (specifier) {
      records.push({
        specifier,
        statement: compactStatement(node, sourceFile, 240),
      });
    }
  });
  return records;
}

export function buildTargetPacket({
  project,
  strategy,
  projectRoot,
  targetUnits,
  testCommand,
  generatedTestRoots = ["test/generated/benchmarkbr"],
}) {
  const normalizedStrategy = normalizeTargetStrategy(strategy);
  const units = loadTargetUnits(projectRoot, targetUnits);
  if (units.length === 0) {
    throw new Error("case has no target units");
  }
  const files = [...new Set(units.map((unit) => unit.filepath))].sort();
  const publicRoutes = publicTargetRoutes(projectRoot, units);
  const packet = {
    project,
    strategy: normalizedStrategy,
    track: TARGET_PROBING_TRACK,
    target_units: units,
    source_file_index: sourceFileIndex(projectRoot, files),
    existing_tests: existingTestContexts(projectRoot, units),
    module_imports: moduleImports(projectRoot, files),
    module_contracts: moduleContracts(projectRoot, files, {
      generatedTestRoots,
    }),
    public_target_routes: publicRoutes,
    generated_test_roots: generatedTestRoots,
    constraints: probeConstraints(),
    test_command: testCommand,
  };
  return packet;
}
