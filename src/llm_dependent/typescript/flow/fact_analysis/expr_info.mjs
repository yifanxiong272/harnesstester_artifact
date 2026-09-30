/** Create monotonic expression facts; predecessors stay statement-local,
 * while value facts cross explicit boundaries into FactStore.
 */
export function exprInfo() {
  return {
    origins: new Set(),
    predecessors: new Set(),
    paramOrigins: new Set(),
    directSources: new Set(),
    providers: new Set(),
    types: new Set(),
    aliases: new Set(),
    paramDeps: new Set(),
    strings: new Set(),
    fieldInfos: new Map(),
  };
}

/** Merge expression facts and return the target for composition. */
export function mergeExprInfo(target, source) {
  mergeInto(target.origins, source.origins);
  mergeInto(target.predecessors, source.predecessors);
  mergeInto(target.paramOrigins, source.paramOrigins);
  mergeInto(target.directSources, source.directSources);
  mergeInto(target.providers, source.providers);
  mergeInto(target.types, source.types);
  mergeInto(target.aliases, source.aliases);
  mergeInto(target.paramDeps, source.paramDeps);
  mergeInto(target.strings, source.strings);
  for (const [suffix, fieldInfo] of source.fieldInfos || []) mergeFieldInfo(target, suffix, fieldInfo);
  return target;
}

/** Merge descendant facts at their field suffix, preserving callable identity.
 * A returned onDelta method becomes callbacks.onDelta, not a callable container.
 */
export function mergeFieldInfo(target, suffix, source) {
  if (!suffix || !source) return target;
  if (!target.fieldInfos.has(suffix)) target.fieldInfos.set(suffix, exprInfo());
  mergeExprInfo(target.fieldInfos.get(suffix), source);
  return target;
}

/** Add iterable values into a set. */
export function mergeInto(target, values) {
  for (const value of values || []) target.add(value);
  return target;
}

/** Identify direct sources, which are emitted separately from dependence edges.
 * Their own source calls must not produce self-dependence edges.
 */
export function isDirectSourceOnly(info) {
  return info.directSources.size > 0 && [...info.origins].every((origin) => info.directSources.has(origin));
}
