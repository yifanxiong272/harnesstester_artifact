import { classFieldRef, localRef, moduleRef } from "../models.mjs";
import { exprPath } from "../syntax.mjs";
import { unwrapExpression } from "../source_locator.mjs";
import { classesForType, classContextKey, transitiveBases } from "./classes.mjs";
import { nameIsLocalToFunction } from "./names.mjs";
import { addRef, addRefs, dedupeRefs, sorted } from "./utils.mjs";

/** Return fact refs that may describe a read expression.
 *
 * Called by: provider certification and flow transfer. Prefix mode is what
 * makes `response.choices[0].message` observe taint already stored on
 * `response`.
 */
export function refsForReadExpr(ts, expr, ctx, facts, index, options = {}) {
  const path = exprPath(ts, expr);
  if (!path) return [];
  return refsForPath(path, ctx, facts, index, options);
}

/** Return fact refs for a dotted path in the current function context.
 *
 * Called by: expression reads, provider checks, and target resolution. It emits
 * local refs, `this` class-field refs, and typed receiver class-field refs.
 */
export function refsForPath(path, ctx, facts, index, options = {}) {
  const includePrefixes = options.includePrefixes !== false;
  const parts = path.split(".").filter(Boolean);
  const paths = includePrefixes ? parts.map((_, idx) => parts.slice(0, idx + 1).join(".")) : [path];
  const out = [];
  const seen = new Set();

  for (const currentPath of paths) {
    addRefs(out, seen, directRefsForPath(currentPath, ctx, index));
    addTypedFieldRefs(out, seen, currentPath, ctx, facts, index);
  }

  return out;
}

/** Return direct local or `this` refs without following type facts.
 *
 * Called by: `refsForPath` and `classesForPath`. Closure refs are added only
 * when the root name is not bound in the current function.
 */
export function directRefsForPath(path, ctx, index) {
  const parts = path.split(".").filter(Boolean);
  if (!parts.length) return [];
  const root = parts[0];
  const suffix = parts.slice(1).join(".");
  const info = ctx.info;
  const classId = classContextKey(info);

  if (info.kind === "module") return [moduleRef(info.file, path)];

  if ((root === "this" || root === "super") && suffix && classId) {
    return [classId, ...sorted(transitiveBases(classId, index))].map((candidate) =>
      classFieldRef(candidate, suffix),
    );
  }

  const refs = [localRef(info.key, path)];
  if (!nameIsLocalToFunction(root, info, index)) {
    let enclosingHasBinding = false;
    for (const enclosing of [...(info.enclosingFunctions || [])].reverse()) {
      refs.push(localRef(enclosing, path));
      const enclosingInfo = index.functions.get(enclosing);
      if (enclosingInfo && nameIsLocalToFunction(root, enclosingInfo, index)) enclosingHasBinding = true;
    }
    if (!enclosingHasBinding && root !== "this" && root !== "super") {
      refs.push(moduleRef(info.file, path));
    }
  }
  return refs;
}

/** Resolve known class types for a path.
 *
 * Called by: receiver and class-field resolution. The recursion lets `obj.a.b`
 * observe type facts from both `obj` and `Class.a`.
 */
export function classesForPath(path, ctx, facts, index, memo = new Map()) {
  if (memo.has(path)) return new Set(memo.get(path));
  const out = new Set();
  if ((path === "this" || path === "super") && classContextKey(ctx.info)) {
    out.add(classContextKey(ctx.info));
  }
  for (const ref of directRefsForPath(path, ctx, index)) {
    for (const typeId of facts.typeOf(ref)) {
      for (const classId of classesForType(typeId, index)) out.add(classId);
    }
  }

  const parts = path.split(".").filter(Boolean);
  for (let idx = 1; idx < parts.length; idx += 1) {
    const prefix = parts.slice(0, idx).join(".");
    const suffix = parts.slice(idx).join(".");
    for (const classId of classesForPath(prefix, ctx, facts, index, memo)) {
      for (const typeId of facts.typeOf(classFieldRef(classId, suffix))) {
        for (const nested of classesForType(typeId, index)) out.add(nested);
      }
    }
  }

  memo.set(path, out);
  return new Set(out);
}

/** Return known receiver classes for a method-call receiver expression.
 *
 * Called by: call resolution and event/channel logic.
 */
export function receiverClasses(ts, expr, ctx, facts, index) {
  const path = exprPath(ts, expr);
  if (!path) return new Set();
  return classesForPath(path, ctx, facts, index);
}

/** Convert an assignment target into refs that should receive facts.
 *
 * Called by: assignments, loop headers, and callback parameter seeding.
 */
