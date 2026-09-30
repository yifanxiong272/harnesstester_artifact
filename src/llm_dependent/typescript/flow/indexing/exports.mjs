import { unwrapExpression } from "../source_locator.mjs";
import { addTargetBinding, targetKey } from "./bindings.mjs";
import { literalText, resolveProjectModule } from "./imports.mjs";
import { hasModifier } from "./names.mjs";

/** Record named/default export declarations.
 *
 * Called by: file visitor. Resolution to concrete class/function ids is delayed
 * until every local declaration has been indexed.
 */
export function recordExportDeclaration(ts, index, file, env, node) {
  const moduleName = literalText(ts, node.moduleSpecifier);
  const projectFile = moduleName ? resolveProjectModule(index, file.rel, moduleName) : "";
  if (!node.exportClause) {
    if (moduleName) {
      env.reexports.push({
        exported: "*",
        imported: "*",
        module: moduleName,
        project_file: projectFile,
      });
    }
    return;
  }
  if (!ts.isNamedExports(node.exportClause)) return;
  for (const element of node.exportClause.elements) {
    const exported = element.name.text;
    const local = element.propertyName?.text || element.name.text;
    if (moduleName) {
      env.reexports.push({
        exported,
        imported: local,
        module: moduleName,
        project_file: projectFile,
      });
    } else {
      addTargetBinding(env.exports, exported, { kind: "local", local });
    }
  }
}

/** Record `export default x` when `x` is an identifier.
 *
 * Called by: file/function visitors. Function/class default-export expressions
 * are also exported when their stable record is registered.
 */
export function recordExportAssignment(ts, env, node) {
  const expr = unwrapExpression(ts, node.expression);
  if (ts.isIdentifier(expr)) addTargetBinding(env.exports, "default", { kind: "local", local: expr.text });
}

/** Export a declaration when it carries `export` or `default` modifiers.
 *
 * Called by: function/class registration.
 */
export function maybeExportDeclaredSymbol(ts, env, node, declaredName, target) {
  if (!hasModifier(node, ts.SyntaxKind.ExportKeyword) && !hasModifier(node, ts.SyntaxKind.DefaultKeyword)) return;
  const exportName = hasModifier(node, ts.SyntaxKind.DefaultKeyword) ? "default" : declaredName;
  addTargetBinding(env.exports, exportName, target);
}

/** Resolve local and re-export targets into `index.exportsByFile`.
 *
 * Called by: `buildProjectIndex` after every file has been visited. The fixed
 * loop handles simple re-export chains without a separate graph pass.
 */
export function finalizeExports(index) {
  for (const file of index.files.keys()) index.exportsByFile.set(file, new Map());

  let changed = true;
  while (changed) {
    changed = false;
    for (const [file, scopeKeyValue] of index.moduleScopes.entries()) {
      const env = index.scopeEnvs.get(scopeKeyValue);
      const fileExports = index.exportsByFile.get(file);
      for (const [exported, targetMap] of env.exports.entries()) {
        for (const target of targetMap.values()) {
          changed = addResolvedExportTargets(env, fileExports, exported, target) || changed;
        }
      }
      for (const reexport of env.reexports) {
        changed = addReexportTargets(index, fileExports, reexport) || changed;
      }
    }
  }
}

/** Add concrete exports for a direct export target.
 *
 * Called by: `finalizeExports`. Local named exports are resolved against the
 * module env's local functions/classes; direct targets are copied through.
 */
function addResolvedExportTargets(env, fileExports, exported, target) {
  if (target.kind === "function" || target.kind === "class" || target.kind === "interface" || target.kind === "type_alias") {
    return addExportTarget(fileExports, exported, target);
  }
  if (target.kind !== "local") return false;

  let changed = false;
  for (const functionId of env.localFunctions.get(target.local) || []) {
    changed = addExportTarget(fileExports, exported, { kind: "function", key: functionId }) || changed;
  }
  for (const classId of env.localClasses.get(target.local) || []) {
    changed = addExportTarget(fileExports, exported, { kind: "class", key: classId }) || changed;
  }
  for (const interfaceId of env.localInterfaces.get(target.local) || []) {
    changed = addExportTarget(fileExports, exported, { kind: "interface", key: interfaceId }) || changed;
  }
  for (const aliasId of env.localTypeAliases.get(target.local) || []) {
    changed = addExportTarget(fileExports, exported, { kind: "type_alias", key: aliasId }) || changed;
  }
  return changed;
}

/** Propagate one re-export when the source file is indexed. */
function addReexportTargets(index, fileExports, reexport) {
  if (!reexport.project_file) return false;
  const sourceExports = index.exportsByFile.get(reexport.project_file);
  if (reexport.imported === "*" && reexport.exported === "*") {
    let changed = false;
    for (const [exported, sourceTargets] of sourceExports || []) {
      if (exported === "default") continue;
      for (const sourceTarget of sourceTargets.values()) {
        changed = addExportTarget(fileExports, exported, sourceTarget) || changed;
      }
    }
    return changed;
  }
  const sourceTargets = sourceExports?.get(reexport.imported);
  let changed = false;
  for (const sourceTarget of sourceTargets?.values?.() || sourceTargets || []) {
    changed = addExportTarget(fileExports, reexport.exported, sourceTarget) || changed;
  }
  return changed;
}

/** Add one concrete export target.
 *
 * Called by: export finalization and re-export propagation.
 */
function addExportTarget(fileExports, exported, target) {
  if (!fileExports.has(exported)) fileExports.set(exported, new Map());
  const targetMap = fileExports.get(exported);
  const key = targetKey(target);
  if (targetMap.has(key)) return false;
  targetMap.set(key, target);
  return true;
}
