#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

import { analyzeProject, writeFlowOutputs } from "./flow/index.mjs";
import { typescriptBoundaries } from "./source_rules.mjs";

/** Run native analysis with the options parsed by the public artifact CLI. */
export function run(args) {
  const flowArgs = {
    root: path.resolve(args.root),
    typescriptRoot: args.typescriptRoot
      ? path.resolve(args.typescriptRoot)
      : undefined,
    sourceBase: path.resolve(args.sourceBase),
    out: path.resolve(args.out),
    compactOut: args.compactOut ? path.resolve(args.compactOut) : undefined,
    maxIterations: args.maxIterations,
    controlDependenceMode: args.controlDependenceMode,
    project: "typescript",
    boundaries: typescriptBoundaries({ measurementScope: "source" }),
  };
  const payload = analyzeProject(flowArgs);
  writeFlowOutputs(flowArgs, payload);
  return payload;
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  run(JSON.parse(fs.readFileSync(0, "utf8")));
}
