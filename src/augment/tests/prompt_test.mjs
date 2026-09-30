import assert from "node:assert/strict";
import path from "node:path";
import { test } from "node:test";
import { pathToFileURL } from "node:url";

import { renderCoverageTargetPrompt, repairMessage } from "../typescript/prompt/prompts.mjs";
import { parseModelResponse } from "../typescript/prompt/proposal.mjs";
import { normalizeFormalRepairSchema } from "./typescript_fixture.mjs";

const formalRoot = process.env.AUGMENT_FORMAL_ROOT ?? process.env.PROBE_FORMAL_ROOT;
const formal = formalRoot
  ? await import(pathToFileURL(path.join(formalRoot, "src/common/test_augmentF/TS/prompt.mjs")))
  : null;
const packet = {
  objective: { objective_id: "target" },
  seed_test: { test_file: "test/seed.test.ts", sha256: "fixture", suites: [{ suite_id: "suite-001" }] },
  test_name_suffix: "_round_001",
  output_contract: { vitest_namespace: "vitest", target_binding: "target", target_loader: "loadTarget" },
};
const context = {
  objective: { filepath: "src/target.ts", seed_test: packet.seed_test },
  generatedTestPreview: "test/test-augment.test.ts",
  targetModuleImport: "../src/target.js",
  targetCoverage: { uncovered_lines: [2] },
  targetBranchGaps: [],
};
const row = { status: "validation_failed" };
const failure = { failure_evidence: "AssertionError: fixture" };

function requestExample(prompt, marker, endMarker = "") {
  const start = prompt.indexOf(marker);
  assert.ok(start >= 0, marker);
  let content = prompt.slice(start + marker.length);
  if (endMarker) {
    const end = content.indexOf(endMarker);
    assert.ok(end >= 0, endMarker);
    content = content.slice(0, end);
  }
  return JSON.parse(content.trim());
}

for (const kind of [
  "export_surface", "module_context", "symbol_definition",
  "function_definition", "class_definition", "test_file_context",
]) {
  test(`generation and repair share context request fields: ${kind}`, () => {
    const initial = requestExample(
      renderCoverageTargetPrompt(packet),
      "Return only one JSON object. Context may be requested once:",
      "Or return a proposal:",
    );
    const repair = requestExample(
      repairMessage(context, row, failure, [], 3),
      "Or request exact missing context:",
    );
    assert.deepEqual(repair.requests, initial.requests);
    assert.deepEqual(Object.keys(initial), ["action", "requests"]);
    assert.deepEqual(Object.keys(repair), ["action", "diagnosis", "requests"]);
    assert.ok(repair.diagnosis);
    for (const example of [initial, repair]) {
      assert.ok(example.requests[0].kind.split("|").includes(kind));
      example.requests[0].kind = kind;
      const parsed = parseModelResponse(example);
      assert.deepEqual(parsed.requests, example.requests);
      assert.equal(parsed.requests[0].start_line, 1);
      assert.equal(parsed.requests[0].end_line, 20);
    }
  });
}

for (const strategy of ["contract_directed", "contract_agnostic"]) {
  for (const limit of [0, 3]) {
    test(`context request controls: ${strategy}/${limit}`, () => {
      const initial = renderCoverageTargetPrompt(packet, strategy);
      const repair = repairMessage({ ...context, strategy }, row, failure, [], limit);
      assert.equal(initial.includes('"action": "request_context"'), strategy === "contract_directed");
      const enabled = strategy === "contract_directed" && limit > 0;
      assert.equal(repair.includes('"action": "request_context"'), enabled);
      assert.ok(repair.includes(enabled
        ? `at most ${limit} item(s)`
        : "Repair-time context requests are disabled."));
    });

    test(`prompt reference differs only in repair schema: ${strategy}/${limit}`, { skip: !formal }, () => {
      assert.equal(renderCoverageTargetPrompt(packet, strategy), formal.renderCoverageTargetPrompt(packet, strategy));
      const options = { ...context, strategy };
      const expected = formal.repairMessage(options, row, failure, [], limit);
      const actual = repairMessage(options, row, failure, [], limit);
      assert.equal(actual, normalizeFormalRepairSchema(expected));
      assert.equal(actual === expected, strategy !== "contract_directed" || limit === 0);
    });
  }
}
