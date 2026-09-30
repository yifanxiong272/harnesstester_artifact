import { classKey, functionKey } from "./models.mjs";
import {
  functionParams,
  isFunctionLikeWithBody,
  readSourceFile,
  spanOf,
  textOf,
} from "./syntax.mjs";
import { collectAssignedNames, collectDeclaredNames } from "./indexing/assignments.mjs";
import {
  addNameBinding,
  createNameEnv,
  registerScope,
  scopeKey,
} from "./indexing/bindings.mjs";
import {
  finalizeExports,
  maybeExportDeclaredSymbol,
  recordExportAssignment,
  recordExportDeclaration,
} from "./indexing/exports.mjs";
import { finalizeClassInheritance, resolveClassPath, resolveInterfacePath } from "./indexing/inheritance.mjs";
import {
  buildPackageResolution,
  recordImportDeclaration,
  recordImportEqualsDeclaration,
  recordRequireImportsFromVariableStatement,
} from "./indexing/imports.mjs";
import {
  heritageBaseExpressions,
  implementedInterfaceExpressions,
  isClassLike,
  stableClassName,
  stableFunctionName,
} from "./indexing/names.mjs";

export { createNameEnv, resolveClassPath, resolveInterfacePath, scopeKey };

/** Index lexical scopes, imports, exports, functions, classes, and inheritance.
 * The resulting maps are shared by the resolver and flow analysis.
 */
export function buildProjectIndex({ ts, root, files }) {
  const index = createProjectIndex(root, files);

  for (const rel of files) {
    const file = readSourceFile(ts, root, rel);
    index.files.set(rel, file);
    const moduleEnv = registerScope(index, createNameEnv({ file: rel }));
    index.moduleScopes.set(rel, moduleEnv.key);
  }

  for (const file of index.files.values()) indexFile(ts, index, file);

  finalizeExports(index);
  finalizeClassInheritance(index);
  return index;
}

/** Create maps for lexical scopes, declarations, exports, and class relationships. */
function createProjectIndex(root, files) {
  return {
    root,
    files: new Map(),
    fileSet: new Set(files),
    packageResolution: buildPackageResolution(root, files),
    moduleScopes: new Map(),
    scopeEnvs: new Map(),
    functions: new Map(),
    functionByNode: new WeakMap(),
    classes: new Map(),
    classByNode: new WeakMap(),
    interfaces: new Map(),
    typeAliases: new Map(),
    interfacePathCache: new Map(),
    classMethods: new Map(),
    classBases: new Map(),
    classSubclasses: new Map(),
    interfaceImplementers: new Map(),
    exportsByFile: new Map(),
  };
}

/** Walk one file and populate static index facts.
 *
 * Called by: `buildProjectIndex` once per parsed source file. Anonymous inline
 * callbacks are not global units; later flow activates them only when a tainted
 * callback route exists.
 */
function indexFile(ts, index, file) {
  const moduleEnv = index.scopeEnvs.get(index.moduleScopes.get(file.rel));
  const state = createVisitorState(moduleEnv);

  function visit(node) {
    const env = currentScope(state);
    if (recordDeclarationSideEffects(ts, index, file, env, node)) return;
    if (tryRegisterInterface(ts, index, file, state, env, node)) return;
    if (tryRegisterTypeAlias(ts, index, file, state, env, node)) return;
    if (tryRegisterClass(ts, index, file, state, env, node)) return;
    if (tryRegisterFunction(ts, index, file, state, env, node)) return;
    ts.forEachChild(node, visit);
  }

  visit(file.sourceFile);
}

/** Create the lexical visitor state for one file walk. */
function createVisitorState(moduleEnv) {
  return {
    scopeStack: [moduleEnv],
    qualStack: [],
    classStack: [],
    functionStack: [],
  };
}

/** Record imports/exports attached to the current lexical env.
 *
 * Called by: every visitor before class/function registration. It returns true
 * only for declarations whose children should not be visited as normal flow
 * units.
 */
