/** Deterministic input and execution checks before model calls. */
import fs from "node:fs";
import path from "node:path";

import { safeRelativePath } from "../support/path_safety.mjs";
import {
  isDiscovery,
  primaryCheckout,
  primaryRevisionKind,
  revisionKinds,
} from "./options.mjs";
import { writeJson } from "../support/json.mjs";
import { validateRevision } from "./session.mjs";

function checkRecord(name, passed, details = {}) {
  return { name, passed: Boolean(passed), ...details };
}

function readableSourceFile(projectRoot, filepath) {
  let rel = String(filepath || "");
  const failure = (error) => ({ passed: false, filepath: rel, error });
  if (!projectRoot) {
    return failure("missing_project_root");
  }
  try {
    rel = safeRelativePath(filepath);
  } catch (error) {
    return failure(error.message);
  }
  const full = path.join(projectRoot, rel);
  const stat = fs.lstatSync(full, { throwIfNoEntry: false });
  if (!stat) {
    return failure("missing_source_file");
  }
  if (stat.isDirectory()) {
    return failure("source_path_is_directory");
  }
  try {
    fs.accessSync(full, fs.constants.R_OK);
  } catch (error) {
    return failure(error.message);
  }
  return { passed: true, filepath: rel };
}

function generatedRootCheck(root) {
  try {
    const rel = safeRelativePath(root).replace(/\/$/u, "");
    return { passed: ![".", "test", "tests"].includes(rel), root: rel };
  } catch (error) {
    return { passed: false, root: String(root || ""), error: error.message };
  }
}

function sourceRootWarnings(projectRoot, roots) {
  const warnings = [];
  for (const root of roots || []) {
    let rel = "";
    try {
      rel = safeRelativePath(root);
    } catch (error) {
      warnings.push({
        kind: "invalid_source_root",
        root: String(root || ""),
        error: error.message,
      });
      continue;
    }
    if (!fs.existsSync(path.join(projectRoot, rel))) {
      warnings.push({ kind: "missing_source_root", root: rel });
    }
  }
  return warnings;
}

export function preflightTargetRun({ manifest, packet }) {
  const checks = [];
  const errors = [];
  const warnings = [];
  const check = (name, passed, details = {}, errorDetails = details) => {
    checks.push(checkRecord(name, passed, details));
    if (!passed) errors.push({ check: name, ...errorDetails });
  };

  const checkout = primaryCheckout(manifest)?.path || "";

  const checkoutExists = Boolean(checkout && fs.existsSync(checkout));
  check(
    `${primaryRevisionKind(manifest.evaluation_mode)}_checkout_exists`,
    checkoutExists,
    { path: checkout },
  );

  const targetFiles = [
    ...new Set(
      (packet?.target_units || [])
        .map((unit) => unit?.filepath)
        .filter(Boolean),
    ),
  ].sort();
  for (const filepath of targetFiles) {
    const result = readableSourceFile(checkout, filepath);
    check("target_source_file_readable", result.passed, result);
  }
  if (targetFiles.length === 0) {
    check(
      "target_source_files_present",
      false,
      {},
      { error: "missing_target_source_files" },
    );
  }

  const routeTargets = packet?.public_target_routes?.targets || [];
  const routedIds = new Set(
    routeTargets
      .filter((item) => (item.entrypoints || []).length > 0)
      .map((item) => item.target_unit_id),
  );
  const missingRoutes = (packet?.target_units || [])
    .map((unit) => unit.unit_id)
    .filter((unitId) => !routedIds.has(unitId));
  const publicRoutesPassed =
    packet?.public_target_routes?.available === true &&
    missingRoutes.length === 0;
  checks.push(
    checkRecord("public_target_routes_available", publicRoutesPassed, {
      advisory: true,
      missing_target_unit_ids: missingRoutes,
    }),
  );
  if (!publicRoutesPassed) {
    warnings.push({
      check: "public_target_routes_available",
      warning: "curation_review_required",
      missing_target_unit_ids: missingRoutes,
    });
  }

  const generatedRoots = packet?.generated_test_roots || [];
  for (const root of generatedRoots) {
    const result = generatedRootCheck(root);
    check("generated_test_root_safe", result.passed, result);
  }
  if (generatedRoots.length === 0) {
    errors.push({
      check: "generated_test_root_safe",
      error: "missing_generated_test_roots",
    });
  }

  const command = packet?.test_command || [];
  const hasCommand = Array.isArray(command) && command.length > 0;
  check(
    "test_command_present",
    hasCommand,
    { command },
    { error: "missing_test_command" },
  );

  warnings.push(...sourceRootWarnings(checkout, manifest?.source_roots || []));

  return {
    schema: isDiscovery(manifest.evaluation_mode)
      ? "test-augment-ts-bug-discovery-preflight-v1"
      : "test-augment-ts-br-preflight-v1",
    passed: errors.length === 0,
    checks,
    errors,
    warnings,
  };
}

