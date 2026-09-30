export {
  functionContext,
  literalString,
} from "./resolver/utils.mjs";

export {
  fullNamesForExpression,
  nameIsLocalToFunction,
  ownScopeNames,
  resolveExprName,
  resolveName,
} from "./resolver/names.mjs";

export {
  classesForPath,
  directRefsForPath,
  receiverClasses,
  refsForPath,
  refsForReadExpr,
  targetRefs,
} from "./resolver/refs.mjs";

export {
  classesForType,
  classContextKey,
  constructorTargets,
  methodInfos,
  methodTargets,
  transitiveBases,
  transitiveSubclasses,
} from "./resolver/classes.mjs";

export {
  resolveCall,
  resolveConstructor,
} from "./resolver/calls.mjs";

export {
  resolveInterfacePath,
} from "./indexing.mjs";
