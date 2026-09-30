import fs from "node:fs";
import path from "node:path";
import { exprPath } from "../syntax.mjs";
import { unwrapExpression } from "../source_locator.mjs";
import { bindingIdentifierName, bindingPropertyName } from "./assignments.mjs";
import { addTargetBinding } from "./bindings.mjs";

const SOURCE_EXTENSIONS = [".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"];

/** Build workspace package import metadata from package.json files.
 *
 * Called by: project indexing before import declarations are resolved. This is
 * intentionally limited to package.json files inside the analyzed source tree,
 * so external dependencies remain external while monorepo packages such as
 * `@scope/pkg` can resolve through their real source exports.
 */
export function buildPackageResolution(root, files) {
  const fileSet = new Set(files);
  const packagesByName = new Map();
  const packagesByDir = new Map();
  for (const dir of candidatePackageDirs(root, files)) {
    const pkg = readPackageJson(root, dir);
    if (!pkg?.name) continue;
    const info = {
      dir,
      name: pkg.name,
      exports: normalizePackageTargets(pkg.exports),
      imports: normalizePackageTargets(pkg.imports),
    };
    if (packageHasResolvableTargets(info, fileSet)) {
      packagesByName.set(info.name, info);
      packagesByDir.set(info.dir, info);
    }
  }
  return { packagesByName, packagesByDir };
}

/** Record ES module import declarations.
 *
 * Called by: index visitors. Relative imports are resolved against indexed
 * files; external provider imports are preserved by module string.
 */
export function recordImportDeclaration(ts, index, file, env, node) {
  const moduleName = literalText(ts, node.moduleSpecifier);
  if (!moduleName) return;
  const projectFile = resolveProjectModule(index, file.rel, moduleName);
  const clause = node.importClause;
  if (!clause) return;

  if (clause.name) {
    addImport(env, clause.name.text, {
      kind: "default",
      module: moduleName,
      imported: "default",
      project_file: projectFile,
    });
  }

  const bindings = clause.namedBindings;
  if (!bindings) return;
  if (ts.isNamespaceImport(bindings)) {
    addImport(env, bindings.name.text, {
      kind: "namespace",
      module: moduleName,
      imported: "*",
      project_file: projectFile,
    });
    return;
  }

  if (ts.isNamedImports(bindings)) {
    for (const element of bindings.elements) {
      addImport(env, element.name.text, {
        kind: "named",
        module: moduleName,
        imported: element.propertyName?.text || element.name.text,
        project_file: projectFile,
      });
    }
  }
}

/** Record `import x = require("module")` declarations.
 *
 * Called by: index visitors for CommonJS-compatible TypeScript code.
 */
export function recordImportEqualsDeclaration(ts, index, file, env, node) {
  if (!ts.isExternalModuleReference(node.moduleReference)) return;
  const moduleName = literalText(ts, node.moduleReference.expression);
  if (!moduleName) return;
  addImport(env, node.name.text, {
    kind: "require",
    module: moduleName,
    imported: "*",
    project_file: resolveProjectModule(index, file.rel, moduleName),
  });
}

/** Record `require()` and literal dynamic `import()` variable bindings.
 *
 * Called by: visitors when they encounter a variable statement. Imports are
 * scoped to the containing function/module env.
 */
export function recordRequireImportsFromVariableStatement(ts, index, file, env, node) {
  for (const declaration of node.declarationList.declarations || []) {
    const moduleName = importLikeModuleName(ts, declaration.initializer);
    if (!moduleName) continue;
    const projectFile = resolveProjectModule(index, file.rel, moduleName);
    recordImportBindingPattern(ts, env, declaration.name, {
      kind: "require",
      module: moduleName,
      imported: "*",
      project_file: projectFile,
    });
  }
}

/** Resolve a literal relative module specifier to an indexed project file.
 *
 * Called by: import/export helpers. External provider modules intentionally
 * return an empty string.
 */
export function resolveProjectModule(index, fromFile, moduleName) {
  if (!moduleName.startsWith(".")) return resolveWorkspacePackageModule(index, fromFile, moduleName);
  return resolveModuleRelativeToDir(index, path.posix.dirname(fromFile), moduleName);
}

