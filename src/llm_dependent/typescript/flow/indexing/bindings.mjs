/** Build the canonical key for a lexical name environment.
 *
 * Called by: `buildProjectIndex` when creating module, function, and class
 * scopes. Resolver code walks these keys through `env.parent`.
 */
export function scopeKey(file, qualname = "") {
  return `${file}::${qualname}`;
}

/** Create one lexical environment record.
 *
 * Called by: module/class/function indexing. Each env stores only declarations
 * introduced in that scope; resolver walks parents instead of copying maps.
 */
export function createNameEnv({ file, qualname = "", parent = null }) {
  return {
    key: scopeKey(file, qualname),
    file,
    qualname,
    parent,
    importsByLocal: new Map(),
    localFunctions: new Map(),
    localClasses: new Map(),
    localInterfaces: new Map(),
    localTypeAliases: new Map(),
    exports: new Map(),
    reexports: [],
  };
}

/** Register a lexical env in the project index.
 *
 * Called by: `buildProjectIndex` and nested visitors whenever a new scope is
 * entered.
 */
export function registerScope(index, env) {
  index.scopeEnvs.set(env.key, env);
  return env;
}

/** Add a local name binding to a map of `name -> Set<id>`.
 *
 * Called by: function/class/method registration and export resolution. Multiple
 * values are preserved for conservative may-analysis.
 */
export function addNameBinding(map, name, value) {
  if (!name) return;
  if (!map.has(name)) map.set(name, new Set());
  map.get(name).add(value);
}

/** Add a structured target to a map of `name -> Map<targetKey, target>`.
 *
 * Called by: import/export helpers where object identity would otherwise create
 * duplicate facts.
 */
export function addTargetBinding(map, name, target) {
  if (!name) return;
  if (!map.has(name)) map.set(name, new Map());
  map.get(name).set(targetKey(target), target);
}

/** Build a stable key for import/export target de-duplication.
 *
 * Called by: `addTargetBinding` and export finalization.
 */
export function targetKey(target) {
  return JSON.stringify(target);
}
