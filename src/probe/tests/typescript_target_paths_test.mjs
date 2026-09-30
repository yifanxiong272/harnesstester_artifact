import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { loadTargetUnits, sourceFileIndex } from "../typescript/input/target_units.mjs";

function fixture(t) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "probe-target-paths-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const root = path.join(directory, "checkout");
  const outside = path.join(directory, "checkout-other");
  fs.mkdirSync(path.join(root, "src"), { recursive: true });
  fs.mkdirSync(outside);
  const source = "export function value() {\n  return 7;\n}\n";
  fs.writeFileSync(path.join(root, "src/value.ts"), source);
  fs.writeFileSync(path.join(outside, "value.ts"), "outside source must not be read");
  return { directory, root, outside, source };
}

function units(root, filepath) {
  return loadTargetUnits(root, [{
    filepath, qualname: "value", kind: "function", start_line: 1, end_line: 3,
  }]);
}

test("ordinary targets retain coordinates, identifiers and source hashes", (t) => {
  const { root, source } = fixture(t);
  const [unit] = units(root, "src/value.ts");
  const code = source.trimEnd();
  assert.deepEqual(unit, {
    unit_id: "src/value.ts::value@1-3:function",
    filepath: "src/value.ts", qualname: "value", kind: "function",
    start_line: 1, end_line: 3, selection_source: "case", code,
    code_sha256: crypto.createHash("sha256").update(code).digest("hex"),
  });
  assert.deepEqual(sourceFileIndex(root, ["missing.ts", "src/value.ts", "src/value.ts"]), [
    { path: "src/value.ts", line_count: 3 },
  ]);
});

for (const kind of ["file", "parent", "checkout"]) {
  test(`internal ${kind} symlinks remain usable without changing target paths`, (t) => {
    const { directory, root, source } = fixture(t);
    let project = root;
    let filepath = "src/value.ts";
    if (kind === "file") {
      filepath = "alias.ts";
      fs.symlinkSync("src/value.ts", path.join(root, filepath));
    } else if (kind === "parent") {
      filepath = "alias/value.ts";
      fs.symlinkSync("src", path.join(root, "alias"), "dir");
    } else {
      project = path.join(directory, "checkout-alias");
      fs.symlinkSync(root, project, "dir");
    }
    assert.equal(units(project, filepath)[0].code, source.trimEnd());
    assert.equal(units(project, filepath)[0].filepath, filepath);
    assert.deepEqual(sourceFileIndex(project, [filepath]), [{ path: filepath, line_count: 3 }]);
  });
}

for (const kind of ["file", "parent"]) {
  for (const operation of ["target", "index"]) {
    test(`${operation} rejects an external ${kind} symlink before reading source`, (t) => {
      const { root, outside } = fixture(t);
      const filepath = kind === "file" ? "external.ts" : "external/value.ts";
      fs.symlinkSync(
        kind === "file" ? path.join(outside, "value.ts") : outside,
        path.join(root, kind === "file" ? filepath : "external"),
        kind === "file" ? "file" : "dir",
      );
      const reads = [];
      const readFile = fs.readFileSync;
      t.mock.method(fs, "readFileSync", (...args) => {
        reads.push(args[0]);
        return readFile(...args);
      });
      assert.throws(
        () => operation === "target" ? units(root, filepath) : sourceFileIndex(root, [filepath]),
        /outside|escape|unsafe/i,
      );
      assert.deepEqual(reads, []);
    });
  }
}

test("absolute and parent-traversal target paths remain rejected", (t) => {
  const { root, outside } = fixture(t);
  for (const filepath of [path.join(outside, "value.ts"), "../checkout-other/value.ts"]) {
    assert.throws(() => units(root, filepath), /unsafe relative path/);
    assert.throws(() => sourceFileIndex(root, [filepath]), /unsafe relative path/);
  }
});

test("unresolvable targets fail while missing index entries remain omitted", (t) => {
  const { root } = fixture(t);
  fs.symlinkSync("missing.ts", path.join(root, "dangling.ts"));
  assert.throws(() => units(root, "dangling.ts"), { code: "ENOENT" });
  assert.deepEqual(sourceFileIndex(root, ["dangling.ts"]), []);
});
