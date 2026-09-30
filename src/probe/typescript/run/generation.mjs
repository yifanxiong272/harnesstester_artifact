import path from "node:path";
import crypto from "node:crypto";
import { messageContent } from "./client.mjs";
import { CaseBudgetExceeded } from "./deadline.mjs";
import { resolveContextRequests } from "../prompt/context.mjs";
import { writeJson, writeText } from "../support/json.mjs";
import {
  renderTargetProbeImplementationPrompt,
  renderTargetProbePlanPrompt,
} from "../prompt/prompts.mjs";
import { parseProbePlan, parseProposalPartial } from "../prompt/proposal.mjs";
import { isDiscovery, primaryCheckout, strategyProfile } from "./options.mjs";
import { compactText, targetOutcomeCategory } from "./reporting.mjs";
import { completeAndRecord } from "./session.mjs";

const DIRECT_PROMPT_STYLE = "direct";

export class InvalidModelOutputError extends Error {
  constructor(error) {
    super(String(error?.message || error), { cause: error });
    this.name = "InvalidModelOutputError";
  }
}

export async function generateTargetPlanAndContext({
  runtime,
  packet,
  sampleDir,
  priorAttempts,
  promptStyle,
}) {
  const allowContext = strategyProfile(runtime.options.strategy).allowContext;
  const maxContextRequests = allowContext
    ? Math.max(0, runtime.options.contextRequests)
    : 0;
  const prompt = renderTargetProbePlanPrompt(packet, {
    priorAttempts,
    direct: promptStyle === DIRECT_PROMPT_STYLE,
  });
  const promptPath = path.join(sampleDir, "plan.prompt.md");
  writeText(promptPath, prompt);
  const response = await completeAndRecord(
    runtime,
    prompt,
    path.join(sampleDir, "plan.raw.json"),
  );
  let parsed;
  try {
    parsed = parseProbePlan(messageContent(response), { maxContextRequests });
    validateBoundaryPlan(packet, parsed.plan);
  } catch (error) {
    if (error instanceof CaseBudgetExceeded) throw error;
    throw new InvalidModelOutputError(error);
  }
  const { plan, errors } = parsed;
  const planData = { ...plan };
  if (errors.length) {
    planData.parse_errors = errors;
  }
  writeJson(path.join(sampleDir, "plan.json"), planData);
  const context = allowContext
    ? resolveContextForManifest({
        manifest: runtime.manifest,
        requests: plan.context_requests,
        maxRequests: maxContextRequests,
        outPath: path.join(sampleDir, "retrieved-context.json"),
      })
    : { requests: [] };
  packet.retrieved_context = context;
  return planData;
}

export function validateBoundaryPlan(packet, plan) {
  const allowed = new Set(
    (packet.target_units || []).map((unit) => unit.unit_id),
  );
  const focus = String(packet.focus_target_unit_id || "");
  const entrypoints = publicEntrypoints(packet);
  for (const boundary of plan.boundary_plan || []) {
    const unknown = boundary.target_unit_ids.filter(
      (unitId) => !allowed.has(unitId),
    );
    if (unknown.length > 0) {
      throw new Error(
        `boundary ${boundary.boundary_id} references unknown target_unit_ids: ${unknown.join(", ")}`,
      );
    }
    if (focus && !boundary.target_unit_ids.includes(focus)) {
      throw new Error(
        `boundary ${boundary.boundary_id} does not include focused target unit ${focus}`,
      );
    }
    const entrypoint = entrypoints.find(
      (item) => item.entrypoint_id === boundary.route.entrypoint_id,
    );
    if (!entrypoint) {
      throw new Error(
        `boundary ${boundary.boundary_id} references unavailable public entrypoint ${boundary.route.entrypoint_id}`,
      );
    }
    if (!boundary.target_unit_ids.includes(entrypoint.target_unit_id)) {
      throw new Error(
        `boundary ${boundary.boundary_id} public entrypoint does not reach a selected target unit`,
      );
    }
  }
}

export async function generateProbeAssets({
  runtime,
  packet,
  plan,
  sampleDir,
  priorAttempts,
  promptStyle,
}) {
  const prompt = renderTargetProbeImplementationPrompt(packet, {
    plan,
    priorAttempts,
    maxAssets: runtime.options.assetsPerSample,
    direct: promptStyle === DIRECT_PROMPT_STYLE,
  });
  const promptPath = path.join(sampleDir, "implementation.prompt.md");
  writeText(promptPath, prompt);
  const response = await completeAndRecord(
    runtime,
    prompt,
    path.join(sampleDir, "implementation.raw.json"),
  );
  let parsed;
  try {
    parsed = parseProposalPartial(
      messageContent(response),
      proposalParseOptions(
        runtime,
        packet,
        runtime.options.assetsPerSample,
        plan,
      ),
    );
  } catch (error) {
    if (error instanceof CaseBudgetExceeded) throw error;
    throw new InvalidModelOutputError(error);
  }
  const { proposal, errors } = parsed;
  proposal.assets = proposal.assets.map((asset) => ({
    ...asset,
    semantic_fingerprint: semanticFingerprint(asset),
  }));
  const data = { ...proposal };
  if (!data.boundary_plan?.length && plan.boundary_plan?.length) {
    data.boundary_plan = plan.boundary_plan;
  }
  if (errors.length) {
    data.parse_errors = errors;
  }
  // Parsed assets inherit target/focus membership from the validated plan.
  const deduplicated = filterSemanticDuplicates(proposal.assets, priorAttempts);
  const assets = deduplicated.assets;
  if (deduplicated.dropped.length) {
    data.dropped_duplicate_assets = deduplicated.dropped;
  }
  const proposalPath = path.join(sampleDir, "proposal.json");
  writeJson(proposalPath, data);
  return { path: proposalPath, assets };
}