/** Resolve one relative specifier from a project-relative directory. */
function resolveModuleRelativeToDir(index, fromDir, moduleName) {
  const raw = normalizeRelPath(path.posix.normalize(path.posix.join(fromDir, moduleName)));
  for (const candidate of moduleCandidates(raw)) {
    if (index.fileSet.has(candidate)) return candidate;
  }
  return "";
}

/** Resolve monorepo package imports using package.json exports/imports.
 *
 * Called by: `resolveProjectModule` after relative imports fail. Package-name
 * imports use the target package's `exports`; `#...` imports use the containing
 * package's `imports`. All targets still have to resolve to an indexed source
 * file, which prevents node_modules or generated files from entering the graph.
 */
function resolveWorkspacePackageModule(index, fromFile, moduleName) {
  const packages = index.packageResolution;
  if (!packages) return "";
  if (moduleName.startsWith("#")) {
    const owner = packageForFile(packages, fromFile);
    return owner ? resolvePackageSpecifier(index, owner, moduleName, owner.imports) : "";
  }

  const { packageName, subpath } = splitPackageSpecifier(moduleName);
  const pkg = packages.packagesByName.get(packageName);
  if (!pkg) return "";
  return resolvePackageSpecifier(index, pkg, subpath, pkg.exports);
}

/** Return a literal module string from import/require arguments.
 *
 * Called by: import and export recorders. Dynamic module expressions are
 * skipped.
 */
export function literalText(ts, node) {
  if (!node) return "";
  if (ts.isStringLiteralLike?.(node)) return node.text;
  return "";
}

/** Add import targets introduced by one binding pattern.
 *
 * Called by: CommonJS `require()` handling. Object destructuring maps each
 * local variable to the destructured imported property.
 */
function recordImportBindingPattern(ts, env, bindingName, target) {
  if (ts.isIdentifier(bindingName)) {
    addImport(env, bindingName.text, target);
    return;
  }
  if (ts.isObjectBindingPattern(bindingName)) {
    for (const element of bindingName.elements) {
      const local = bindingIdentifierName(ts, element.name);
      const imported = element.propertyName ? bindingPropertyName(ts, element.propertyName) : local;
      if (!local || !imported) continue;
      addImport(env, local, {
        ...target,
        kind: "named_require",
        imported,
      });
    }
  }
}

/** Add one import target to an environment. */
function addImport(env, localName, target) {
  addTargetBinding(env.importsByLocal, localName, target);
}

/** Return the literal module name from `require()` or `import()`.
 *
 * Called by: CommonJS/dynamic import handling. It supports `await import("x")`.
 */
function importLikeModuleName(ts, initializer) {
  if (!initializer) return "";
  let expr = unwrapExpression(ts, initializer);
  if (ts.isAwaitExpression?.(expr)) expr = unwrapExpression(ts, expr.expression);
  if (!ts.isCallExpression(expr)) return "";
  const callee = exprPath(ts, expr.expression);
  const isDynamicImport = expr.expression.kind === ts.SyntaxKind.ImportKeyword;
  if (callee !== "require" && !isDynamicImport) return "";
  return literalText(ts, expr.arguments?.[0]);
}

/** Produce file candidates for a relative module specifier.
 *
 * Called by: `resolveProjectModule`. TS projects often import `.js` paths that
 * resolve to `.ts` sources in the checkout, so extension swaps are included.
 */
function moduleCandidates(raw) {
  const ext = path.posix.extname(raw);
  const base = ext ? raw.slice(0, -ext.length) : raw;
  const candidates = [];
  if (ext) candidates.push(raw);
  for (const sourceExt of SOURCE_EXTENSIONS) candidates.push(`${base}${sourceExt}`);
  for (const sourceExt of SOURCE_EXTENSIONS) candidates.push(`${raw}/index${sourceExt}`);
  return [...new Set(candidates.map(normalizeRelPath))];
}

