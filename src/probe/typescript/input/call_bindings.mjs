/** Resolve local call bindings using a single in-memory TypeScript source file. */
import path from "node:path";
import { isFunctionValue, walkAst } from "../support/typescript.mjs";

export function unwrapExpression(ts, expression) {
  let current = expression;
  while (
    current &&
    (ts.isParenthesizedExpression(current) ||
      ts.isAsExpression(current) ||
      ts.isTypeAssertionExpression(current) ||
      ts.isNonNullExpression(current) ||
      ts.isSatisfiesExpression?.(current))
  ) {
    current = current.expression;
  }
  return current;
}

export function callResolver(ts, sourceFile) {
  const filename = path.resolve(sourceFile.fileName);
  const isSource = (file) => path.resolve(file) === filename;
  const program = ts.createProgram(
    [sourceFile.fileName],
    {
      noLib: true,
      noResolve: true,
      allowJs: true,
      target: ts.ScriptTarget.Latest,
    },
    {
      getSourceFile: (file) => (isSource(file) ? sourceFile : undefined),
      fileExists: isSource,
      readFile: (file) => (isSource(file) ? sourceFile.text : undefined),
      getDefaultLibFileName: () => "",
      getCurrentDirectory: () => process.cwd(),
      getCanonicalFileName: (file) => file,
      useCaseSensitiveFileNames: () => true,
      getNewLine: () => "\n",
      writeFile() {},
    },
  );
  const checker = program.getTypeChecker();
  const symbolAt = (node) => {
    if (!ts.isElementAccessExpression(node))
      return checker.getSymbolAtLocation(node);
    const key = checker.getTypeAtLocation(node.argumentExpression);
    return key.flags & (ts.TypeFlags.StringLiteral | ts.TypeFlags.NumberLiteral)
      ? checker.getPropertyOfType(
          checker.getTypeAtLocation(node.expression),
          String(key.value),
        )
      : undefined;
  };
  const writes = new Set();
  const markWrite = (node) => {
    if (!node) return;
    if (
      ts.isIdentifier(node) ||
      ts.isPropertyAccessExpression(node) ||
      ts.isElementAccessExpression(node)
    ) {
      writes.add(symbolAt(node));
    } else if (ts.isBinaryExpression(node)) {
      markWrite(node.left);
    } else if (ts.isPropertyAssignment(node)) {
      markWrite(node.initializer);
    } else {
      ts.forEachChild(node, markWrite);
    }
  };
  walkAst(ts, sourceFile, (node) => {
    if (
      ts.isBinaryExpression(node) &&
      node.operatorToken.kind >= ts.SyntaxKind.FirstAssignment &&
      node.operatorToken.kind <= ts.SyntaxKind.LastAssignment
    ) {
      markWrite(node.left);
    } else if (
      (ts.isPrefixUnaryExpression(node) || ts.isPostfixUnaryExpression(node)) &&
      [ts.SyntaxKind.PlusPlusToken, ts.SyntaxKind.MinusMinusToken].includes(
        node.operator,
      )
    ) {
      markWrite(node.operand);
    } else if (
      (ts.isForInStatement(node) || ts.isForOfStatement(node)) &&
      !ts.isVariableDeclarationList(node.initializer)
    ) {
      markWrite(node.initializer);
    }
  });

  const resolveSymbol = (symbol, seen) => {
    if (!symbol || writes.has(symbol) || seen.has(symbol)) return undefined;
    seen = new Set([...seen, symbol]);
    const bodies = (symbol.declarations || []).filter((node) => node.body);
    if (bodies.length > 1) return undefined;
    const declaration =
      bodies[0] || symbol.valueDeclaration || symbol.declarations?.[0];
    if (!declaration) return undefined;
    if (
      ts.isVariableDeclaration(declaration) ||
      ts.isPropertyAssignment(declaration) ||
      ts.isPropertyDeclaration(declaration)
    ) {
      return declaration.initializer
        ? resolve(declaration.initializer, seen)
        : declaration;
    }
    if (ts.isShorthandPropertyAssignment(declaration)) {
      return resolveSymbol(
        checker.getShorthandAssignmentValueSymbol(declaration),
        seen,
      );
    }
    if (ts.isBindingElement(declaration)) {
      const pattern = declaration.parent;
      const initializer = pattern.parent?.initializer;
      if (
        ts.isObjectBindingPattern(pattern) &&
        initializer &&
        !declaration.dotDotDotToken &&
        !declaration.initializer
      ) {
        const key = declaration.propertyName || declaration.name;
        if (ts.isIdentifier(key) || ts.isStringLiteral(key)) {
          return resolveSymbol(
            checker.getPropertyOfType(
              checker.getTypeAtLocation(initializer),
              key.text,
            ),
            seen,
          );
        }
      }
      return declaration;
    }
    // Type-only members do not identify their eventual runtime implementation.
    if (
      ts.isMethodSignature(declaration) ||
      ts.isPropertySignature(declaration)
    )
      return undefined;
    return declaration;
  };
  const resolve = (expression, seen = new Set()) => {
    const node = unwrapExpression(ts, expression);
    if (!node) return undefined;
    if (
      isFunctionValue(ts, node) ||
      ts.isClassExpression(node) ||
      ts.isLiteralExpression(node)
    )
      return node;
    if (
      ts.isIdentifier(node) ||
      ts.isPropertyAccessExpression(node) ||
      ts.isElementAccessExpression(node)
    ) {
      return resolveSymbol(symbolAt(node), seen);
    }
    return undefined;
  };
  return resolve;
}
