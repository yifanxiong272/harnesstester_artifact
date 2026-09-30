import { exprPath, isFunctionLikeWithBody } from "../syntax.mjs";
import { isClassLike } from "./names.mjs";

/** Collect assignment paths within one function, excluding nested units. */
export function collectAssignedNames(ts, functionNode) {
  const assigned = new Set();

  function visit(node) {
    if (node !== functionNode && (isFunctionLikeWithBody(ts, node) || isClassLike(ts, node))) return;

    if (ts.isVariableDeclaration(node)) {
      collectBindingNames(ts, node.name, assigned);
    } else if (ts.isBinaryExpression(node) && assignmentOperatorKinds(ts).has(node.operatorToken.kind)) {
      const pathText = exprPath(ts, node.left);
      if (pathText) assigned.add(pathText);
      collectBindingNames(ts, node.left, assigned);
    } else if (ts.isParameter(node)) {
      collectBindingNames(ts, node.name, assigned);
    } else if (ts.isPrefixUnaryExpression(node) || ts.isPostfixUnaryExpression(node)) {
      const pathText = exprPath(ts, node.operand);
      if (pathText) assigned.add(pathText);
    } else if (ts.isForOfStatement?.(node) || ts.isForInStatement?.(node)) {
      collectLoopBindingNames(ts, node, assigned);
    }

    ts.forEachChild(node, visit);
  }

  visit(functionNode);
  return [...assigned].sort();
}

/** Collect declarations separately from assignments for closure resolution.
 * Assigning an outer variable does not declare a local name.
 */
export function collectDeclaredNames(ts, functionNode) {
  const declared = new Set();

  function visit(node) {
    if (node !== functionNode && (isFunctionLikeWithBody(ts, node) || isClassLike(ts, node))) return;
    if (ts.isVariableDeclaration(node) || ts.isParameter(node)) collectBindingNames(ts, node.name, declared);
    ts.forEachChild(node, visit);
  }

  visit(functionNode);
  return [...declared].sort();
}

/** Read assignment operators available in this compiler's SyntaxKind. */
export function assignmentOperatorKinds(ts) {
  return new Set([
    ts.SyntaxKind.EqualsToken,
    ts.SyntaxKind.PlusEqualsToken,
    ts.SyntaxKind.MinusEqualsToken,
    ts.SyntaxKind.AsteriskEqualsToken,
    ts.SyntaxKind.AsteriskAsteriskEqualsToken,
    ts.SyntaxKind.SlashEqualsToken,
    ts.SyntaxKind.PercentEqualsToken,
    ts.SyntaxKind.AmpersandEqualsToken,
    ts.SyntaxKind.BarEqualsToken,
    ts.SyntaxKind.CaretEqualsToken,
    ts.SyntaxKind.LessThanLessThanEqualsToken,
    ts.SyntaxKind.GreaterThanGreaterThanEqualsToken,
    ts.SyntaxKind.GreaterThanGreaterThanGreaterThanEqualsToken,
    ts.SyntaxKind.AmpersandAmpersandEqualsToken,
    ts.SyntaxKind.BarBarEqualsToken,
    ts.SyntaxKind.QuestionQuestionEqualsToken,
  ].filter((kind) => kind !== undefined));
}

/** Collect identifier names introduced by a binding pattern. */
export function collectBindingNames(ts, name, out) {
  if (!name) return;
  if (ts.isIdentifier(name)) {
    out.add(name.text);
    return;
  }
  if (ts.isObjectBindingPattern(name) || ts.isArrayBindingPattern(name)) {
    for (const element of name.elements || []) {
      if (ts.isBindingElement(element)) collectBindingNames(ts, element.name, out);
    }
  }
}

/** Read the local identifier in a CommonJS destructuring binding. */
export function bindingIdentifierName(ts, name) {
  if (ts.isIdentifier(name)) return name.text;
  return "";
}

/** Read the imported property in a CommonJS destructuring binding. */
export function bindingPropertyName(ts, propertyName) {
  if (ts.isIdentifier(propertyName)) return propertyName.text;
  if (ts.isStringLiteralLike?.(propertyName) || ts.isNumericLiteral(propertyName)) return propertyName.text;
  return "";
}

/** Collect for-of and for-in initializer bindings. */
function collectLoopBindingNames(ts, node, assigned) {
  if (ts.isVariableDeclarationList(node.initializer)) {
    for (const declaration of node.initializer.declarations) collectBindingNames(ts, declaration.name, assigned);
    return;
  }
  const pathText = exprPath(ts, node.initializer);
  if (pathText) assigned.add(pathText);
}
