import path from "node:path";

import { readJson } from "../json.mjs";
import { prepareInputs } from "./prepare.mjs";

function resolveInputPath(baseInputFile, value) {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`Input path must be a non-empty string: ${baseInputFile}`);
  }
  return path.resolve(path.dirname(baseInputFile), value);
}

/** Load base_input.json and prepare the regions/coverage pair for augmentation. */
export function loadInputs(baseInputFile) {
  const raw = readJson(baseInputFile);
  if (typeof raw.project !== "string" || !raw.project) {
    throw new Error(`Base input must declare a project: ${baseInputFile}`);
  }
  const projectRoot = resolveInputPath(baseInputFile, raw.project_root);
  const regions = readJson(resolveInputPath(baseInputFile, raw.ldh?.regions_json));
  const coverage = readJson(resolveInputPath(baseInputFile, raw.general_cov?.coverage_json));
  return {
    baseInput: { ...raw, project_root: projectRoot },
    ...prepareInputs(regions, coverage, raw.project),
  };
}
