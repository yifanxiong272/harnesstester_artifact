import { spanKey } from "../models.mjs";

/** Build function-level control-dependence regions from recorded call facts.
 *
 * Called by: `FlowAnalyzer.analyzeProject` after fixed-point convergence.
 * `block_only` emits no function-level regions. Direct mode includes callees
 * called under tainted control with no tainted argument. Recursive mode follows
 * ordinary resolved project-local calls from those selected callees.
 */
export function buildControlRegions({ facts, index, mode }) {
  if (mode === "block_only") return [];

  const selected = new Map();
  const queue = [];
  const callerDataSpans = callerDataSpanKeys(facts);
  for (const fact of [...facts.controlCalls.values()].sort(compareControlCalls)) {
    if (callerDataSpans.has(spanKey(fact.span))) continue;
    if (selected.has(fact.callee)) continue;
    selected.set(fact.callee, fact.control_span);
    queue.push(fact.callee);
  }

  if (mode === "control-dependence-recursive") {
    addRecursiveControlCallees({ facts, selected, queue });
  }

  return [...selected.entries()]
    .filter(([functionId]) => index.functions.has(functionId))
    .map(([functionId, controlSpan]) => ({
      info: index.functions.get(functionId),
      control_span: controlSpan,
    }));
}

/** Return call-site spans already represented by direct caller data flow. */
function callerDataSpanKeys(facts) {
  const out = new Set();
  for (const edge of facts.dataEdges.values()) {
    if (edge.dependence_type === "caller") out.add(spanKey(edge.span));
  }
  return out;
}

/** Expand selected control-dependent functions through project-local calls. */
function addRecursiveControlCallees({ facts, selected, queue }) {
  const outgoing = new Map();
  for (const fact of facts.calls.values()) {
    if (!outgoing.has(fact.caller)) outgoing.set(fact.caller, new Set());
    outgoing.get(fact.caller).add(fact.callee);
  }
  for (let cursor = 0; cursor < queue.length; cursor += 1) {
    const caller = queue[cursor];
    for (const callee of [...(outgoing.get(caller) || [])].sort()) {
      if (selected.has(callee)) continue;
      selected.set(callee, selected.get(caller));
      queue.push(callee);
    }
  }
}

/** Sort recorded control-call facts deterministically. */
function compareControlCalls(left, right) {
  return (
    left.callee.localeCompare(right.callee) ||
    left.control_span.filepath.localeCompare(right.control_span.filepath) ||
    left.control_span.start_line - right.control_span.start_line ||
    left.control_span.end_line - right.control_span.end_line
  );
}