function recordDeclarationSideEffects(ts, index, file, env, node) {
  if (ts.isImportDeclaration(node)) {
    recordImportDeclaration(ts, index, file, env, node);
    return true;
  }
  if (ts.isImportEqualsDeclaration(node)) {
    recordImportEqualsDeclaration(ts, index, file, env, node);
    return true;
  }
  if (ts.isVariableStatement(node)) recordRequireImportsFromVariableStatement(ts, index, file, env, node);
  if (ts.isExportDeclaration(node)) {
    recordExportDeclaration(ts, index, file, env, node);
    return true;
  }
  if (ts.isExportAssignment(node)) recordExportAssignment(ts, env, node);
  return false;
}

/** Register an interface declaration as a project-local type target.
 *
 * Called by: file/function visitors before class/function registration.
 * Interfaces have no executable body, but their names can type receivers whose
 * method calls should dispatch to explicit implementing classes.
 */
function tryRegisterInterface(ts, index, file, state, env, node) {
  if (!ts.isInterfaceDeclaration?.(node)) return false;
  const info = buildInterfaceInfo(file, state, node);
  addNameBinding(env.localInterfaces, info.name, info.key);
  maybeExportDeclaredSymbol(ts, env, node, info.name, { kind: "interface", key: info.key });
  index.interfaces.set(info.key, info);
  return true;
}

/** Register a type alias so interface identities can be recovered through it.
 *
 * Called by: file/function visitors before class registration. Type aliases do
 * not create executable regions, but they often wrap interfaces in TS utility
 * types such as `RPCMethods<SDKAPI>`.
 */
function tryRegisterTypeAlias(ts, index, file, state, env, node) {
  if (!ts.isTypeAliasDeclaration?.(node)) return false;
  const info = buildTypeAliasInfo(file, state, node);
  addNameBinding(env.localTypeAliases, info.name, info.key);
  maybeExportDeclaredSymbol(ts, env, node, info.name, { kind: "type_alias", key: info.key });
  index.typeAliases.set(info.key, info);
  return true;
}

/** Build the metadata record for one interface declaration. */
function buildInterfaceInfo(file, state, node) {
  const name = node.name.text;
  const qualname = [...state.qualStack, name].join(".");
  const span = spanOf(file.sourceFile, node);
  return {
    key: interfaceKey(file.rel, qualname),
    file: file.rel,
    node,
    sourceFile: file.sourceFile,
    text: file.text,
    name,
    qualname,
    scope: currentScope(state).key,
    start: span.start,
    end: span.end,
    span,
  };
}

/** Build the metadata record for one project-local type alias. */
function buildTypeAliasInfo(file, state, node) {
  const name = node.name.text;
  const qualname = [...state.qualStack, name].join(".");
  const span = spanOf(file.sourceFile, node);
  return {
    key: typeAliasKey(file.rel, qualname),
    file: file.rel,
    node,
    sourceFile: file.sourceFile,
    text: file.text,
    name,
    qualname,
    scope: currentScope(state).key,
    annotation: node.type ? textOf(file.sourceFile, node.type) : "",
    start: span.start,
    end: span.end,
    span,
  };
}

/** Register a class if the node has a stable project-local identity.
 *
 * Called by: file/function/class visitors. Anonymous inline classes are skipped
 * because object identity is not part of the first TS may-analysis model.
 */
function tryRegisterClass(ts, index, file, state, env, node) {
  if (!isClassLike(ts, node)) return false;
  const info = buildClassInfo(ts, file, state, node);
  if (!info) return true;
  registerClass(ts, index, file, state, env, info, node);
  return true;
}

/** Register a function if the node has a stable project-local identity.
 *
 * Called by: file/function/class visitors. Bare anonymous callback arguments are
 * intentionally not indexed globally.
 */
