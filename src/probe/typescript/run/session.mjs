/** Model calls and isolated candidate validation on prepared revisions. */
import fs from "node:fs";
import path from "node:path";
import { chatCompletion } from "./client.mjs";
import { limitTimeout } from "./deadline.mjs";
import { ensureDir, writeJson } from "../support/json.mjs";
import { safeRelativePath } from "../support/path_safety.mjs";
import { validateVitest } from "../runtime/validate.mjs";
import { compactText } from "./reporting.mjs";
import { primaryRevisionKind } from "./options.mjs";

const IGNORED = new Set([
  ".git",
  "node_modules",
  ".stryker-tmp",
  ".tmp",
  ".vitest",
  "coverage",
  "dist",
  "dist-runtime",
  "__openclaw_vitest__",
]);

function copyCheckout(source, target) {
  fs.cpSync(source, target, {
    recursive: true,
    dereference: false,
    filter: (file) =>
      !IGNORED.has(path.basename(file)) && !file.endsWith(".log"),
  });
  const linkDependencies = (directory, relative = "") => {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const from = path.join(directory, entry.name);
      const rel = path.join(relative, entry.name);
      if (entry.name === "node_modules") {
        if (
          fs.existsSync(from) &&
          fs.existsSync(path.dirname(path.join(target, rel)))
        )
          fs.symlinkSync(fs.realpathSync(from), path.join(target, rel), "dir");
      } else if (entry.isDirectory() && !IGNORED.has(entry.name)) {
        linkDependencies(from, rel);
      }
    }
  };
  linkDependencies(source);
}

/** Validate one candidate in a disposable copy of its prepared revision. */
export function preparedValidation({ runtime, revisionKind, asset, assetDir }) {
  limitTimeout();
  ensureDir(assetDir);
  const workspace = fs.mkdtempSync(path.join(assetDir, "validation-"));
  const checkout = path.join(workspace, "checkout");
  const revision = String(runtime.caseData.revisions[revisionKind]);
  const materialized = {
    revision,
    copy_root: checkout,
    test_file: asset.test_file,
  };
  let result;
  try {
    copyCheckout(runtime.roots[revisionKind], checkout);
    const relative = safeRelativePath(asset.test_file);
    const target = path.join(checkout, relative);
    // Resolve existing parents before creating directories through a symlink.
    let ancestor = path.dirname(target);
    while (!fs.existsSync(ancestor)) ancestor = path.dirname(ancestor);
    const realAncestor = fs.realpathSync(ancestor);
    const realRoot = fs.realpathSync(checkout);
    if (
      realAncestor !== realRoot &&
      !realAncestor.startsWith(`${realRoot}${path.sep}`)
    ) {
      throw new Error(`generated test path escapes checkout: ${relative}`);
    }
    ensureDir(path.dirname(target));
    fs.writeFileSync(target, `${asset.append_code.trimEnd()}\n`, {
      flag: "wx",
    });
    result = validateVitest({
      projectRoot: checkout,
      testFile: asset.test_file,
      testCommand: runtime.packet.test_command,
      outDir: path.join(assetDir, `${revisionKind}.vitest`),
      timeoutSeconds: runtime.options.timeoutSeconds,
      env: runtime.env,
    });
  } finally {
    fs.rmSync(workspace, { recursive: true, force: true });
    materialized.cleanup = { removed: !fs.existsSync(workspace) };
    writeJson(
      path.join(assetDir, `${revisionKind}.materialized.json`),
      materialized,
    );
  }
  limitTimeout();
  return { materialized, result, summary: validationSummary(revision, result) };
}

export async function modelComplete(runtime, prompt) {
  limitTimeout();
  let response;
  if (runtime.options.modelClient?.complete) {
    response = await runtime.options.modelClient.complete(prompt);
  } else {
    response = await chatCompletion({
      prompt,
      model: runtime.options.model,
      provider: runtime.options.provider,
      env: runtime.env,
      timeoutMs: runtime.options.modelTimeoutMs,
      retries: runtime.options.modelRetries,
    });
  }
  limitTimeout();
  return response;
}

export function rawPayload(runtime, response) {
  if (runtime.options.modelClient?.rawPayload) {
    return runtime.options.modelClient.rawPayload(response);
  }
  return {
    provider: runtime.options.provider,
    model: runtime.options.model,
    response,
  };
}

/** Persist a completed model response at its phase-specific path. */
export async function completeAndRecord(runtime, prompt, rawPath) {
  const response = await modelComplete(runtime, prompt);
  writeJson(rawPath, rawPayload(runtime, response));
  return response;
}

export function validationSummary(revision, result) {
  return {
    revision,
    passed: Boolean(result.evidence?.passed),
    phase: "vitest",
    exit_code: result.exit_code,
    timed_out: Boolean(result.timed_out),
    status: result.status || "",
    classification_source: result.evidence?.classification_source || "",
    classification_reason: result.evidence?.classification_reason || "",
    diagnostics: result.evidence?.diagnostics || {},
    failed_hooks: result.evidence?.failed_hooks || [],
    signal: result.signal || "",
    test_counts: result.test_counts || {},
    failed_nodeids: result.evidence?.failed_nodeids || [],
    failure_excerpt: result.evidence?.failure_excerpt || "",
    output_tail: compactText(result.output_tail || "", 4000),
  };
}

export function validateRevision({ runtime, revisionKind, asset, assetDir }) {
  limitTimeout();
  const result = runtime.options.validationRunner({
    runtime,
    revisionKind,
    asset,
    assetDir,
  });
  writeJson(path.join(assetDir, `${revisionKind}.validation.json`), result);
  limitTimeout();
  return result;
}

/** Save a candidate and validate the active buggy or latest checkout. */
export function validateBuggyAsset(
  runtime,
  asset,
  sampleDir,
  parseErrors = [],
) {
  const proposalPath = path.join(sampleDir, "proposal.json");
  writeJson(proposalPath, {
    ...asset,
    ...(parseErrors.length ? { parse_errors: parseErrors } : {}),
  });
  const buggy = validateRevision({
    runtime,
    revisionKind: primaryRevisionKind(runtime.options.evaluationMode),
    asset,
    assetDir: sampleDir,
  });
  return { asset, proposalPath, sampleDir, buggy };
}
