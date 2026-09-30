import path from "node:path";

import { typescriptBoundaries } from "../source_rules.mjs";
import { analyzeFactProject } from "./analysis_fact.mjs";
import {
  buildCompactFactLocationPayload,
  writeJson,
} from "./payload.mjs";
import { normalizeControlDependenceMode } from "./models.mjs";
import {
  loadFileList,
  loadTypeScript,
} from "./source_locator.mjs";

const DEFAULT_MAX_ITERATIONS = 80;

/** Analyze the supplied source-file list and return source/data/control regions. */
export function analyzeProject(args) {
  const root = path.resolve(args.root);
  const sourceBase = path.resolve(args.sourceBase);
  const typescriptRoot = path.resolve(args.typescriptRoot || root);
  const ts = loadTypeScript(typescriptRoot);
  const { files } = loadFileList({ root, sourceBase });
  return analyzeFactProject({
    ts,
    root,
    files,
    project: args.project || "typescript",
    sourceRules: args.boundaries || typescriptBoundaries({ measurementScope: "source" }),
    options: {
      maxIterations: args.maxIterations || DEFAULT_MAX_ITERATIONS,
      controlDependenceMode: normalizeControlDependenceMode(args.controlDependenceMode),
    },
  });
}

/** Write detailed and optional compact artifacts for one analysis run. */
export function writeFlowOutputs(args, payload) {
  writeJson(args.out, payload);
  if (args.compactOut) {
    const mode = payload.options?.control_dependence_mode || args.controlDependenceMode;
    writeJson(args.compactOut, buildCompactFactLocationPayload(payload, {
      includeControlDependence: mode !== "block_only",
    }));
  }
}