/** Normalize paths to POSIX-style relative paths. */
function normalizeRelPath(value) {
  return value.replaceAll("\\", "/").replace(/^\.\//, "");
}

/** Return package directories that contain at least one analyzed file. */
function candidatePackageDirs(root, files) {
  const dirs = new Set();
  for (const file of files) {
    for (let dir = path.posix.dirname(file); dir && dir !== "."; dir = path.posix.dirname(dir)) {
      if (dirs.has(dir)) continue;
      if (fs.existsSync(path.join(root, dir, "package.json"))) dirs.add(dir);
    }
  }
  if (fs.existsSync(path.join(root, "package.json"))) dirs.add(".");
  return [...dirs].sort((a, b) => a.length - b.length);
}

/** Parse a package.json file, returning null for malformed metadata. */
function readPackageJson(root, dir) {
  try {
    return JSON.parse(fs.readFileSync(path.join(root, dir, "package.json"), "utf8"));
  } catch {
    return null;
  }
}

/** Normalize package exports/imports into a subpath -> target strings map. */
function normalizePackageTargets(value) {
  if (!value) return new Map();
  if (typeof value === "string" || Array.isArray(value)) return new Map([[".", packageTargetStrings(value)]]);
  if (typeof value !== "object") return new Map();
  const keys = Object.keys(value);
  if (!keys.some((key) => key === "." || key.startsWith("./") || key.startsWith("#"))) {
    return new Map([[".", packageTargetStrings(value)]]);
  }
  const out = new Map();
  for (const [key, target] of Object.entries(value)) out.set(key, packageTargetStrings(target));
  return out;
}

/** Return every string target nested inside package conditional exports. */
function packageTargetStrings(value) {
  if (typeof value === "string") return [value];
  if (Array.isArray(value)) return value.flatMap(packageTargetStrings);
  if (value && typeof value === "object") return Object.values(value).flatMap(packageTargetStrings);
  return [];
}

/** Keep only package metadata whose targets point at analyzed source files. */
function packageHasResolvableTargets(pkg, fileSet) {
  for (const [key, targets] of [...pkg.exports.entries(), ...pkg.imports.entries()]) {
    for (const target of targets) {
      const sample = key.includes("*") ? target.replaceAll("*", "index") : target;
      if (resolvePackageTargetPath(pkg.dir, sample, fileSet)) return true;
    }
  }
  return false;
}

/** Resolve one package subpath against exact and wildcard target entries. */
function resolvePackageSpecifier(index, pkg, specifier, targetsByKey) {
  for (const target of packageTargetsForSpecifier(specifier, targetsByKey)) {
    const resolved = resolvePackageTargetPath(pkg.dir, target, index.fileSet);
    if (resolved) return resolved;
  }
  return "";
}

/** Return candidate package target strings for a subpath specifier. */
function packageTargetsForSpecifier(specifier, targetsByKey) {
  const exact = targetsByKey.get(specifier);
  if (exact?.length) return exact;
  const out = [];
  for (const [pattern, targets] of targetsByKey.entries()) {
    const star = pattern.indexOf("*");
    if (star === -1) continue;
    const prefix = pattern.slice(0, star);
    const suffix = pattern.slice(star + 1);
    if (!specifier.startsWith(prefix) || !specifier.endsWith(suffix)) continue;
    const capture = specifier.slice(prefix.length, specifier.length - suffix.length);
    out.push(...targets.map((target) => target.replaceAll("*", capture)));
  }
  return out;
}

/** Resolve one package target string to an indexed source file. */
function resolvePackageTargetPath(packageDir, target, fileSet) {
  if (!target.startsWith(".")) return "";
  const raw = normalizeRelPath(path.posix.normalize(path.posix.join(packageDir, target)));
  for (const candidate of moduleCandidates(raw)) {
    if (fileSet.has(candidate)) return candidate;
  }
  return "";
}

/** Return the package metadata that owns a project-relative file. */
function packageForFile(packages, file) {
  let best = null;
  for (const pkg of packages.packagesByDir.values()) {
    if (pkg.dir === "." || file === pkg.dir || file.startsWith(`${pkg.dir}/`)) {
      if (!best || pkg.dir.length > best.dir.length) best = pkg;
    }
  }
  return best;
}

/** Split a package specifier into package name and export subpath. */
function splitPackageSpecifier(moduleName) {
  const parts = moduleName.split("/");
  const scoped = moduleName.startsWith("@");
  const packageName = scoped ? parts.slice(0, 2).join("/") : parts[0];
  const rest = parts.slice(scoped ? 2 : 1).join("/");
  return { packageName, subpath: rest ? `./${rest}` : "." };
}
