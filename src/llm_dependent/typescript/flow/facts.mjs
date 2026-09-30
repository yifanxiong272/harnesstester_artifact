import {
  callFactKey,
  controlCallFactKey,
  flowEdge,
  paramDepKey,
  refKey,
  compareSpans,
  spanKey,
  returnRef,
} from "./models.mjs";

function setValues(values = []) {
  return values instanceof Set ? values : new Set(values);
}

/** Build a structural key for values stored inside fact sets. */
function factValueKey(value) {
  if (
    value &&
    typeof value === "object" &&
    value.filepath &&
    value.start_line !== undefined &&
    value.end_line !== undefined
  ) {
    return `span:${spanKey(value)}`;
  }
  if (value && typeof value === "object") return `object:${JSON.stringify(value)}`;
  return `${typeof value}:${value}`;
}

/** Add a structurally new fact, preserving its first representative. */
function addFactValue(values, value) {
  const key = factValueKey(value);
  for (const current of values) {
    if (factValueKey(current) === key) return false;
  }
  values.add(value);
  return true;
}

/** Add or merge one edge in a fact-store edge map. */
function addEdge(store, span, origins, dependenceType) {
  const destinationKey = spanKey(span);
  let sourceSpans = setValues(origins);
  for (const sourceSpan of sourceSpans) {
    if (spanKey(sourceSpan) !== destinationKey) continue;
    const filtered = new Set();
    for (const candidate of sourceSpans) {
      if (spanKey(candidate) !== destinationKey) filtered.add(candidate);
    }
    sourceSpans = filtered;
    break;
  }
  if (!sourceSpans.size) return false;
  const key = dataEdgeKey(span, dependenceType);
  if (!store.has(key)) {
    const edge = flowEdge(span, sourceSpans, dependenceType);
    edge.source_keys = new Set(edge.source_spans.map(spanKey));
    store.set(key, edge);
    return true;
  }

  const edge = store.get(key);
  if (!edge.source_keys) edge.source_keys = new Set(edge.source_spans.map(spanKey));
  let changed = false;
  for (const sourceSpan of sourceSpans) {
    const sourceKey = spanKey(sourceSpan);
    if (edge.source_keys.has(sourceKey)) continue;
    edge.source_keys.add(sourceKey);
    edge.source_spans.push(sourceSpan);
    changed = true;
  }
  if (!changed) return false;
  edge.source_spans.sort(compareSpans);
  return true;
}

/** Monotonic source, value, call, and edge facts for fixed-point analysis.
 * Changed refs schedule their readers; convergence means no affected reader remains.
 */
export class FactStore {
  constructor() {
    this.sources = new Map();
    this.taints = new Map();
    this.paramTaints = new Map();
    this.providers = new Map();
    this.types = new Map();
    this.aliases = new Map();
    this.paramDeps = new Map();
    this.returnParamDeps = new Map();
    this.strings = new Map();
    this.dataEdges = new Map();
    this.bridgeEdges = new Map();
    this.attemptedDataRegions = new Map();
    this.calls = new Map();
    this.controlCalls = new Map();
    this.changedRefs = new Map();
    this.refs = new Map();
    this.descendantRefKeys = new Map();
  }

  /** Record a certified provider/model request statement. */
  addSource(span) {
    return this.#addMapItem(this.sources, spanKey(span), span);
  }

  /** Preserve all adjacent origins and reschedule readers when taint grows.
   * Downstream edges retain complete source locations.
   */
  addTaint(ref, origins) {
    return this.#addRefValues(this.taints, ref, origins);
  }

  /** Mark taint origins on `ref` as formal-parameter-derived. */
  addParamTaint(ref, origins) {
    return this.#addRefValues(this.paramTaints, ref, origins);
  }

  /** Mark a value ref as provider-backed. */
  addProvider(ref, providerKinds) {
    return this.#addRefValues(this.providers, ref, providerKinds);
  }

  /** Record known project class/type identities for a value ref. */
  addType(ref, classKeys) {
    return this.#addRefValues(this.types, ref, classKeys);
  }

  /** Record project-local callable aliases for a value ref. */
  addAlias(ref, targets) {
    return this.#addRefValues(this.aliases, ref, targets);
  }

  /** Record formal-parameter dependencies for one value ref. */
  addParamDep(ref, deps) {
    return this.#addRefValues(this.paramDeps, ref, deps);
  }

  /** Record string/URL fragments known for a value ref. */
  addString(ref, strings) {
    return this.#addRefValues(this.strings, ref, strings);
  }

  /** Mark one project-local function return as LLM-derived. */
  addReturn(functionId, origins) {
    return this.addTaint({ kind: "return", function: functionId }, origins);
  }

  /** Record parameter-dependent return spans for one project-local function. */
  addReturnParamDeps(functionId, deps, span) {
    let changed = false;
    if (!this.returnParamDeps.has(functionId)) this.returnParamDeps.set(functionId, new Map());
    const byDep = this.returnParamDeps.get(functionId);
    for (const dep of setValues(deps)) {
      const key = paramDepKey(dep);
      if (!byDep.has(key)) byDep.set(key, { dep, spans: new Set() });
      if (addFactValue(byDep.get(key).spans, span)) changed = true;
    }
    if (changed) this.#markChanged(returnRef(functionId));
    return changed;
  }

  /** Record one statement-level flow edge. */
  addDataEdge(span, origins, dependenceType) {
    if (setValues(origins).size) this.attemptedDataRegions.set(spanKey(span), span);
    return addEdge(this.dataEdges, span, origins, dependenceType);
  }

