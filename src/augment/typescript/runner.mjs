#!/usr/bin/env node
/** Adapt command-line arguments for one prepared TypeScript augmentation run. */

import path from "node:path";
import { fileURLToPath } from "node:url";

import { parseAugmentArgs, runAugmentCli } from "./run_cli.mjs";
import { readJson } from "./json.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const artifactRoot = path.resolve(here, "../../..");

function vitestLauncher(project) {
  return (env) => {
    const key = `${project.toUpperCase().replace(/-/gu, "_")}_VITEST_LAUNCHER`;
    const raw = String(env[key] || env.VITEST_LAUNCHER || "pnpm").trim();
    if (raw === "pnpm") return ["pnpm", "exec", "vitest"];
    if (raw === "npx") return ["npx", "vitest"];
    return raw.split(/\s+/u).filter(Boolean);
  };
}

const values = parseAugmentArgs("python3 run.py augment");
if (values) {
  const { createPackageVitestAdapter } = await import("./package_vitest_adapter.mjs");
  const { project } = values;
  const config = readJson(path.join(artifactRoot, "resources/projects.json"))[project];
  if (!config || config.language !== "typescript") {
    throw new Error(`unknown TypeScript project: ${project}`);
  }
  const settings = config.augment ?? {};
  const testPackages = settings.test_packages ?? [{ name: "root", cwd: "." }];
  const coverageFilterArgs =
    settings.coverage_include || settings.coverage_exclude
      ? [
          ...(settings.coverage_include ?? []).flatMap((glob) => [
            "--coverage.include",
            glob,
          ]),
          ...(settings.coverage_exclude ?? []).flatMap((glob) => [
            "--coverage.exclude",
            glob,
          ]),
        ]
      : undefined;
  const adapter = createPackageVitestAdapter({
    packages: testPackages,
    launcher: vitestLauncher(project),
    coverageFilterArgs,
    teardownTimeoutMs: settings.teardown_timeout_ms,
  });
  await runAugmentCli({
    values,
    defaultOutRoot: path.join(artifactRoot, "outputs", project, "augment"),
    measureTestFileCoverage: adapter.measureTestFileCoverage,
    validateGeneratedTest: adapter.validateGeneratedTest,
    testPackages,
  });
}
