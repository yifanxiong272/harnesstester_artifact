import { unwrapExpression } from "../source_locator.mjs";

/** Read a static string literal; dynamic expressions return an empty string. */
export function literalString(ts, expr) {
  const node = unwrapExpression(ts, expr);
  if (!node) return "";
  if (ts.isStringLiteralLike?.(node) || ts.isNoSubstitutionTemplateLiteral?.(node)) return node.text;
  return "";
}

/** Pair an indexed function with its current control origin. */
export function functionContext(info, controlOrigin = null) {
  return { info, control_origin: controlOrigin };
}

/** Build a local call target; TS has no explicit self parameter. */
export function callTarget(functionId, positionalOffset = 0) {
  return { key: functionId, positional_offset: positionalOffset };
}

/** Sort set-like values for deterministic analysis output. */
export function sorted(values) {
  return [...(values || [])].sort();
}

/** Append structurally distinct refs in encounter order. */
export function addRefs(out, seen, refs) {
  for (const ref of refs) addRef(out, seen, ref);
}

/** Add one ref to an output list while preserving order. */
export function addRef(out, seen, ref) {
  const key = JSON.stringify(ref);
  if (seen.has(key)) return;
  seen.add(key);
  out.push(ref);
}

/** Deduplicate refs by serialized structure, preserving first-seen order. */
export function dedupeRefs(refs) {
  return uniqueBy(refs, JSON.stringify);
}

/** Deduplicate resolved names while preserving first-seen order. */
export function dedupeResolvedNames(items) {
  return uniqueBy(items, item => `${item.kind}:${item.full_name}:${item.function || ""}:${item.class || ""}`);
}

/** Deduplicate call targets while preserving first-seen order. */
export function dedupeCallTargets(targets) {
  return uniqueBy(targets, target => `${target.key}:${target.positional_offset}`);
}

/** Preserve the first value for each structural key, in encounter order. */
export function uniqueBy(items, keyOf) {
  const out = [];
  const seen = new Set();
  for (const item of items) {
    const key = keyOf(item);
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(item);
  }
  return out;
}

/** Walk transitive class edges from one class id. */
export function transitiveClassWalk(classId, edgeMap) {
  const out = new Set();
  const queue = [...(edgeMap.get(classId) || [])];
  while (queue.length) {
    const item = queue.pop();
    if (!item || out.has(item)) continue;
    out.add(item);
    queue.push(...(edgeMap.get(item) || []));
  }
  return out;
}
