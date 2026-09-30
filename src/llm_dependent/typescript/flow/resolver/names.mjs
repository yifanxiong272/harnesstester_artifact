import { exprPath, isFunctionLikeWithBody } from "../syntax.mjs";
import { collectBindingNames } from "../indexing/assignments.mjs";
import { dedupeResolvedNames, sorted } from "./utils.mjs";

/** Resolve a name or dotted expression from one lexical scope.
 *
 * Called by: provider certification, constructor resolution, and call
 * resolution. The root identifier is resolved through lexical envs; the
 * remaining property path is projected through project exports or external
 * full names.
 */
export function resolveExprName(ts, expr, scope, index) {
  const path = exprPath(ts, expr);
  if (!path) return [];
  const parts = path.split(".").filter(Boolean);
  if (!parts.length) return [];
  let roots = resolveName(parts[0], scope, index);
  if (!roots.length) return [];
  const limit = parameterScopeLimit(ts, expr, parts[0], scope, index);
  if (limit !== null) roots = resolveName(parts[0], scope, index, limit);
  if (parts.length === 1) return roots;
  return dedupeResolvedNames(roots.flatMap((root) => extendResolvedName(index, root, parts.slice(1))));
}

/** Resolve one identifier through lexical scopes.
 *
 * Called by: `resolveExprName` and future type/provider seeding. Nearest scope
 * wins; if that scope has multiple possible bindings, all are returned.
 */
export function resolveName(name, scope, index, stopBefore = null) {
  for (let env = index.scopeEnvs.get(scope); env && env.key !== stopBefore; env = index.scopeEnvs.get(env.parent)) {
    const results = [];
    for (const functionId of sorted(env.localFunctions.get(name))) results.push(functionResolvedName(index, functionId));
    for (const classId of sorted(env.localClasses.get(name))) results.push(classResolvedName(index, classId));
    for (const interfaceId of sorted(env.localInterfaces.get(name))) {
      results.push(interfaceResolvedName(index, interfaceId));
    }
    if (results.length) return dedupeResolvedNames(results);

    const importTargets = env.importsByLocal.get(name);
    if (importTargets?.size) {
      return dedupeResolvedNames([...importTargets.values()].flatMap((target) => resolveImportTarget(index, target)));
    }
  }
  return [];
}

/** Stop value-name lookup at a shadowing parameter, including inline callbacks. */
function parameterScopeLimit(ts, expr, name, scope, index) {
  for (let node = expr; node; node = node.parent) {
    if (!isFunctionLikeWithBody(ts, node)) continue;
    const names = new Set();
    for (const param of node.parameters || []) collectBindingNames(ts, param.name, names);
    if (names.has(name)) {
      // Indexed bodies retain their local declarations; inline callbacks share the owner scope.
      return index.functionByNode.get(node)?.parentScope ?? scope;
    }
  }
  return null;
}

/** Return names bound directly in one lexical env.
 *
 * Called by: closure-sensitive ref resolution. If a root is local to the current
 * function, reads should not fall through to enclosing functions.
 */
export function ownScopeNames(scope, index) {
  const env = index.scopeEnvs.get(scope);
  if (!env) return new Set();
  return new Set([
    ...env.importsByLocal.keys(),
    ...env.localFunctions.keys(),
    ...env.localClasses.keys(),
    ...env.localInterfaces.keys(),
    ...env.localTypeAliases.keys(),
  ]);
}

/** Return whether a name is local to the current function.
 *
 * Called by: `directRefsForPath` to decide whether closure refs from enclosing
 * functions should be added for a read path.
 */
export function nameIsLocalToFunction(name, info, index) {
  const declaredNames = info.declaredNames || info.assignedNames || [];
  return (
    info.params.some((param) => param.name === name) ||
    declaredNames.includes(name) ||
    ownScopeNames(info.scope, index).has(name)
  );
}

