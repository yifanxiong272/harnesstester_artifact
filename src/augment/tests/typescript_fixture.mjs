import fs from "node:fs";
import path from "node:path";

// The artifact exposes the same request fields in generation and repair.
// Reference comparisons retain every other byte of the formal prompt.
export function normalizeFormalRepairSchema(text) {
  const request = {
    kind: "module_context|symbol_definition|function_definition|class_definition|test_file_context",
    filepath: "project/relative/path.ts",
    qualname: "exact.qualified.name",
    reason: "contract required to repair the test",
  };
  const envelope = {
    action: "request_context",
    diagnosis: "evidence-based root cause and missing contract",
    requests: [request],
  };
  const aligned = {
    ...envelope,
    requests: [{
      kind: `export_surface|${request.kind}`,
      filepath: request.filepath,
      qualname: request.qualname,
      start_line: 1,
      end_line: 20,
      reason: "contract required by the test",
    }],
  };
  return text.replace(
    JSON.stringify(envelope, null, 2),
    JSON.stringify(aligned, null, 2),
  );
}

export function writeJson(file, data) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(data));
}

export function projectFixture(root, nodeModules) {
  const project = path.join(root, "project");
  fs.mkdirSync(path.join(project, "src"), { recursive: true });
  fs.mkdirSync(path.join(project, "test"));
  fs.symlinkSync(nodeModules, path.join(project, "node_modules"), "dir");
  writeJson(path.join(project, "package.json"), { type: "module" });
  fs.writeFileSync(path.join(project, "src/target.ts"),
    'export function choose(value: boolean) {\n  if (value) return "yes";\n  return "no";\n}\n');
  fs.writeFileSync(path.join(project, "src/helper.ts"), 'export const expected = "yes";\n');
  fs.writeFileSync(path.join(project, "test/seed.test.ts"), [
    'import { describe, it, expect } from "vitest";',
    'import { choose } from "../src/target.js";',
    'describe("seed", () => { it("baseline", () => expect(choose(true)).toBe("yes")); });',
  ].join("\n"));
  const input = path.join(root, "input.json");
  writeJson(path.join(root, "regions.json"), {
    sources: [{ location: { filepath: "src/target.ts", start_line: 1, end_line: 3 } }],
    data_dependence: [],
  });
  writeJson(path.join(root, "coverage.json"), {
    project: "fixture", files: { "src/target.ts": {
      lines: { total: [[1, 3]], covered: [[1, 1]] },
      branches: [{ line: 2, total: 2, covered: 0 }],
    } },
    test_coverage: { "src/target.ts": { "test/seed.test.ts": { lines: [[1, 1]], branch_lines: [] } } },
  });
  writeJson(input, {
    project: "fixture", project_root: "project",
    ldh: { regions_json: "regions.json" }, general_cov: { coverage_json: "coverage.json" },
  });
  return { project, input };
}

export function scriptedModel(scenario, conversations) {
  let calls = 0;
  return async ({ messages }) => {
    calls += 1;
    conversations.push(structuredClone(messages));
    if (scenario === "transport_retry" && calls === 1) {
      throw new Error("temporary model transport error");
    }
    let response;
    if ((scenario === "initial_context" && calls === 1) ||
        (scenario === "repair_context" && calls === 2)) {
      response = { action: "request_context", diagnosis: "Check the return contract.",
        requests: [{ kind: "module_context", filepath: "src/helper.ts",
          reason: "Expected collaborator value." }] };
    } else {
      const prompt = messages[0].content;
      const namespace = prompt.match(/"vitest_namespace": "([^"]+)"/u)[1];
      const loader = prompt.match(/"target_loader": "([^"]+)"/u)[1];
      const suffix = [...messages.filter(m => m.role === "user").flatMap(m =>
        [...m.content.matchAll(/"test_name_suffix": "([^"]+)"/gu)].map(x => x[1]),
      )].at(-1);
      const wrong = ["repair", "repair_context"].includes(scenario) && calls === 1;
      const body = scenario === "continuation" && calls === 1
        ? `${namespace}.expect(target.choose(true)).toBe("yes");`
        : `${namespace}.expect(target.choose(true)).toBe(${JSON.stringify(wrong ? "wrong" : "yes")}); ${namespace}.expect(target.choose(false)).toBe("no");`;
      const unit = {
        label: "paths", test_name: `paths${suffix}`,
        append_code: `${namespace}.it("paths${suffix}", async () => { const target = await ${loader}(); ${body} });`,
        oracle: "return value", mocking_strategy: "none",
      };
      const units = [unit];
      if (scenario === "partial") units.push({
        ...unit, label: "bad", test_name: `bad${suffix}`,
        append_code: `${namespace}.it("bad${suffix}", () => { ${namespace}.expect(true).toBe(false); });`,
      });
      response = { action: "propose_test", suite_id: "suite-001", test_units: units };
    }
    return { choices: [{ message: { content: JSON.stringify(response) } }],
      usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 } };
  };
}