export function validatePreflightAsset(runtime, preflightDir, label, asset) {
  const outcomes = Object.fromEntries(
    revisionKinds(runtime.options.evaluationMode).map((revisionKind) => [
      revisionKind,
      validateRevision({
        runtime,
        revisionKind,
        asset,
        assetDir: path.join(preflightDir, label, revisionKind),
      }).summary,
    ]),
  );
  return {
    attempted: true,
    passed: Object.values(outcomes).every((summary) => summary.passed),
    asset: { test_file: asset.test_file },
    ...outcomes,
  };
}

export function runRevisionValidationPreflight(runtime, runDir) {
  const targetFiles = [
    ...new Set(
      (runtime.packet.target_units || [])
        .map((unit) => unit.filepath)
        .filter(Boolean),
    ),
  ];
  const contracts = targetFiles.map((filepath) =>
    (runtime.packet.module_contracts || []).find(
      (item) => item?.filepath === filepath && item?.suggested_imports?.length,
    ),
  );
  const specifiers = contracts.map(
    (contract) => contract?.suggested_imports?.[0]?.specifier || "",
  );
  const root = String(runtime.packet.generated_test_roots?.[0] || "").replace(
    /\/$/u,
    "",
  );
  const outPath = path.join(runDir, "preflight-validation.json");
  if (!root) {
    const record = {
      passed: false,
      path: outPath,
      error: "missing_generated_root",
      target_files: targetFiles,
    };
    writeJson(outPath, record);
    return record;
  }
  const preflightDir = path.join(runDir, "preflight-validation");
  const importsAvailable = specifiers.length > 0 && specifiers.every(Boolean);
  let targetImport = {
    attempted: false,
    passed: null,
    reason: "missing_target_import",
    target_files: targetFiles,
  };
  if (importsAvailable) {
    const importCode = specifiers
      .map(
        (specifier, index) =>
          `import * as targetModule${index} from ${JSON.stringify(specifier)};`,
      )
      .join("\n");
    const moduleNames = specifiers
      .map((_, index) => `targetModule${index}`)
      .join(", ");
    const asset = {
      asset_id: "preflight-target-import",
      test_file: `${root}/test_benchmarkbr_preflight_target_import.test.ts`,
      append_code: `import { expect, it } from "vitest";\n${importCode}\n\nit("collects the generated test and imports every target module", () => {\n  expect([${moduleNames}]).toHaveLength(${specifiers.length});\n});\n`,
    };
    targetImport = {
      ...validatePreflightAsset(runtime, preflightDir, "target-import", asset),
      asset: { test_file: asset.test_file, target_imports: specifiers },
    };
  }

  let runner;
  if (targetImport.passed) {
    runner = {
      attempted: false,
      passed: true,
      reason: "confirmed_by_target_import",
    };
  } else {
    const asset = {
      asset_id: "preflight-runner",
      test_file: `${root}/test_benchmarkbr_preflight_runner.test.ts`,
      append_code:
        'import { expect, it } from "vitest";\n\nit("runs generated test infrastructure", () => {\n  expect(true).toBe(true);\n});\n',
    };
    runner = validatePreflightAsset(runtime, preflightDir, "runner", asset);
  }

  const record = {
    passed: runner.passed,
    path: outPath,
    runner,
    target_import: targetImport,
  };
  writeJson(outPath, record);
  return record;
}
