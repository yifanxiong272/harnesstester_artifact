import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const workflowRequire = createRequire(import.meta.url);

function missingTypeScript(error) {
  return (
    error?.code === "MODULE_NOT_FOUND" &&
    /^Cannot find module ['"]typescript['"]/u.test(String(error.message ?? ""))
  );
}

/** Prefer the subject compiler, then use the study workspace dependency. */
export function loadTypeScript(projectRoot) {
  try {
    return createRequire(path.join(projectRoot, "package.json"))("typescript");
  } catch (error) {
    if (!missingTypeScript(error)) {
      throw error;
    }
  }
  try {
    return workflowRequire("typescript");
  } catch (error) {
    if (!missingTypeScript(error)) {
      throw error;
    }
    throw new Error(
      "TypeScript is not installed in the subject or study workspace; run npm install from the study root",
      { cause: error },
    );
  }
}

function scriptKind(ts, filepath) {
  if (filepath.endsWith(".tsx")) {
    return ts.ScriptKind.TSX;
  }
  if (filepath.endsWith(".jsx")) {
    return ts.ScriptKind.JSX;
  }
  if (
    filepath.endsWith(".js") ||
    filepath.endsWith(".mjs") ||
    filepath.endsWith(".cjs")
  ) {
    return ts.ScriptKind.JS;
  }
  return ts.ScriptKind.TS;
}

/** Parse source using the supplied TypeScript compiler. */
export function parseTypeScript(ts, filepath, source) {
  return ts.createSourceFile(
    filepath,
    source,
    ts.ScriptTarget.Latest,
    true,
    scriptKind(ts, filepath),
  );
}

export function parseProjectFile(
  projectRoot,
  filepath,
  typescript = loadTypeScript(projectRoot),
) {
  const source = fs.readFileSync(path.join(projectRoot, filepath), "utf8");
  return {
    source,
    sourceFile: parseTypeScript(typescript, filepath, source),
    typescript,
  };
}

function hasModifier(ts, node, kind) {
  return Boolean(
    ts.getModifiers?.(node)?.some((modifier) => modifier.kind === kind),
  );
}

function bindingNames(ts, name, output) {
  if (ts.isIdentifier(name)) {
    output.add(name.text);
    return;
  }
  for (const element of name.elements ?? []) {
    if (!ts.isOmittedExpression(element)) {
      bindingNames(ts, element.name, output);
    }
  }
}

/** Return names that this module exports explicitly. Star re-exports stay unresolved. */
export function exportedNames(ts, sourceFile) {
  const names = new Set();
  for (const statement of sourceFile.statements) {
    if (ts.isExportAssignment(statement)) {
      names.add(statement.isExportEquals ? "export=" : "default");
      continue;
    }
    if (ts.isExportDeclaration(statement)) {
      const clause = statement.exportClause;
      if (clause && ts.isNamedExports(clause)) {
        for (const element of clause.elements) {
          names.add(element.name.text);
        }
      } else if (clause && ts.isNamespaceExport?.(clause)) {
        names.add(clause.name.text);
      }
      continue;
    }
    if (!hasModifier(ts, statement, ts.SyntaxKind.ExportKeyword)) {
      continue;
    }
    if (hasModifier(ts, statement, ts.SyntaxKind.DefaultKeyword)) {
      names.add("default");
      continue;
    }
    if (ts.isVariableStatement(statement)) {
      for (const declaration of statement.declarationList.declarations) {
        bindingNames(ts, declaration.name, names);
      }
    } else if (statement.name && ts.isIdentifier(statement.name)) {
      names.add(statement.name.text);
    }
  }
  return [...names].sort();
}

function nodeName(ts, node) {
  const name = node.name;
  if (!name) {
    return ts.isConstructorDeclaration(node) ? "constructor" : null;
  }
  if (
    ts.isIdentifier(name) ||
    ts.isStringLiteral(name) ||
    ts.isNumericLiteral(name)
  ) {
    return name.text;
  }
  return null;
}

function declarationKind(ts, node) {
  if (ts.isClassDeclaration(node) || ts.isClassExpression(node)) return "class";
  if (ts.isFunctionDeclaration(node) || ts.isFunctionExpression(node))
    return "function";
  if (ts.isMethodDeclaration(node)) return "method";
  if (ts.isGetAccessorDeclaration(node) || ts.isSetAccessorDeclaration(node))
    return "accessor";
  if (ts.isConstructorDeclaration(node)) return "constructor";
  if (ts.isInterfaceDeclaration(node)) return "interface";
  if (ts.isTypeAliasDeclaration(node)) return "type";
  if (ts.isEnumDeclaration(node)) return "enum";
  if (ts.isModuleDeclaration(node)) return "module";
  if (ts.isVariableDeclaration(node)) return "variable";
  if (ts.isPropertyDeclaration(node)) return "property";
  return null;
}

/**
 * Index declarations by lexical qualname.
 *
 * The index follows declared class/function/module scopes. A request for
 * `Client.send` therefore cannot silently bind to another `send` declaration.
 */
function declarationIndex(ts, sourceFile) {
  const declarations = [];

  function visit(node, scope) {
    const kind = declarationKind(ts, node);
    const name = kind ? nodeName(ts, node) : null;
    const nextScope = name ? [...scope, name] : scope;
    if (name) {
      declarations.push({ kind, name, qualname: nextScope.join("."), node });
    }

    if (ts.isVariableDeclaration(node)) {
      return;
    }
    ts.forEachChild(node, (child) => visit(child, nextScope));
  }

  for (const statement of sourceFile.statements) {
    visit(statement, []);
  }
  return declarations;
}

/** Resolve an exact lexical qualname without name-based fallback. */
export function resolveDeclaration(ts, sourceFile, qualname) {
  const requested = String(qualname ?? "").trim();
  if (!requested) {
    return { status: "invalid", matches: [] };
  }
  const declarations = declarationIndex(ts, sourceFile);
  const exact = declarations.filter((item) => item.qualname === requested);
  return exact.length > 0
    ? uniqueDeclaration(exact)
    : { status: "not_found", matches: [] };
}

function uniqueDeclaration(matches) {
  if (matches.length === 1) {
    return { status: "found", matches };
  }
  const implementations = matches.filter((item) => item.node.body);
  return implementations.length === 1
    ? { status: "found", matches: implementations }
    : { status: "ambiguous", matches };
}

export function nodeLineRange(sourceFile, node) {
  return {
    startLine:
      sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile)).line +
      1,
    endLine: sourceFile.getLineAndCharacterOfPosition(node.end).line + 1,
  };
}

/** Return the innermost declaration containing an exact runtime source line. */
export function declarationAtLine(ts, sourceFile, line) {
  const matches = declarationIndex(ts, sourceFile)
    .map((item) => ({
      ...item,
      range: nodeLineRange(sourceFile, item.node),
    }))
    .filter(
      (item) => item.range.startLine <= line && line <= item.range.endLine,
    )
    .sort(
      (left, right) =>
        left.range.endLine -
          left.range.startLine -
          (right.range.endLine - right.range.startLine) ||
        right.range.startLine - left.range.startLine ||
        left.qualname.localeCompare(right.qualname),
    );
  return matches[0] ?? null;
}