function tryRegisterFunction(ts, index, file, state, env, node) {
  if (!isFunctionLikeWithBody(ts, node)) return false;
  const info = buildFunctionInfo(ts, file, state, node);
  if (!info) return true;
  registerFunction(ts, index, file, state, env, info, node);
  return true;
}

/** Build the metadata record for one stable class. */
function buildClassInfo(ts, file, state, node) {
  const nameInfo = stableClassName(ts, node);
  if (!nameInfo) return null;
  const qualname = [...state.qualStack, nameInfo.name].join(".");
  const span = spanOf(file.sourceFile, node);
  return {
    key: classKey(file.rel, qualname),
    file: file.rel,
    node,
    sourceFile: file.sourceFile,
    text: file.text,
    name: nameInfo.name,
    registerPath: nameInfo.registerPath,
    qualname,
    scope: currentScope(state).key,
    parentScope: currentScope(state).key,
    enclosingFunction: currentFunction(state)?.key || "",
    enclosingFunctions: state.functionStack.map((item) => item.key),
    start: span.start,
    end: span.end,
    span,
    bases: heritageBaseExpressions(ts, file.sourceFile, node),
    interfaces: implementedInterfaceExpressions(ts, file.sourceFile, node),
  };
}

/** Register a class, create its scope, and visit class members. */
function registerClass(ts, index, file, state, env, info, node) {
  addNameBinding(env.localClasses, info.registerPath || info.name, info.key);
  addNameBinding(env.localClasses, info.name, info.key);
  maybeExportDeclaredSymbol(ts, env, node, info.name, { kind: "class", key: info.key });

  const classEnv = registerScope(
    index,
    createNameEnv({ file: file.rel, qualname: info.qualname, parent: env.key }),
  );
  info.scope = classEnv.key;
  info.parentScope = env.key;
  index.classes.set(info.key, info);
  index.classByNode.set(node, info);

  pushClassState(state, classEnv, info);
  for (const member of node.members || []) indexClassChild(ts, index, file, state, member);
  popClassState(state);
}

/** Visit a class member under the class lexical scope.
 *
 * Called by: `registerClass`. Class-field arrow functions are handled through
 * their initializer; nested named classes/functions remain normal indexed units.
 */
function indexClassChild(ts, index, file, state, node) {
  const env = currentScope(state);
  if (tryRegisterInterface(ts, index, file, state, env, node)) return;
  if (tryRegisterTypeAlias(ts, index, file, state, env, node)) return;
  if (tryRegisterClass(ts, index, file, state, env, node)) return;
  if (tryRegisterFunction(ts, index, file, state, env, node)) return;
  if (ts.isPropertyDeclaration?.(node) && node.initializer) {
    if (tryRegisterFunction(ts, index, file, state, env, node.initializer)) return;
  }
  ts.forEachChild(node, (child) => indexClassChild(ts, index, file, state, child));
}

/** Build the metadata record for one stable function or method. */
function buildFunctionInfo(ts, file, state, node) {
  const nameInfo = stableFunctionName(ts, file.sourceFile, node);
  if (!nameInfo) return null;
  const qualname = [...state.qualStack, nameInfo.name].join(".");
  const span = spanOf(file.sourceFile, node);
  const ownerClass = owningClassForFunction(ts, state, node);
  const enclosingClass = currentClass(state);
  return {
    key: functionKey(file.rel, qualname),
    file: file.rel,
    node,
    sourceFile: file.sourceFile,
    text: file.text,
    name: nameInfo.name,
    registerPath: nameInfo.registerPath,
    kind: nameInfo.kind,
    qualname,
    scope: currentScope(state).key,
    parentScope: currentScope(state).key,
    classKey: ownerClass?.key || "",
    enclosingClassKey: enclosingClass?.key || "",
    enclosingFunction: currentFunction(state)?.key || "",
    enclosingFunctions: state.functionStack.map((item) => item.key),
    start: span.start,
    end: span.end,
    span,
    params: functionParams(ts, node, file.sourceFile),
    returnAnnotation: node.type ? textOf(file.sourceFile, node.type) : "",
    assignedNames: collectAssignedNames(ts, node),
    declaredNames: collectDeclaredNames(ts, node),
  };
}

