import { refKey } from "../models.mjs";

/** Deduplicated dirty-function queue drained in the supplied project order. */
export class DirtyFunctionQueue {
  constructor(functionOrder) {
    this.functionRank = new Map(
      functionOrder.map((info, index) => [info.key, index]),
    );
    this.pending = new Set();
  }

  /** Add one function id if it belongs to the indexed project. */
  add(functionId) {
    if (!this.functionRank.has(functionId)) return;
    this.pending.add(functionId);
  }

  /** Return pending function ids in project order and clear the queue. */
  drain() {
    const out = [...this.pending].sort(
      (left, right) =>
        this.functionRank.get(left) - this.functionRank.get(right),
    );
    this.pending.clear();
    return out;
  }
}

/** Enqueue functions affected by changed value refs.
 *
 * Called by: `FlowAnalyzer` after every class seeding/function analysis step.
 * Local and class-field ref changes re-run only functions that previously read
 * that exact ref. Module ref changes re-run functions that previously read the
 * module path. Return ref changes re-run known callers. This keeps the analysis
 * conservative at the ref abstraction level without treating a class, module, or
 * function as dirty just because an unrelated value changed.
 */
export function enqueueChangedRefs({
  queue,
  refs,
  callersByCallee,
  localRefReaders,
  classFieldReaders,
  moduleRefReaders,
  descendantRefReaders,
  ignoreLocalFunction = null,
}) {
  for (const item of refs) {
    const ref = item.ref || item;
    if (ref.kind === "local") {
      enqueueRefReaders(
        queue,
        localRefReaders,
        ref,
        ignoreLocalFunction,
      );
    } else if (ref.kind === "return") {
      enqueueCallers(queue, callersByCallee, ref.function);
    } else if (ref.kind === "class_field") {
      enqueueRefReaders(queue, classFieldReaders, ref);
    } else if (ref.kind === "module") {
      enqueueRefReaders(queue, moduleRefReaders, ref);
    }
    enqueueAncestorReaders({
      queue,
      ref,
      descendantRefReaders,
      ignoreLocalFunction,
    });
  }
}

/** Register one call edge and return whether the edge is new.
 *
 * Called by: `FlowAnalyzer.handleCall`. The caller map is used later when a
 * callee return fact changes and callers need to be re-analyzed.
 */
export function recordCallEdge({ facts, callersByCallee, fact }) {
  const added = facts.addCall(fact);
  if (!added) return false;
  if (!callersByCallee.has(fact.callee))
    callersByCallee.set(fact.callee, new Set());
  callersByCallee.get(fact.callee).add(fact.caller);
  return true;
}

/** Enqueue every known caller for a callee function id. */
function enqueueCallers(queue, callersByCallee, callee) {
  for (const caller of callersByCallee.get(callee) || []) queue.add(caller);
}

/** Enqueue prior readers except the function currently being analyzed. */
function enqueueRefReaders(queue, readersByRef, ref, ignoreFunction = null) {
  for (const functionId of readersByRef.get(refKey(ref)) || []) {
    if (functionId !== ignoreFunction) queue.add(functionId);
  }
}

/** Enqueue readers of parent container refs for a changed child ref.
 *
 * Called by: `enqueueChangedRefs`. How it is called: if a later pass learns
 * facts for `opts.onDelta`, any function that previously read `opts` for an
 * object spread must run again so the new child field can be copied.
 */
function enqueueAncestorReaders({
  queue,
  ref,
  descendantRefReaders,
  ignoreLocalFunction,
}) {
  for (const ancestor of ancestorRefs(ref)) {
    enqueueRefReaders(
      queue,
      descendantRefReaders,
      ancestor,
      ignoreLocalFunction,
    );
  }
}

/** Return prefix refs for a concrete child ref. */
function ancestorRefs(ref) {
  if (!ref || !("path" in ref)) return [];
  const parts = ref.path.split(".").filter(Boolean);
  const out = [];
  for (let index = 1; index < parts.length; index += 1) {
    const path = parts.slice(0, index).join(".");
    if (ref.kind === "local")
      out.push({ kind: "local", function: ref.function, path });
    else if (ref.kind === "class_field")
      out.push({ kind: "class_field", class: ref.class, path });
    else if (ref.kind === "module")
      out.push({ kind: "module", file: ref.file, path });
  }
  return out;
}
