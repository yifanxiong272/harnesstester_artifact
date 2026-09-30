/** Standard receiver methods whose callback receives receiver-carried values.
 *
 * Called by: callback flow in `analysis_fact.mjs`. These are JS/TS library
 * semantics, not project rule names: if `items` may contain LLM data, then
 * `items.map((item) => ...)` receives an LLM-derived `item`.
 */
export const RECEIVER_CALLBACK_METHODS = new Map([
  ["map", [{ arg: 0, params: [0] }]],
  ["flatMap", [{ arg: 0, params: [0] }]],
  ["filter", [{ arg: 0, params: [0] }]],
  ["find", [{ arg: 0, params: [0] }]],
  ["findIndex", [{ arg: 0, params: [0] }]],
  ["findLast", [{ arg: 0, params: [0] }]],
  ["findLastIndex", [{ arg: 0, params: [0] }]],
  ["forEach", [{ arg: 0, params: [0] }]],
  ["every", [{ arg: 0, params: [0] }]],
  ["some", [{ arg: 0, params: [0] }]],
  ["reduce", [{ arg: 0, params: [1] }]],
  ["reduceRight", [{ arg: 0, params: [1] }]],
  ["sort", [{ arg: 0, params: [0, 1] }]],
  ["then", [{ arg: 0, params: [0] }, { arg: 1, params: [0] }]],
  ["catch", [{ arg: 0, params: [0] }]],
]);

/** Static helper calls that route one source argument into a callback.
 *
 * Called by: callback flow for APIs such as `Array.from(items, mapFn)`.
 */
export const STATIC_CALLBACK_METHODS = new Map([
  ["Array.from", { sourceArgIndex: 0, callbacks: [{ arg: 1, params: [0] }] }],
  ["Array.fromAsync", { sourceArgIndex: 0, callbacks: [{ arg: 1, params: [0] }] }],
  ["Object.groupBy", { sourceArgIndex: 0, callbacks: [{ arg: 1, params: [0] }] }],
  ["Map.groupBy", { sourceArgIndex: 0, callbacks: [{ arg: 1, params: [0] }] }],
]);

/** Standard event/subscription methods that pass receiver events to handlers.
 *
 * Called by: subscription flow. Event names are intentionally not filtered:
 * once the receiver is LLM-derived, every registered handler is conservatively
 * treated as receiving LLM-derived channel data.
 */
export const EVENT_SUBSCRIPTION_METHODS = new Set([
  "subscribe",
  "on",
  "once",
  "addEventListener",
  "addListener",
  "prependListener",
]);

/** Standard methods that publish one value into an event/channel receiver.
 *
 * Called by: event-channel flow. These names are library/channel verbs, not
 * project wrappers. The transfer still requires the published argument to be
 * LLM-derived before any receiver becomes a channel carrier.
 */
export const EVENT_PUBLISH_METHODS = new Set([
  "dispatch",
  "emit",
  "fire",
  "notify",
  "publish",
]);

/** Standard receiver methods whose return value may come from the receiver.
 *
 * Called by: call-result transfer. This is conservative container/response
 * semantics for static may-analysis; project-local callees still use normal
 * call resolution and return facts.
 */
export const RECEIVER_RETURN_METHODS = new Set([
  "map",
  "flatMap",
  "filter",
  "find",
  "reduce",
  "join",
  "pop",
  "shift",
  "split",
  "slice",
  "at",
  "get",
  "keys",
  "values",
  "entries",
  "json",
  "text",
]);

/** Standard mutating methods that store argument values into a receiver.
 *
 * Called by: container mutation flow. The transfer is container-level: after
 * `items.push(x)` or `map.set(k, x)`, later reads from `items`/`map` may see
 * facts from `x`.
 */
export const CONTAINER_MUTATION_METHODS = new Set([
  "add",
  "append",
  "fill",
  "push",
  "set",
  "splice",
  "unshift",
]);

export const CONTROL_DEPENDENCE_MODES = new Set([
  "block_only",
  "control-dependence-direct",
  "control-dependence-recursive",
]);

/** Normalize OpenHands-style control dependence mode names. */
export function normalizeControlDependenceMode(value) {
  const mode = value || "block_only";
  if (!CONTROL_DEPENDENCE_MODES.has(mode)) {
    throw new Error(
      "--control-dependence-mode must be one of: block_only, control-dependence-direct, control-dependence-recursive",
    );
  }
  return mode;
}

/** Build the canonical id for a project-local function. */
export function functionKey(file, qualname) {
  return `${file}::${qualname}`;
}

/** Build the canonical id for a project-local class. */
export function classKey(file, qualname) {
  return `${file}::${qualname}`;
}

/** Build a local value ref inside one function scope. */
export function localRef(functionId, path) {
  return { kind: "local", function: functionId, path };
}

/** Build a return value ref for one project-local function.
 *
 * The optional path stores returned object-field facts, for example
 * `returnRef(fn, "onDelta")` can later become `callbacks.onDelta`.
 */
export function returnRef(functionId, path = "") {
  return path ? { kind: "return", function: functionId, path } : { kind: "return", function: functionId };
}

/** Build a dependency on one formal parameter of one function. */
export function paramDep(functionId, name) {
  return { function: functionId, name };
}

/** Build a class-level field ref. */
export function classFieldRef(classId, path) {
  return { kind: "class_field", class: classId, path };
}

/** Build a module-level value ref. */
export function moduleRef(file, path) {
  return { kind: "module", file, path };
}

/** Build a stable string key for any fact-store value ref. */
export function refKey(ref) {
  if (ref.kind === "local") return `local:${ref.function}:${ref.path}`;
  if (ref.kind === "return") return ref.path ? `return:${ref.function}:${ref.path}` : `return:${ref.function}`;
  if (ref.kind === "class_field") return `class_field:${ref.class}:${ref.path}`;
  if (ref.kind === "module") return `module:${ref.file}:${ref.path}`;
  throw new Error(`unknown ref kind: ${ref.kind}`);
}

/** Build a stable key for one source/data/control span. */
export function spanKey(span) {
  return `${span.filepath}:${span.start_line}:${span.end_line}`;
}

/** Build a stable key for one formal-parameter dependency. */
export function paramDepKey(dep) {
  return `${dep.function}:${dep.name}`;
}

/** Sort spans by file and line range for deterministic artifacts. */
export function compareSpans(left, right) {
  return (
    left.filepath.localeCompare(right.filepath) ||
    left.start_line - right.start_line ||
    left.end_line - right.end_line
  );
}

/** Return spans in stable order. */
export function orderedSpans(spans) {
  return [...spans].sort(compareSpans);
}

/** Build one statement-level flow edge for fact-store payload serialization. */
export function flowEdge(span, sourceSpans, dependenceType) {
  return {
    span,
    source_spans: orderedSpans(sourceSpans),
    dependence_type: dependenceType,
  };
}

/** Build one resolved project-local call fact. */
export function callFact(caller, callee, span) {
  return { caller, callee, span };
}

/** Build a stable key for one call fact. */
export function callFactKey(fact) {
  return `${fact.caller}->${fact.callee}:${spanKey(fact.span)}`;
}

/** Build one control-dependent project-local call fact. */
export function controlCallFact(caller, callee, span, controlSpan) {
  return { caller, callee, span, control_span: controlSpan };
}

/** Build a stable key for one control call fact. */
export function controlCallFactKey(fact) {
  return `${fact.caller}->${fact.callee}:${spanKey(fact.span)}:${spanKey(fact.control_span)}`;
}
