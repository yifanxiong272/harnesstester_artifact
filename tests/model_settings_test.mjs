import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import vm from "node:vm";
import test from "node:test";

import * as settings from "../src/common/model_settings.mjs";
import { safeRelativePath } from "../src/augment/typescript/paths.mjs";
import { parseProbeArgs } from "../src/probe/typescript/runner.mjs";

const artifact = fileURLToPath(new URL("..", import.meta.url));
const formal = process.env.AUGMENT_FORMAL_ROOT || process.env.PROBE_FORMAL_ROOT;
const dependencies = process.env.ARTIFACT_TEST_NODE_MODULES || process.env.PROBE_TEST_NODE_MODULES;
const require = createRequire(dependencies ? path.join(dependencies, "../package.json") : import.meta.url);
const ts = require("typescript");
const clone = (value) => JSON.parse(JSON.stringify(value));

for (const [name, processEnv, fileEnv, explicit, expected] of [
  ["default", {}, {}, null, "gpt-5-mini"],
  ["process", { OPENAI_MODEL: "process-model" }, {}, null, "process-model"],
  ["file", {}, { OPENAI_MODEL: "file-model" }, null, "file-model"],
  ["file override", { OPENAI_MODEL: "process-model" }, { OPENAI_MODEL: "file-model" }, null, "file-model"],
  ["generic model", {}, { LLM_MODEL: "generic", OPENAI_MODEL: "provider" }, null, "generic"],
  ["generic process", { LLM_MODEL: "process-model" }, { OPENAI_MODEL: "file-model" }, null, "process-model"],
  ["generic file override", { LLM_MODEL: "process-model" }, { LLM_MODEL: "file-model" }, null, "file-model"],
  ["explicit default", {}, { OPENAI_MODEL: "file-model" }, "gpt-5-mini", "gpt-5-mini"],
  ["explicit", { LLM_MODEL: "process-model" }, { OPENAI_MODEL: "file-model" }, "explicit-model", "explicit-model"],
]) {
  test(`TypeScript Probe model selection: ${name}`, (t) => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "probe-model-options-"));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const previous = { ...process.env };
    t.after(() => { process.env = previous; });
    for (const key of ["LLM_MODEL", "OPENAI_MODEL", "LLM_PROVIDER"])
      delete process.env[key];
    Object.assign(process.env, processEnv);
    const envFile = path.join(root, "model.env");
    const content = Object.entries(fileEnv).map(([key, value]) => `${key}=${value}\n`).join("");
    fs.writeFileSync(envFile, content);
    const before = { ...process.env };
    const args = ["--env-file", envFile, ...(explicit ? ["--model", explicit] : [])];
    assert.equal(parseProbeArgs(args).options.model, expected);
    assert.deepEqual({ ...process.env }, before);
    assert.equal(fs.readFileSync(envFile, "utf8"), content);
  });
}

// Keep the client's actual policy code; replace only I/O and the clock.
function loadPolicy(file, bindings, omitted = []) {
  const tree = ts.createSourceFile(file, fs.readFileSync(file, "utf8"), ts.ScriptTarget.Latest, true);
  const source = tree.statements.filter((node) =>
    !ts.isImportDeclaration(node) && !ts.isExportDeclaration(node) &&
    !omitted.includes(node.name?.text),
  ).map((node) => node.getText(tree).replace(/^export /u, "")).join("\n");
  const context = vm.createContext({ ...settings, path, ...bindings });
  vm.runInContext(source, context, { filename: file });
  return context;
}

async function runPolicy(file, scenario) {
  const trace = [];
  let calls = 0;
  let now = 0;
  const record = (...event) => trace.push(clone(event));
  const context = loadPolicy(file, {
    Date: { now: () => now },
    limitTimeout: (timeout = 10000) => timeout,
    CaseBudgetExceeded: class CaseBudgetExceeded extends Error {},
    async sleep(ms) { record("sleep", ms); now += ms; },
    async postJson(request) {
      record("request", request);
      const step = scenario.responses?.[calls++] || {};
      now += step.elapsed || 0;
      if (step.error) throw new Error(step.error);
      return {
        ok: !step.status || step.status === 200,
        status: step.status || 200,
        text: step.text ?? '{"choices":[{"message":{"content":"{}"}}]}',
        headers: new Map([["retry-after", step.retryAfter || ""]]),
      };
    },
  }, ["postJson", "sleep"]);
  const input = {
    prompt: "original prompt", model: "fixture", retries: 1,
    env: { LLM_API_KEY: "fixture-secret", LLM_BASE_URL: "https://model.invalid/v1/" },
    ...scenario.input,
  };
  const before = clone(input);
  let outcome;
  try {
    outcome = { value: await context.chatCompletion(input) };
  } catch (error) {
    outcome = { error: error.message, name: error.name, retryable: error.retryable, status: error.status };
  }
  assert.deepEqual(clone(input), before);
  return clone({ trace, outcome });
}

