import fs from "node:fs";

import {
  normalizeTargetStrategy,
  TARGET_PROBE_LDH_STRATEGY,
  strategyProfile,
} from "../run/options.mjs";

function renderTemplate(name, values) {
  const template = new URL(`templates/${name}_prompt.md`, import.meta.url);
  let text = fs.readFileSync(template, "utf8");
  for (const [key, value] of Object.entries(values)) {
    const replacement = String(
      key.endsWith("_json") ? prettyJson(value) : value,
    );
    text = text.split(`$${key}`).join(replacement);
  }
  return `${text.trimEnd()}\n`;
}

function prettyJson(value) {
  return JSON.stringify(value ?? {}, null, 2);
}

export function promptPriorAttempts(priorAttempts) {
  return (priorAttempts || []).map((attempt) => {
    const promptAttempt = { ...attempt };
    const targetOutcomes =
      promptAttempt.latest_outcomes || promptAttempt.buggy_outcomes;
    if (targetOutcomes) {
      promptAttempt.target_outcomes = targetOutcomes;
    }
    delete promptAttempt.latest_outcomes;
    delete promptAttempt.buggy_outcomes;
    delete promptAttempt.semantic_fingerprint;
    delete promptAttempt.semantic_fingerprints;
    return promptAttempt;
  });
}

function generatedTestFileExample(packet) {
  const roots =
    Array.isArray(packet.generated_test_roots) &&
    packet.generated_test_roots.length
      ? packet.generated_test_roots
      : ["test/generated/benchmarkbr"];
  return `${String(roots[0]).replace(/\/$/u, "")}/test_generated_target_probe_asset_001.test.ts`;
}

export function renderTargetProbePlanPrompt(
  packet,
  { priorAttempts = [], direct = false } = {},
) {
  return renderTemplate(
    direct ? "target_probe_direct_plan" : "target_probe_plan",
    {
      strategy_guidance: targetGuidance(packet, direct),
      context_request_instruction: planContextInstruction(packet, direct),
      packet_json: promptPacket(packet),
      prior_attempts_json: promptPriorAttempts(priorAttempts),
    },
  );
}

export function renderTargetProbeImplementationPrompt(
  packet,
  { plan = {}, priorAttempts = [], maxAssets = 5, direct = false } = {},
) {
  return renderTemplate(
    direct
      ? "target_probe_direct_implementation"
      : "target_probe_implementation",
    {
      strategy_guidance: targetGuidance(packet, direct),
      packet_json: promptPacket(packet),
      plan_json: plan,
      prior_attempts_json: promptPriorAttempts(priorAttempts),
      max_assets: Math.max(1, Number(maxAssets) || 1),
      generated_test_file_example: generatedTestFileExample(packet),
    },
  );
}

export function renderTargetProbeMinimizePrompt(
  packet,
  { asset, buggySummary, retryContext = null } = {},
) {
  return renderTemplate("target_probe_minimize", {
    packet_json: promptPacket(packet),
    asset_json: asset,
    buggy_summary_json: buggySummary,
    retry_context_section: minimizationRetryContextSection(retryContext),
    generated_test_file_example: generatedTestFileExample(packet),
  });
}

export function renderTargetHarnessRepairContextRequestPrompt(
  packet,
  { plan, asset, buggySummary, tracebackContext, maxContextRequests = 0 } = {},
) {
  const contextRequestSection =
    maxContextRequests > 0
      ? `Request at most ${maxContextRequests} exact context item(s):\n\n${prettyJson(
          {
            action: "request_context",
            diagnosis: "evidence-based root cause and missing contract",
            requests: [
              {
                kind: "module_context|class_definition|function_definition|symbol_definition",
                filepath: "src/pkg/module.ts",
                qualname: "ClassName",
                reason: "contract required to repair the test",
              },
            ],
          },
        )}`
      : "Repair-time context requests are disabled for this run.";
  return renderTemplate("target_harness_repair_context_request", {
    packet_json: promptPacket(packet, { includeModuleImports: true }),
    plan_json: plan,
    asset_json: asset,
    buggy_summary_json: buggySummary,
    traceback_context_json: tracebackContext || [],
    context_request_section: contextRequestSection,
    generated_test_file_example: generatedTestFileExample(packet),
  });
}

export function renderTargetHarnessRepairPrompt(
  packet,
  { plan, asset, buggySummary, tracebackContext, repairContext } = {},
) {
  return renderTemplate("target_harness_repair", {
    packet_json: promptPacket(packet, { includeModuleImports: true }),
    plan_json: plan,
    asset_json: asset,
    buggy_summary_json: buggySummary,
    traceback_context_json: tracebackContext || [],
    repair_context_json: repairContext || {},
    generated_test_file_example: generatedTestFileExample(packet),
  });
}

