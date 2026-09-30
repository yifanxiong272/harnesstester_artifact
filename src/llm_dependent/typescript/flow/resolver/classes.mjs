import { callTarget, sorted, transitiveClassWalk } from "./utils.mjs";

/** Return the class context used for `this` and class fields.
 *
 * Called by: ref and method resolution. `classKey` means direct class member;
 * `enclosingClassKey` preserves conservative `this` handling for nested arrows.
 */
export function classContextKey(info) {
  return info.classKey || info.enclosingClassKey || "";
}

/** Return constructor function targets for a class.
 *
 * Called by: `resolveCall` when a call expression resolves to a class.
 */
export function constructorTargets(classId, index) {
  return methodTargets(classId, "constructor", index);
}

/** Return method targets for a known receiver class and method name.
 *
 * Called by: call resolution. Exact methods, inherited base methods, and known
 * subclass overrides are all included for conservative dynamic dispatch.
 */
export function methodTargets(classId, methodName, index) {
  return methodInfos(classId, methodName, index).map((info) => callTarget(info.key));
}

/** Return method FunctionInfo records for one class/method pair.
 *
 * Called by: `methodTargets`. The index shape is
 * `classKey -> methodName -> Set<functionKey>`.
 */
export function methodInfos(classId, methodName, index) {
  const functionIds = new Set(index.classMethods.get(classId)?.get(methodName) || []);
  for (const base of transitiveBases(classId, index)) {
    for (const functionId of index.classMethods.get(base)?.get(methodName) || []) functionIds.add(functionId);
  }
  for (const subclass of transitiveSubclasses(classId, index)) {
    for (const functionId of index.classMethods.get(subclass)?.get(methodName) || []) functionIds.add(functionId);
  }
  return sorted(functionIds)
    .map((functionId) => index.functions.get(functionId))
    .filter(Boolean);
}

/** Return concrete classes represented by one class/interface type id.
 *
 * Called by: ref resolution for typed receivers. Class ids stay exact while
 * interface ids expand only through explicit `implements` clauses, avoiding
 * structural guessing.
 */
export function classesForType(typeId, index) {
  if (index.classes.has(typeId)) return new Set([typeId]);
  return new Set(index.interfaceImplementers.get(typeId) || []);
}

/** Return all known base classes for a class.
 *
 * Called by: class-field refs and method resolution.
 */
export function transitiveBases(classId, index) {
  return transitiveClassWalk(classId, index.classBases);
}

/** Return all known subclasses for a class.
 *
 * Called by: method resolution so base-typed receivers include overrides.
 */
export function transitiveSubclasses(classId, index) {
  return transitiveClassWalk(classId, index.classSubclasses);
}