  /** Record an edge that is emitted only when needed for graph closure. */
  addBridgeEdge(span, origins, dependenceType) {
    return addEdge(this.bridgeEdges, span, origins, dependenceType);
  }

  /** Record one resolved project-local call. */
  addCall(fact) {
    return this.#addMapItem(this.calls, callFactKey(fact), fact);
  }

  /** Record one control-dependent project-local call. */
  addControlCall(fact) {
    return this.#addMapItem(this.controlCalls, controlCallFactKey(fact), fact);
  }

  /** Return adjacent taint origins for a value ref. */
  taintOf(ref) {
    return new Set(this.taints.get(refKey(ref)) || []);
  }

  /** Return taint origins on `ref` that are formal-parameter-derived. */
  paramTaintOf(ref) {
    return new Set(this.paramTaints.get(refKey(ref)) || []);
  }

  /** Return provider provenance for a value ref. */
  providerOf(ref) {
    return new Set(this.providers.get(refKey(ref)) || []);
  }

  /** Return known type/class ids for a value ref. */
  typeOf(ref) {
    return new Set(this.types.get(refKey(ref)) || []);
  }

  /** Return callable alias targets for a value ref. */
  aliasOf(ref) {
    return new Set(this.aliases.get(refKey(ref)) || []);
  }

  /** Return formal-parameter dependencies for a value ref. */
  paramDepOf(ref) {
    return new Set(this.paramDeps.get(refKey(ref)) || []);
  }

  /** Return parameter-dependent return summaries for one function. */
  returnParamDepsOf(functionId) {
    const out = new Map();
    for (const [key, entry] of this.returnParamDeps.get(functionId) || []) {
      out.set(key, { dep: entry.dep, spans: new Set(entry.spans) });
    }
    return out;
  }

  /** Return known string/URL fragments for a value ref. */
  stringOf(ref) {
    return new Set(this.strings.get(refKey(ref)) || []);
  }

  /** Return and clear refs whose facts changed since the last drain. */
  drainChangedRefs() {
    const refs = [...this.changedRefs.values()];
    this.changedRefs.clear();
    return refs;
  }

  /** Return descendants with relative paths for object-argument propagation.
   * Passing opts to callee(params) maps opts.onDone facts to params.onDone.
   */
  descendantRefsOf(baseRef) {
    const out = [];
    for (const key of this.descendantRefKeys.get(refKey(baseRef)) || []) {
      const ref = this.refs.get(key);
      if (!ref) continue;
      const suffix = descendantSuffix(baseRef, ref);
      if (suffix) out.push({ ref, suffix });
    }
    out.sort((left, right) => left.suffix.localeCompare(right.suffix) || refKey(left.ref).localeCompare(refKey(right.ref)));
    return out;
  }

  #addRefValues(store, ref, values) {
    const key = refKey(ref);
    const nextValues = setValues(values);
    if (!nextValues.size) return false;
    if (!store.has(key)) store.set(key, new Set());
    const current = store.get(key);
    const before = current.size;
    for (const value of nextValues) addFactValue(current, value);
    const changed = current.size !== before;
    if (changed) {
      this.#rememberRef(ref);
      this.#markChanged(ref);
    }
    return changed;
  }

  #rememberRef(ref) {
    const key = refKey(ref);
    if (this.refs.has(key)) return;
    this.refs.set(key, ref);
    for (const baseRef of ancestorRefs(ref)) {
      const baseKey = refKey(baseRef);
      if (!this.descendantRefKeys.has(baseKey)) this.descendantRefKeys.set(baseKey, new Set());
      this.descendantRefKeys.get(baseKey).add(key);
    }
  }

  #markChanged(ref) {
    const key = refKey(ref);
    if (!this.changedRefs.has(key)) this.changedRefs.set(key, ref);
  }

  #addMapItem(store, key, value) {
    if (store.has(key)) return false;
    store.set(key, value);
    return true;
  }
}

/** Key edges by destination and flow type so later passes merge source spans. */
function dataEdgeKey(span, dependenceType) {
  return `${spanKey(span)}:${dependenceType}`;
}

/** Return object/container prefix refs for one concrete path ref. */
function ancestorRefs(ref) {
  if (!ref || !("path" in ref)) return [];
  const parts = ref.path.split(".").filter(Boolean);
  const out = [];
  if (ref.kind === "return" && parts.length) out.push(returnRef(ref.function));
  for (let index = 1; index < parts.length; index += 1) {
    const path = parts.slice(0, index).join(".");
    if (ref.kind === "local") out.push({ kind: "local", function: ref.function, path });
    else if (ref.kind === "return") out.push(returnRef(ref.function, path));
    else if (ref.kind === "class_field") out.push({ kind: "class_field", class: ref.class, path });
    else if (ref.kind === "module") out.push({ kind: "module", file: ref.file, path });
  }
  return out;
}

/** Return the field suffix when `candidate` is under `base`, otherwise empty. */
function descendantSuffix(base, candidate) {
  if (!base || !candidate || base.kind !== candidate.kind) return "";
  if (base.kind === "local" && base.function !== candidate.function) return "";
  if (base.kind === "return" && base.function !== candidate.function) return "";
  if (base.kind === "class_field" && base.class !== candidate.class) return "";
  if (base.kind === "module" && base.file !== candidate.file) return "";
  const basePath = "path" in base ? base.path : "";
  const candidatePath = "path" in candidate ? candidate.path : "";
  if (!candidatePath) return "";
  if (!basePath) return candidatePath;
  const prefix = `${basePath}.`;
  return candidatePath.startsWith(prefix) ? candidatePath.slice(prefix.length) : "";
}
