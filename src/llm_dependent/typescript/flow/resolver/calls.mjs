import { unwrapExpression } from "../source_locator.mjs";
import { constructorTargets, methodTargets } from "./classes.mjs";
import { resolveExprName } from "./names.mjs";
import { refsForReadExpr, receiverClasses } from "./refs.mjs";
import { callTarget, dedupeCallTargets, literalString, sorted } from "./utils.mjs";

/** Resolve class construction for a call or new expression.
 *
 * Called by: provider/type seeding. For TypeScript, constructor calls do not
 * need Python-style positional offsets because `this` is implicit.
 */
export function resolveConstructor(ts, call, ctx, index) {
  const callee = call.expression;
  const out = new Set();
  for (const resolved of resolveExprName(ts, callee, ctx.info.scope, index)) {
    if (resolved.class) out.add(resolved.class);
  }
  return out;
}

/** Resolve one call/new expression to project-local callable targets.
 *
 * Called by: flow transfer for return propagation, argument-to-parameter flow,
 * and control-dependent callee expansion. It combines callable aliases,
 * lexical/imported functions, constructors, and typed receiver methods.
 */
export function resolveCall(ts, call, ctx, facts, index) {
  if (!call || (!ts.isCallExpression(call) && !ts.isNewExpression(call))) return [];
  const callee = call.expression;
  const targets = [];

  for (const ref of refsForReadExpr(ts, callee, ctx, facts, index, { includePrefixes: false })) {
    for (const alias of sorted(facts.aliasOf(ref))) targets.push(callTarget(alias));
  }

  for (const resolved of resolveExprName(ts, callee, ctx.info.scope, index)) {
    if (resolved.function) targets.push(callTarget(resolved.function));
    if (resolved.class) targets.push(...constructorTargets(resolved.class, index));
  }

  const receiver = callReceiver(ts, callee);
  const method = callMemberName(ts, callee);
  if (receiver && method) {
    for (const classId of receiverClasses(ts, receiver, ctx, facts, index)) {
      targets.push(...methodTargets(classId, method, index));
    }
  }

  return dedupeCallTargets(targets);
}

/** Return the receiver expression from a member call. */
function callReceiver(ts, callee) {
  const expr = unwrapExpression(ts, callee);
  if (ts.isPropertyAccessExpression(expr) || ts.isElementAccessExpression(expr)) return expr.expression;
  return null;
}

/** Return the member name from a property/element call expression. */
function callMemberName(ts, callee) {
  const expr = unwrapExpression(ts, callee);
  if (ts.isPropertyAccessExpression(expr)) return expr.name.text;
  if (ts.isElementAccessExpression(expr)) return literalString(ts, expr.argumentExpression);
  return "";
}