export function renderTargetContractAgnosticRepairPrompt(
  packet,
  { plan, asset, buggySummary } = {},
) {
  return renderTemplate("target_contract_agnostic_repair", {
    packet_json: promptPacket(packet),
    plan_json: plan,
    asset_json: asset,
    buggy_summary_json: buggySummary,
    generated_test_file_example: generatedTestFileExample(packet),
  });
}

function planContextInstruction(packet, direct = false) {
  if (
    !strategyProfile(packet.strategy || TARGET_PROBE_LDH_STRATEGY).allowContext
  ) {
    return 'Use only the supplied packet; additional context retrieval is unavailable.\nReturn "context_requests": [].';
  }
  return direct
    ? "Request exact target-revision context only when required. Otherwise return no\nrequests."
    : "Request exact target-revision context only when the packet lacks information needed\n" +
        "to complete this chain. Requests use a project-relative `filepath` and an exact\n" +
        "AST `qualname`, except for `module_context`.";
}

export function promptPacket(packet, { includeModuleImports = false } = {}) {
  const profile = strategyProfile(
    packet.strategy || TARGET_PROBE_LDH_STRATEGY,
  );
  const payload = {
    project: packet.project,
    target_units: (packet.target_units || []).map((unit) => ({
      unit_id: unit.unit_id,
      filepath: unit.filepath,
      qualname: unit.qualname,
      kind: unit.kind,
      code: unit.code || "",
    })),
    source_file_index: packet.source_file_index || [],
    existing_tests: packet.existing_tests || [],
    // Static target import/export metadata is shared by every strategy.
    module_contracts: packet.module_contracts || [],
    public_target_routes: packet.public_target_routes || {},
    generated_test_roots: packet.generated_test_roots || [
      "test/generated/benchmarkbr",
    ],
    constraints: packet.constraints || [],
    test_command: packet.test_command || [],
  };
  if (packet.lane) {
    payload.lane = packet.lane;
  }
  if (includeModuleImports && profile.allowContext) {
    payload.module_imports = packet.module_imports || [];
  }
  if (packet.focus_target_unit_id) {
    payload.focus_target_unit_id = packet.focus_target_unit_id;
    payload.focus_sample_index = packet.focus_sample_index;
    payload.focus_total_target_units = packet.focus_total_target_units;
  }
  if (profile.allowContext && hasRetrievedContext(packet)) {
    payload.retrieved_context = packet.retrieved_context;
  }
  if (packet.boundary_plan?.length) {
    payload.boundary_plan = packet.boundary_plan;
  }
  if (packet.whole_target_pass) {
    payload.whole_target_pass = true;
    payload.soft_sample_index = packet.soft_sample_index;
  }
  return payload;
}

function hasRetrievedContext(packet) {
  return Boolean(
    packet.retrieved_context?.requests?.some(
      (item) => item?.status === "found",
    ),
  );
}

function targetGuidance(packet, direct = false) {
  const strategy = normalizeTargetStrategy(
    String(packet.strategy || TARGET_PROBE_LDH_STRATEGY),
  );
  let guidance = sharedGuidance(direct);
  if (strategy === TARGET_PROBE_LDH_STRATEGY) {
    guidance += `\n\n${ldhMethodGuidance()}`;
  }
  return guidance;
}

function sharedGuidance(direct = false) {
  let guidance = [
    "Generate deterministic tests whose purpose is to reveal a defect, not merely to pass on the target revision.",
    "Exercise the provided target units through their declared public entrypoints.",
    "Treat target code as reachability and failure-hypothesis evidence, never as the authority that defines expected behavior.",
    "Derive one independently justified public or stable semantic invariant and assert one externally observable consequence.",
    "Probe defensible boundary conditions even when the expected behavior differs from the current implementation.",
    "Choose the strongest route autonomously without forcing a specific bug pattern or testing technique.",
  ].join(" ");
  if (direct) {
    guidance +=
      " In the direct lane, minimize harness complexity while preserving the complete causal route.";
  }
  return guidance;
}

function ldhMethodGuidance() {
  return [
    "As an additional discovery aid, consider how values produced, shaped, or interpreted through model or agent interactions propagate into target behavior, and use those flows to identify defensible perturbations and observable invariants.",
    "This perspective must not displace the primary deterministic bug-reveal objective, target reachability, independent oracle quality, determinism, or a stronger alternative route; keep target behavior real and mock only necessary external or nondeterministic boundaries.",
  ].join(" ");
}

function minimizationRetryContextSection(retryContext) {
  if (!retryContext) {
    return "";
  }
  return `## Preserve-Failure Retry Context\n\nThe previous minimization did not preserve the target-revision failure. Preserve the original target call and failure-inducing input more carefully.\n\n\`\`\`json\n${prettyJson(retryContext)}\n\`\`\`\n`;
}
