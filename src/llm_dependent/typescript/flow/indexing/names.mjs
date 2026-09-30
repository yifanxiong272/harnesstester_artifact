import { exprPath, textOf } from "../syntax.mjs";
import { propertyChain, unwrapExpression } from "../source_locator.mjs";

/** Test whether a node introduces a class scope with a body.
 *
 * Called by: index visitors and assignment metadata to keep class bodies scoped
 * separately from enclosing functions.
 */
export function isClassLike(ts, node) {
  return ts.isClassDeclaration(node) || ts.isClassExpression(node);
}

/** Return a property/function/member name from a TS name node.
 *
 * Called by: stable identity helpers. Computed names are supported only for
 * literal keys; non-literal computed names are intentionally not guessed.
 */
export function nameNodeText(ts, sourceFile, node) {
  if (!node) return "";
  if (ts.isIdentifier(node) || ts.isPrivateIdentifier?.(node)) return node.text;
  if (ts.isStringLiteralLike?.(node) || ts.isNumericLiteral(node)) return node.text;
  if (ts.isComputedPropertyName(node)) {
    const expression = unwrapExpression(ts, node.expression);
    if (ts.isStringLiteralLike?.(expression) || ts.isNumericLiteral(expression)) return expression.text;
    return "";
  }
  return textOf(sourceFile, node);
}

/** Decide whether a function-like node has a stable project-local name.
 *
 * Called by: function indexing. It covers declarations, methods, assigned
 * function expressions, class-field functions, and default-export expressions.
 */
export function stableFunctionName(ts, sourceFile, node) {
  if (ts.isConstructorDeclaration(node)) {
    return { name: "constructor", registerPath: "constructor", kind: "constructor" };
  }
  if (ts.isMethodDeclaration(node) || ts.isGetAccessorDeclaration(node) || ts.isSetAccessorDeclaration(node)) {
    const name = nameNodeText(ts, sourceFile, node.name);
    if (!name) return null;
    return { name, registerPath: name, kind: "method" };
  }
  if (ts.isFunctionDeclaration(node)) {
    const name = node.name?.text || (hasModifier(node, ts.SyntaxKind.DefaultKeyword) ? "default" : "");
    if (!name) return null;
    return { name, registerPath: name, kind: "function_declaration" };
  }

  const assignedPath = assignedFunctionPath(ts, sourceFile, node);
  if (!assignedPath) return null;
  const name = assignedPath.split(".").filter(Boolean).pop() || assignedPath;
  return {
    name,
    registerPath: assignedPath,
    kind: ts.isArrowFunction(node) ? "arrow_function" : "function_expression",
  };
}

/** Decide whether a class-like node has a stable project-local name.
 *
 * Called by: class indexing. Anonymous class expressions are indexed only when
 * they are assigned to a stable local/property or default export.
 */
export function stableClassName(ts, node) {
  if (ts.isClassDeclaration(node)) {
    const name = node.name?.text || (hasModifier(node, ts.SyntaxKind.DefaultKeyword) ? "default" : "");
    if (!name) return null;
    return { name, registerPath: name };
  }

  const parent = node.parent;
  if (!parent) return null;
  if (ts.isVariableDeclaration(parent) && ts.isIdentifier(parent.name)) {
    return { name: parent.name.text, registerPath: parent.name.text };
  }
  if (ts.isBinaryExpression(parent) && parent.right === node) {
    const assignedPath = exprPath(ts, parent.left);
    const name = assignedPath.split(".").filter(Boolean).pop() || assignedPath;
    return assignedPath ? { name, registerPath: assignedPath } : null;
  }
  if (ts.isExportAssignment(parent)) return { name: "default", registerPath: "default" };
  return null;
}

/** Collect syntactic `extends` expressions for a class.
 *
 * Called by: class indexing. Resolution is delayed until imports/exports and
 * all classes are known.
 */