/** Return all resolved full names for provider-rule matching.
 *
 * Called by: `providers.mjs`. Project-local names and external imports are both
 * returned as strings; source rules normally consume external provider names.
 */
export function fullNamesForExpression(ts, expr, ctx, index) {
  return new Set(resolveExprName(ts, expr, ctx.info.scope, index).map((item) => item.full_name));
}

/** Resolve one import target to project or external names.
 *
 * Called by: `resolveName`. Namespace imports stay namespace-like so property
 * access can be resolved through project exports later.
 */
function resolveImportTarget(index, target) {
  if (target.project_file) {
    if (target.imported === "*") return [namespaceResolvedName(target.module, target.project_file)];
    return resolveProjectExport(index, target.project_file, target.imported);
  }
  if (target.imported === "*") return [namespaceResolvedName(target.module, "")];
  return [externalResolvedName(`${target.module}.${target.imported}`, target.module, target.imported)];
}

/** Extend a resolved root with remaining property parts.
 *
 * Called by: `resolveExprName` after resolving the root identifier.
 */
function extendResolvedName(index, root, rest) {
  if (root.kind === "namespace" && root.project_file) {
    const [exportName, ...tail] = rest;
    const exports = resolveProjectExport(index, root.project_file, exportName);
    if (!tail.length) return exports;
    return exports.map((item) => externalResolvedName(`${item.full_name}.${tail.join(".")}`));
  }
  return [externalResolvedName(`${root.full_name}.${rest.join(".")}`, root.module || "", "")];
}

/** Resolve a named export from an indexed project file.
 *
 * Called by: import and namespace resolution. When no indexed export exists,
 * an external name is returned so provider matching can still use the full path.
 */
function resolveProjectExport(index, file, exportedName) {
  const exportTargets = index.exportsByFile.get(file)?.get(exportedName);
  const out = [];
  for (const target of exportTargets?.values() || []) {
    if (target.kind === "function") out.push(functionResolvedName(index, target.key));
    if (target.kind === "class") out.push(classResolvedName(index, target.key));
    if (target.kind === "interface") out.push(interfaceResolvedName(index, target.key));
  }
  if (out.length) return out;

  const moduleEnv = index.scopeEnvs.get(index.moduleScopes.get(file));
  for (const functionId of sorted(moduleEnv?.localFunctions.get(exportedName))) {
    out.push(functionResolvedName(index, functionId));
  }
  for (const classId of sorted(moduleEnv?.localClasses.get(exportedName))) {
    out.push(classResolvedName(index, classId));
  }
  for (const interfaceId of sorted(moduleEnv?.localInterfaces.get(exportedName))) {
    out.push(interfaceResolvedName(index, interfaceId));
  }
  return out.length ? out : [externalResolvedName(`${file}.${exportedName}`)];
}

/** Build a resolved function name object. */
function functionResolvedName(index, functionId) {
  const info = index.functions.get(functionId);
  const fullName = info ? `${info.file}.${info.qualname}` : functionId;
  return { kind: "function", full_name: fullName, function: functionId, class: "" };
}

/** Build a resolved class name object. */
function classResolvedName(index, classId) {
  const info = index.classes.get(classId);
  const fullName = info ? `${info.file}.${info.qualname}` : classId;
  return { kind: "class", full_name: fullName, function: "", class: classId };
}

/** Build a resolved interface name object. */
function interfaceResolvedName(index, interfaceId) {
  const info = index.interfaces.get(interfaceId);
  const fullName = info ? `${info.file}.${info.qualname}` : interfaceId;
  return { kind: "interface", full_name: fullName, function: "", class: "", interface: interfaceId };
}

/** Build an external resolved name object. */
function externalResolvedName(fullName, module = "", imported = "") {
  return { kind: "external", full_name: fullName, module, imported, function: "", class: "" };
}

/** Build a namespace resolved name object. */
function namespaceResolvedName(module, projectFile) {
  return { kind: "namespace", full_name: module, module, project_file: projectFile, function: "", class: "" };
}
