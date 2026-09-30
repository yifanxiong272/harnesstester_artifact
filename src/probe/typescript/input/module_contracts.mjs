import fs from "node:fs";
import path from "node:path";

import { safeRelativePath } from "../support/path_safety.mjs";
import {
  loadTypeScript,
  parseSource,
  memberName,
  hasModifier,
  compactStatement,
  stripSourceExtension,
} from "../support/typescript.mjs";

function safeGeneratedRoots(roots) {
  const result = [];
  for (const root of roots || []) {
    try {
      result.push(safeRelativePath(root).replace(/\/$/u, ""));
    } catch {
      // Invalid generated roots are handled by preflight. Contract extraction
      // should stay best-effort and non-fatal.
    }
  }
  return result.length ? result : ["test/generated/benchmarkbr"];
}

function importSpecifiers(filepath, generatedTestRoots) {
  const target = stripSourceExtension(filepath);
  const sourceExtension = path.posix.extname(filepath);
  const values = new Map();
  for (const root of safeGeneratedRoots(generatedTestRoots)) {
    const generatedDir = root.replace(/\/$/u, "");
    let rel = path.posix.relative(generatedDir, target);
    if (!rel.startsWith(".")) {
      rel = `./${rel}`;
    }
    for (const specifier of [rel, `${rel}.js`, `${rel}${sourceExtension}`]) {
      if (!values.has(specifier)) {
        values.set(specifier, { from_generated_root: generatedDir, specifier });
      }
    }
  }
  return [...values.values()].slice(0, 12);
}

function declarationKind(ts, node) {
  for (const [matches, kind] of [
    [ts.isFunctionDeclaration, "function"],
    [ts.isClassDeclaration, "class"],
    [ts.isInterfaceDeclaration, "interface"],
    [ts.isTypeAliasDeclaration, "type"],
    [ts.isEnumDeclaration, "enum"],
    [ts.isVariableStatement, "variable"],
  ]) {
    if (matches(node)) return kind;
  }
  return "symbol";
}

function exportedDeclarationNames(ts, statement) {
  if (ts.isVariableStatement(statement)) {
    return (statement.declarationList?.declarations || [])
      .filter((declaration) => ts.isIdentifier(declaration.name))
      .map((declaration) => declaration.name.text);
  }
  const name = memberName(statement);
  return name ? [name] : [];
}

function namedExportElements(ts, clause) {
  if (!clause || !ts.isNamedExports(clause)) {
    return [];
  }
  return clause.elements.map((item) => ({
    name: item.name.text,
    property_name: item.propertyName?.text || "",
  }));
}

function exportRecords(ts, sourceFile, limit = 80) {
  const records = [];
  const push = (record) => {
    if (records.length < limit) {
      records.push(record);
    }
  };

  for (const statement of sourceFile.statements) {
    if (ts.isExportDeclaration(statement)) {
      const specifier = statement.moduleSpecifier
        ? statement.moduleSpecifier.text
        : "";
      const names = namedExportElements(ts, statement.exportClause);
      push({
        kind: specifier
          ? names.length
            ? "named_reexport"
            : "export_star"
          : "named_export_list",
        source: specifier,
        names,
        statement: compactStatement(statement, sourceFile),
      });
      continue;
    }

    if (ts.isExportAssignment(statement)) {
      push({
        kind: statement.isExportEquals ? "export_equals" : "default",
        expression: compactStatement(statement.expression, sourceFile, 120),
        statement: compactStatement(statement, sourceFile),
      });
      continue;
    }

    if (!hasModifier(ts, statement, ts.SyntaxKind.ExportKeyword)) {
      continue;
    }

    const isDefault = hasModifier(ts, statement, ts.SyntaxKind.DefaultKeyword);
    const names = exportedDeclarationNames(ts, statement);
    const declaration = {
      declaration_kind: declarationKind(ts, statement),
      statement: compactStatement(statement, sourceFile),
    };
    if (isDefault) {
      push({
        kind: "default",
        local_name: names[0] || "",
        ...declaration,
      });
    } else {
      for (const name of names) {
        push({
          kind: "named",
          name,
          ...declaration,
        });
      }
    }
  }
  return records;
}

export function moduleContracts(
  projectRoot,
  files,
  { generatedTestRoots = [], limit = 24 } = {},
) {
  const ts = loadTypeScript(projectRoot);
  if (!ts) {
    return [];
  }
  const contracts = [];
  const seen = new Set();
  for (const file of files || []) {
    let rel = "";
    try {
      rel = safeRelativePath(file);
    } catch {
      continue;
    }
    if (seen.has(rel)) {
      continue;
    }
    seen.add(rel);
    const full = path.join(projectRoot, rel);
    if (!fs.existsSync(full)) continue;
    let text;
    try {
      text = fs.readFileSync(full, "utf8");
    } catch {
      continue;
    }
    const sourceFile = parseSource(ts, rel, text);
    contracts.push({
      filepath: rel,
      suggested_imports: importSpecifiers(rel, generatedTestRoots),
      exports: exportRecords(ts, sourceFile),
    });
    if (contracts.length >= limit) {
      break;
    }
  }
  return contracts;
}