export function heritageBaseExpressions(ts, sourceFile, node) {
  const bases = [];
  for (const clause of node.heritageClauses || []) {
    if (clause.token !== ts.SyntaxKind.ExtendsKeyword) continue;
    for (const type of clause.types || []) {
      const pathText = exprPath(ts, type.expression) || propertyChain(ts, type.expression).join(".");
      bases.push({
        expression: textOf(sourceFile, type.expression),
        path: pathText,
        resolved_class_keys: [],
      });
    }
  }
  return bases;
}

/** Collect explicit `implements` interface expressions for a class.
 *
 * Called by: class indexing. These are later resolved to indexed interfaces so
 * interface-typed receiver calls can dispatch to concrete class methods.
 */
export function implementedInterfaceExpressions(ts, sourceFile, node) {
  const interfaces = [];
  for (const clause of node.heritageClauses || []) {
    if (clause.token !== ts.SyntaxKind.ImplementsKeyword) continue;
    for (const type of clause.types || []) {
      const pathText = exprPath(ts, type.expression) || propertyChain(ts, type.expression).join(".");
      interfaces.push({
        expression: textOf(sourceFile, type.expression),
        path: pathText,
        resolved_interface_keys: [],
      });
    }
  }
  return interfaces;
}

/** Test whether a node has a modifier keyword.
 *
 * Called by: identity and export helpers.
 */
export function hasModifier(node, kind) {
  return Boolean(node.modifiers?.some((modifier) => modifier.kind === kind));
}

/** Find the assigned path that gives a function expression stable identity.
 *
 * Called by: `stableFunctionName`. This is syntax-only and does not infer
 * wrapper behavior from names.
 */
function assignedFunctionPath(ts, sourceFile, node) {
  const parent = node.parent;
  if (!parent) return "";

  if (ts.isVariableDeclaration(parent) && ts.isIdentifier(parent.name)) return parent.name.text;
  if (ts.isPropertyDeclaration?.(parent)) return nameNodeText(ts, sourceFile, parent.name);
  if (ts.isPropertyAssignment(parent)) return objectLiteralFunctionPath(ts, sourceFile, parent);
  if (ts.isBinaryExpression(parent) && parent.right === node) return exprPath(ts, parent.left);
  if (ts.isExportAssignment(parent)) return "default";
  return "";
}

/** Build a path for `{ fn: () => ... }` when possible.
 *
 * Called by: `assignedFunctionPath`. If the object literal is anonymous, the
 * property name alone is still useful inside the containing local scope.
 */
function objectLiteralFunctionPath(ts, sourceFile, propertyAssignment) {
  const propertyName = nameNodeText(ts, sourceFile, propertyAssignment.name);
  if (!propertyName) return "";
  const objectLiteral = propertyAssignment.parent;
  if (!ts.isObjectLiteralExpression(objectLiteral)) return propertyName;
  const owner = objectLiteralAssignedPath(ts, objectLiteral);
  return owner ? `${owner}.${propertyName}` : propertyName;
}

/** Return the local owner path for an object literal expression.
 *
 * Called by: object-literal function identity.
 */
function objectLiteralAssignedPath(ts, objectLiteral) {
  const parent = objectLiteral.parent;
  if (!parent) return "";
  if (ts.isVariableDeclaration(parent) && ts.isIdentifier(parent.name)) return parent.name.text;
  if (ts.isPropertyDeclaration?.(parent)) return nameNodeText(ts, objectLiteral.getSourceFile(), parent.name);
  if (ts.isPropertyAssignment(parent)) {
    const owner = objectLiteralAssignedPath(ts, parent.parent);
    const property = nameNodeText(ts, objectLiteral.getSourceFile(), parent.name);
    return owner && property ? `${owner}.${property}` : property;
  }
  if (ts.isBinaryExpression(parent) && parent.right === objectLiteral) return exprPath(ts, parent.left);
  if (ts.isReturnStatement?.(parent)) return "";
  return "";
}
