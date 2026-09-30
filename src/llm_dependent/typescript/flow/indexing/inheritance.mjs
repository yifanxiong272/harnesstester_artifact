/** Resolve class inheritance links after exports/imports are known.
 *
 * Called by: `buildProjectIndex` after export finalization. Resolver uses these
 * links to include inherited methods without provider- or project-specific
 * special cases.
 */
export function finalizeClassInheritance(index) {
  for (const classInfo of index.classes.values()) {
    const baseKeys = new Set();
    for (const base of classInfo.bases) {
      for (const resolved of resolveClassPath(index, classInfo.scope, base.path)) {
        baseKeys.add(resolved);
        base.resolved_class_keys.push(resolved);
      }
    }
    index.classBases.set(classInfo.key, baseKeys);
    for (const baseKey of baseKeys) {
      if (!index.classSubclasses.has(baseKey)) index.classSubclasses.set(baseKey, new Set());
      index.classSubclasses.get(baseKey).add(classInfo.key);
    }
    for (const implemented of classInfo.interfaces || []) {
      for (const interfaceKey of resolveInterfacePath(index, classInfo.scope, implemented.path)) {
        implemented.resolved_interface_keys.push(interfaceKey);
        if (!index.interfaceImplementers.has(interfaceKey)) index.interfaceImplementers.set(interfaceKey, new Set());
        index.interfaceImplementers.get(interfaceKey).add(classInfo.key);
      }
    }
  }
}

/** Resolve a class path from one lexical scope.
 *
 * Called by: class inheritance finalization and resolver code. It handles local
 * classes, named/default imports, and namespace imports from indexed files.
 */
export function resolveClassPath(index, startingScopeKey, classPath) {
  if (!classPath) return new Set();
  const segments = classPath.split(".").filter(Boolean);
  if (segments.length === 0) return new Set();
  const first = segments[0];
  const out = new Set();

  for (let env = index.scopeEnvs.get(startingScopeKey); env; env = index.scopeEnvs.get(env.parent)) {
    if (segments.length === 1) {
      for (const localClass of env.localClasses.get(first) || []) out.add(localClass);
    }

    const imports = env.importsByLocal.get(first);
    for (const target of imports?.values() || []) {
      addImportedClassTargets(index, out, target, segments);
    }
  }

  return out;
}

/** Resolve an interface path from one lexical scope.
 *
 * Called by: interface-implementation finalization and type-annotation
 * seeding. Only explicit local/imported interfaces are resolved; structural
 * matching is intentionally out of scope for this static may-analysis pass.
 */
export function resolveInterfacePath(index, startingScopeKey, interfacePath, seenAliases = new Set()) {
  if (!interfacePath) return new Set();
  const cacheKey = seenAliases.size === 0 ? `${startingScopeKey}:${interfacePath}` : "";
  if (cacheKey && index.interfacePathCache?.has(cacheKey)) {
    return new Set(index.interfacePathCache.get(cacheKey));
  }
  const segments = interfacePath.split(".").filter(Boolean);
  if (segments.length === 0) return new Set();
  const first = segments[0];
  const out = new Set();

  for (let env = index.scopeEnvs.get(startingScopeKey); env; env = index.scopeEnvs.get(env.parent)) {
    if (segments.length === 1) {
      for (const localInterface of env.localInterfaces.get(first) || []) out.add(localInterface);
      for (const aliasId of env.localTypeAliases.get(first) || []) {
        addAliasInterfaces(index, out, aliasId, seenAliases);
      }
    }

    const imports = env.importsByLocal.get(first);
    for (const target of imports?.values() || []) {
      addImportedInterfaceTargets(index, out, target, segments, seenAliases);
    }
  }

  if (cacheKey) index.interfacePathCache?.set(cacheKey, new Set(out));
  return out;
}

/** Add class targets reachable through an import target.
 *
 * Called by: `resolveClassPath`.
 */
function addImportedClassTargets(index, out, target, segments) {
  if (!target.project_file) return;
  let exportName = "";
  if (target.imported === "*") {
    exportName = segments.length > 1 ? segments[1] : "";
  } else if (segments.length === 1) {
    exportName = target.imported;
  }
  if (!exportName) return;

  const exports = index.exportsByFile.get(target.project_file);
  for (const exportedTarget of exports?.get(exportName)?.values() || []) {
    if (exportedTarget.kind === "class") out.add(exportedTarget.key);
  }
}

/** Add interface targets reachable through an import target. */
function addImportedInterfaceTargets(index, out, target, segments, seenAliases) {
  if (!target.project_file) return;
  let exportName = "";
  if (target.imported === "*") {
    exportName = segments.length > 1 ? segments[1] : "";
  } else if (segments.length === 1) {
    exportName = target.imported;
  }
  if (!exportName) return;

  const exports = index.exportsByFile.get(target.project_file);
  for (const exportedTarget of exports?.get(exportName)?.values() || []) {
    if (exportedTarget.kind === "interface") out.add(exportedTarget.key);
    if (exportedTarget.kind === "type_alias") addAliasInterfaces(index, out, exportedTarget.key, seenAliases);
  }
}

/** Expand one type alias into real project-local interfaces.
 *
 * Called by: `resolveInterfacePath`. This intentionally stays syntactic: it
 * follows type names in the alias RHS and lets normal lexical/import resolution
 * decide which of those names are project interfaces or more aliases.
 */
function addAliasInterfaces(index, out, aliasId, seenAliases) {
  if (seenAliases.has(aliasId)) return;
  seenAliases.add(aliasId);
  const info = index.typeAliases.get(aliasId);
  if (!info) return;
  for (const name of typeNamesInAnnotation(info.annotation)) {
    for (const interfaceId of resolveInterfacePath(index, info.scope, name, seenAliases)) {
      out.add(interfaceId);
    }
  }
}

/** Extract candidate type identifiers from an annotation string. */
function typeNamesInAnnotation(annotation) {
  const out = new Set();
  for (const match of String(annotation || "").matchAll(/\b[A-Za-z_$][A-Za-z0-9_$]*\b/g)) {
    const name = match[0];
    if (!TYPE_NAME_STOP_WORDS.has(name)) out.add(name);
  }
  return out;
}

const TYPE_NAME_STOP_WORDS = new Set([
  "Array",
  "Promise",
  "Record",
  "Readonly",
  "ReadonlyArray",
  "Partial",
  "Required",
  "Pick",
  "Omit",
  "Exclude",
  "Extract",
  "NonNullable",
  "ReturnType",
  "Parameters",
  "ConstructorParameters",
  "InstanceType",
  "Awaited",
  "keyof",
  "typeof",
  "infer",
  "extends",
  "readonly",
  "string",
  "number",
  "boolean",
  "bigint",
  "symbol",
  "object",
  "unknown",
  "never",
  "void",
  "null",
  "undefined",
  "true",
  "false",
]);
