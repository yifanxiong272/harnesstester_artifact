/** Load reference modules and source ASTs for differential tests. */
import fs from "node:fs";
import path from "node:path";
import { createRequire, registerHooks } from "node:module";
import { pathToFileURL } from "node:url";

export const formalRoot = process.env.PROBE_FORMAL_ROOT;

export function alignFormalNames(source) {
  return source
    .replaceAll("LDCR", "LDH")
    .replaceAll("ldcr", "ldh")
    .replaceAll('"current"', '"latest"')
    .replaceAll("'current'", "'latest'")
    .replaceAll("current_", "latest_")
    .replace(/(?<!\.)\.current\b/gu, ".latest")
    .replace(/\bcurrent:/gu, "latest:");
}

// Keep formal files immutable; imported reference modules get names only.
if (formalRoot) {
  const prefixes = ["run", "prompt"].map((name) =>
    pathToFileURL(formalPath(name) + path.sep).href,
  );
  registerHooks({
    load(url, context, nextLoad) {
      const loaded = nextLoad(url, context);
      if (prefixes.some((prefix) => url.startsWith(prefix)) && url.endsWith(".mjs")) {
        return { ...loaded, source: alignFormalNames(String(loaded.source)) };
      }
      return loaded;
    },
  });
}

export function formalPath(module) {
  return path.join(formalRoot, "src/common/test_augment/TS", module);
}

export function formalModule(module) {
  return import(pathToFileURL(formalPath(module)).href);
}

export function sourceModule(file) {
  const require = createRequire(
    path.join(process.env.PROBE_TEST_NODE_MODULES, "../package.json"),
  );
  const ts = require("typescript");
  const original = fs.readFileSync(file, "utf8");
  const source = formalRoot && path.resolve(file).startsWith(formalPath("") + path.sep)
    ? alignFormalNames(original)
    : original;
  const tree = ts.createSourceFile(
    file,
    source,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.JS,
  );
  return { ts, source, tree };
}