const scenarios = {
  direct: {},
  router: { input: { provider: "openrouter", env: { OPENROUTER_API_KEY: "router-key", LLM_MAX_TOKENS: "12.9" } } },
  precedence: { input: { env: { OPENAI_API_KEY: "provider-key", LLM_API_KEY: "generic-key", OPENAI_BASE_URL: "https://provider.invalid/", LLM_BASE_URL: "https://fallback.invalid", TEST_AUGMENT_MAX_TOKENS: "42", LLM_MAX_TOKENS: "7" } } },
  emptyProvider: { input: { env: { OPENAI_API_KEY: "", LLM_API_KEY: "generic-key", OPENAI_BASE_URL: "", LLM_BASE_URL: "https://fallback.invalid" } } },
  invalidTokens: { input: { env: { LLM_API_KEY: "fixture-key", TEST_AUGMENT_MAX_TOKENS: "bad", LLM_MAX_TOKENS: "10" } } },
  fractionalTokens: { input: { env: { LLM_API_KEY: "fixture-key", LLM_MAX_TOKENS: ".5" } } },
  missingKey: { input: { env: {} } },
  unsupported: { input: { provider: "unsupported" } },
  missingModel: { input: { model: "" } },
  customSystem: { input: { prompt: null, messages: [{ role: "system", content: "preserve this" }, { role: "user", content: "question" }] } },
  noSystem: { input: { prompt: null, messages: [{ role: "user", content: "question" }] } },
  ambiguousInput: { input: { messages: [] } },
  missingInput: { input: { prompt: null } },
  requestTimeout: { input: { timeoutMs: 600, env: { LLM_API_KEY: "fixture-key", LLM_REQUEST_TIMEOUT_MS: "21.8" } } },
  totalTimeout: { input: { totalTimeoutMs: 10 }, responses: [{ status: 503, elapsed: 11 }] },
  forbidden: { responses: [{ status: 403, text: "fixture-secret" }] },
  retry: { responses: [{ status: 429, retryAfter: "0.01" }] },
  exhausted: { responses: [{ status: 503 }, { status: 503 }] },
  network: { responses: [{ error: "connection closed" }] },
  malformedResponse: { responses: [{ text: "invalid JSON" }] },
  noAttempts: { input: { retries: -1 } },
};

for (const [workflow, module, original] of [
  ["augment", "augment/typescript/run/client.mjs", "test_augmentF/TS/client.mjs"],
  ["probe", "probe/typescript/run/client.mjs", "test_augment/TS/run/client.mjs"],
]) {
  for (const [name, scenario] of Object.entries(scenarios)) {
    test(`${workflow} client policy matches formal: ${name}`, { skip: !formal }, async () => {
      assert.deepEqual(
        await runPolicy(path.join(artifact, "src", module), scenario),
        await runPolicy(path.join(formal, "src/common", original), scenario),
      );
    });
  }
  test(`${workflow} response decoding matches formal`, { skip: !formal }, () => {
    const reference = loadPolicy(path.join(formal, "src/common", original), {});
    for (const content of [undefined, null, "", "text", 0, false, ["text"], { text: "value" }]) {
      const response = { choices: [{ message: { content } }] };
      assert.equal(settings.messageContent(response), reference.messageContent(response));
    }
    assert.equal(settings.messageContent({}), reference.messageContent({}));
  });
  test(`${workflow} env parsing preserves its formal quote rules`, { skip: !formal }, (t) => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "artifact-client-env-"));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const file = path.join(root, ".env");
    const lines = [
      "# comment", "invalid", "=ignored", "export A = first", "A=second",
      "B=one=two", "EMPTY=", 'QUOTED="text"', 'MIXED=\' " value " \'',
      "export export DOUBLE = value", "COMMENT=value # comment",
      'MALFORMED="unterminated', 'VALUE="\'nested\'"',
    ];
    fs.writeFileSync(file, lines.join("\r\n"));
    const implementation = loadPolicy(path.join(artifact, "src", module), { fs });
    const reference = loadPolicy(path.join(formal, "src/common", original), { fs });
    for (const input of [undefined, null, "", path.join(root, "missing"), file]) {
      assert.deepEqual(clone(implementation.parseEnvFile(input)), clone(reference.parseEnvFile(input)));
    }
    assert.equal(fs.readFileSync(file, "utf8"), lines.join("\r\n"));
  });
}

test("prepared input path checks match both formal loaders", { skip: !formal }, () => {
  const values = [null, undefined, "", ".", "..", "../a", "a/../b", "a/./b", "a//b", "a/", "/a", "C:/a", "C:\\a", "a\\b", "a\0b", "src/a.ts", 42];
  for (const file of ["snapshot.mjs", "seed_coverage.mjs"]) {
    const reference = loadPolicy(path.join(formal, "src/common/test_augmentF/TS/input", file), {});
    for (const value of values) {
      assert.equal(safeRelativePath(value), reference.safeRelativePath(value), `${file}: ${value}`);
    }
  }
});