export function filterSemanticDuplicates(assets, priorAttempts) {
  const seen = priorSemanticFingerprints(priorAttempts);
  const kept = [];
  const dropped = [];
  for (const asset of assets) {
    const fingerprint =
      asset.semantic_fingerprint || semanticFingerprint(asset);
    if (seen.has(fingerprint)) {
      dropped.push({
        asset_id: asset.asset_id,
        semantic_fingerprint: fingerprint,
      });
      continue;
    }
    seen.add(fingerprint);
    kept.push({ ...asset, semantic_fingerprint: fingerprint });
  }
  return { assets: kept, dropped };
}

export function priorSemanticFingerprints(priorAttempts) {
  const fingerprints = new Set();
  for (const attempt of priorAttempts || []) {
    if (attempt.semantic_fingerprint) {
      fingerprints.add(attempt.semantic_fingerprint);
    }
    for (const fingerprint of attempt.semantic_fingerprints || []) {
      if (fingerprint) {
        fingerprints.add(fingerprint);
      }
    }
  }
  return fingerprints;
}

export function semanticFingerprint(asset) {
  const normalized = (value) => compactText(value, 1000).toLowerCase();
  const payload = {
    target_unit_ids: [...(asset.target_unit_ids || [])].sort(),
    public_entrypoint_id: asset.public_entrypoint_id || "",
    test_intent: normalized(asset.test_intent),
    activation_conditions: (asset.activation_conditions || [])
      .map(normalized)
      .sort(),
    independent_oracle: normalized(asset.independent_oracle),
    input_construction: normalized(asset.input_construction),
    primary_oracle: normalized(asset.primary_oracle),
  };
  return crypto
    .createHash("sha256")
    .update(JSON.stringify(payload))
    .digest("hex");
}

export function priorAttemptLedger(rows, maxItems = 18) {
  const families = new Map();
  for (const row of rows) {
    const discovery = isDiscovery(row.evaluation_mode);
    const outcomeKey = discovery ? "latest_outcomes" : "buggy_outcomes";
    for (const asset of row.assets || []) {
      const fingerprint =
        asset.semantic_fingerprint ||
        (asset.input_construction ? semanticFingerprint(asset) : "");
      if (!fingerprint) {
        continue;
      }
      const targetUnitIds = [...(asset.target_unit_ids || [])]
        .map(String)
        .sort();
      const oracleFamily = compactText(
        asset.oracle_family ||
          asset.independent_oracle ||
          asset.primary_oracle ||
          asset.test_intent ||
          `unclassified-${fingerprint.slice(0, 12)}`,
        260,
      );
      const familyKey = `${targetUnitIds.join("\0")}\0${compactText(
        oracleFamily,
        1000,
      ).toLowerCase()}`;
      const familyId = `family-${crypto
        .createHash("sha256")
        .update(familyKey)
        .digest("hex")
        .slice(0, 12)}`;
      const family = families.get(familyKey) || {
        family_id: familyId,
        target_unit_ids: targetUnitIds,
        oracle_family: oracleFamily,
        representative_intent: compactText(asset.test_intent, 180),
        attempt_count: 0,
        [outcomeKey]: {},
        semantic_fingerprints: [],
      };
      family.attempt_count += 1;
      const outcome = targetOutcomeCategory(asset, discovery);
      const outcomeCounts = family[outcomeKey];
      outcomeCounts[outcome] = (outcomeCounts[outcome] || 0) + 1;
      if (!family.semantic_fingerprints.includes(fingerprint)) {
        family.semantic_fingerprints.push(fingerprint);
      }
      families.delete(familyKey);
      families.set(familyKey, family);
    }
  }
  return [...families.values()].slice(-Math.max(0, maxItems));
}

export function resolveContextForManifest({
  manifest,
  requests,
  maxRequests,
  outPath,
}) {
  const checkout = primaryCheckout(manifest)?.path;
  const sourceRoots = Array.isArray(manifest.source_roots)
    ? manifest.source_roots
    : [];
  const source = isDiscovery(manifest.evaluation_mode)
    ? "target-revision exact context requests"
    : "buggy-side exact context requests";
  const resolved = checkout
    ? resolveContextRequests({
        projectRoot: checkout,
        sourceRoots,
        requests,
        maxRequests,
        source,
      })
    : {
        source,
        requests: [],
        error: "missing_target_checkout",
      };
  writeJson(outPath, resolved);
  return resolved;
}

export function proposalParseOptions(
  runtime,
  packet,
  maxAssets,
  canonicalPlan,
) {
  return {
    maxAssets,
    allowedTestRoots: packet.generated_test_roots,
    projectRoot: primaryCheckout(runtime.manifest)?.path || "",
    canonicalPlan,
    publicEntrypoints: publicEntrypoints(packet),
  };
}

export function publicEntrypoints(packet) {
  return (packet.public_target_routes?.targets || []).flatMap((target) =>
    (target.entrypoints || []).map((entrypoint) => ({
      ...entrypoint,
      target_unit_id: target.target_unit_id,
    })),
  );
}