/** Register a function, create its scope, and visit nested declarations. */
function registerFunction(ts, index, file, state, env, info, node) {
  if (!info.classKey) addNameBinding(env.localFunctions, info.registerPath || info.name, info.key);
  else addClassMethod(index, info.classKey, info.name, info.key);
  maybeExportDeclaredSymbol(ts, env, node, info.name, { kind: "function", key: info.key });

  const functionEnv = registerScope(
    index,
    createNameEnv({ file: file.rel, qualname: info.qualname, parent: env.key }),
  );
  info.scope = functionEnv.key;
  info.parentScope = env.key;
  index.functions.set(info.key, info);
  index.functionByNode.set(node, info);

  pushFunctionState(state, functionEnv, info);
  ts.forEachChild(node, (child) => indexNestedChild(ts, index, file, state, child));
  popFunctionState(state);
}

/** Visit nested declarations under a function body.
 *
 * Called by: `registerFunction`. Non-stable anonymous callbacks are skipped
 * until flow-time callback activation.
 */
function indexNestedChild(ts, index, file, state, node) {
  const env = currentScope(state);
  if (recordDeclarationSideEffects(ts, index, file, env, node)) return;
  if (tryRegisterInterface(ts, index, file, state, env, node)) return;
  if (tryRegisterTypeAlias(ts, index, file, state, env, node)) return;
  if (tryRegisterClass(ts, index, file, state, env, node)) return;
  if (tryRegisterFunction(ts, index, file, state, env, node)) return;
  ts.forEachChild(node, (child) => indexNestedChild(ts, index, file, state, child));
}

/** Return the class that directly owns a function-like class member. */
function owningClassForFunction(ts, state, node) {
  const owner = currentClass(state);
  if (!owner) return null;
  if (node.parent === owner.node) return owner;
  if (ts.isPropertyDeclaration?.(node.parent) && node.parent.parent === owner.node) return owner;
  return null;
}

/** Record one class method mapping used by resolver method calls. */
function addClassMethod(index, owningClassKey, methodName, functionId) {
  let methods = index.classMethods.get(owningClassKey);
  if (!methods) {
    methods = new Map();
    index.classMethods.set(owningClassKey, methods);
  }
  addNameBinding(methods, methodName, functionId);
}

/** Build a stable project-local interface key. */
function interfaceKey(file, qualname) {
  return `${file}::interface:${qualname}`;
}

/** Build a stable project-local type-alias key. */
function typeAliasKey(file, qualname) {
  return `${file}::type_alias:${qualname}`;
}

/** Return the env currently visible to a visitor. */
function currentScope(state) {
  return state.scopeStack[state.scopeStack.length - 1];
}

/** Return the directly enclosing class, if any. */
function currentClass(state) {
  return state.classStack[state.classStack.length - 1] || null;
}

/** Return the directly enclosing function, if any. */
function currentFunction(state) {
  return state.functionStack[state.functionStack.length - 1] || null;
}

/** Push class lexical state while visiting class members. */
function pushClassState(state, env, info) {
  state.scopeStack.push(env);
  state.qualStack.push(info.name);
  state.classStack.push(info);
}

/** Restore visitor state after a class. */
function popClassState(state) {
  state.classStack.pop();
  state.qualStack.pop();
  state.scopeStack.pop();
}

/** Push function lexical state while visiting nested declarations. */
function pushFunctionState(state, env, info) {
  state.scopeStack.push(env);
  state.qualStack.push(info.name);
  state.functionStack.push(info);
}

/** Restore visitor state after a function. */
function popFunctionState(state) {
  state.functionStack.pop();
  state.qualStack.pop();
  state.scopeStack.pop();
}
