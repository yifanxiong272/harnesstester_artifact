import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { loadInputs } from "../src/augment/typescript/input/snapshot.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

for (const project of ["openclaw", "roo-code", "kimi-code"]) {
  test(`${project}: bundled targets and measured seed tests exist`, () => {
    const input = loadInputs(path.join(root, "resources/inputs", project, "base_input.json"));
    assert.ok(input.ldhFiles.size > 0);
    for (const file of input.ldhFiles) {
      assert.ok(fs.existsSync(path.join(input.baseInput.project_root, file)), file);
    }
    const tests = new Set(
      Object.values(input.generalTestScores).flatMap((rows) => rows.map((r) => r.test_file)),
    );
    assert.ok(tests.size > 0);
    for (const file of tests) {
      assert.ok(fs.existsSync(path.join(input.baseInput.project_root, file)), file);
    }
  });
}