export function targetRefs(ts, target, ctx, facts, index) {
  const node = unwrapExpression(ts, target);
  if (!node) return [];

  if (ts.isIdentifier(node)) return directTargetRefsForPath(node.text, ctx, index);
  if (ts.isObjectBindingPattern?.(node) || ts.isArrayBindingPattern?.(node)) {
    return bindingPatternRefs(ts, node, ctx, facts, index);
  }
  if (ts.isObjectLiteralExpression?.(node) || ts.isArrayLiteralExpression?.(node)) {
    return destructuringAssignmentRefs(ts, node, ctx, facts, index);
  }

  const path = exprPath(ts, node);
  if (!path) return [];
  const refs = directTargetRefsForPath(path, ctx, index);
  addTypedTargetRefs(refs, path, ctx, facts, index);
  return dedupeRefs(refs);
}

/** Add class-field refs reached through typed prefixes of one read path. */
function addTypedFieldRefs(out, seen, currentPath, ctx, facts, index) {
  const parts = currentPath.split(".");
  for (let idx = 1; idx < parts.length; idx += 1) {
    const prefix = parts.slice(0, idx).join(".");
    const suffix = parts.slice(idx).join(".");
    for (const classId of classesForPath(prefix, ctx, facts, index)) {
      addRef(out, seen, classFieldRef(classId, suffix));
    }
  }
}

/** Return direct write refs for a dotted target path.
 *
 * Called by: assignment and container-mutation target resolution. Writes follow
 * TS lexical scope: if a nested callback writes `out.push(x)` and `out` is
 * declared by an enclosing function, the write updates the enclosing local ref
 * rather than creating an unrelated callback-local value.
 */
function directTargetRefsForPath(path, ctx, index) {
  const parts = path.split(".").filter(Boolean);
  if (!parts.length) return [];
  if (ctx.info.kind === "module") return [moduleRef(ctx.info.file, path)];
  const classId = classContextKey(ctx.info);
  if ((parts[0] === "this" || parts[0] === "super") && parts.length > 1 && classId) {
    return [classFieldRef(classId, parts.slice(1).join("."))];
  }
  const root = parts[0];
  if (nameIsLocalToFunction(root, ctx.info, index)) return [localRef(ctx.info.key, path)];

  const refs = [];
  let enclosingHasBinding = false;
  for (const enclosing of [...(ctx.info.enclosingFunctions || [])].reverse()) {
    refs.push(localRef(enclosing, path));
    const enclosingInfo = index.functions.get(enclosing);
    if (enclosingInfo && nameIsLocalToFunction(root, enclosingInfo, index)) enclosingHasBinding = true;
  }
  if (!enclosingHasBinding && root !== "this" && root !== "super") refs.push(moduleRef(ctx.info.file, path));
  return refs.length ? refs : [localRef(ctx.info.key, path)];
}

/** Add class-field write refs reached through typed receiver prefixes. */
function addTypedTargetRefs(refs, path, ctx, facts, index) {
  const parts = path.split(".").filter(Boolean);
  if (parts.length <= 1) return;
  const base = parts.slice(0, -1).join(".");
  const suffix = parts[parts.length - 1];
  for (const receiverClass of classesForPath(base, ctx, facts, index)) {
    refs.push(classFieldRef(receiverClass, suffix));
  }
}

/** Return refs from a binding pattern.
 *
 * Called by: `targetRefs` for parameters and variable declarations.
 */
function bindingPatternRefs(ts, pattern, ctx, facts, index) {
  const refs = [];
  for (const element of pattern.elements || []) {
    if (!ts.isBindingElement?.(element)) continue;
    refs.push(...targetRefs(ts, element.name, ctx, facts, index));
  }
  return dedupeRefs(refs);
}

/** Return refs from destructuring assignment syntax.
 *
 * Called by: `targetRefs` for assignment targets such as `({ x } = value)`.
 */
function destructuringAssignmentRefs(ts, pattern, ctx, facts, index) {
  const refs = [];
  for (const element of pattern.elements || pattern.properties || []) {
    if (ts.isSpreadElement?.(element)) refs.push(...targetRefs(ts, element.expression, ctx, facts, index));
    else if (ts.isShorthandPropertyAssignment?.(element)) refs.push(localRef(ctx.info.key, element.name.text));
    else if (ts.isPropertyAssignment?.(element)) refs.push(...targetRefs(ts, element.initializer, ctx, facts, index));
    else if (element.name) refs.push(...targetRefs(ts, element.name, ctx, facts, index));
  }
  return dedupeRefs(refs);
}
