import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

import { callResolver, unwrapExpression } from "./call_bindings.mjs";
import { safeRelativePath } from "../support/path_safety.mjs";
import {
  loadTypeScript,
  parseSource,
  walkAst,
  nodeRange,
  memberName,
  hasModifier,
  isFunctionValue,
} from "../support/typescript.mjs";

const MAX_ENTRYPOINT_SIGNATURE_CHARS = 4_000;
const MAX_ROUTES_PER_TARGET = 4;

function declarationName(node) {
  return node?.name?.getText?.() || "";
}

function explicitExports(ts, sourceFile) {
  const named = new Map();
  const defaults = new Set();
  for (const statement of sourceFile.statements) {
    if (
      ts.isExportDeclaration(statement) &&
      !statement.moduleSpecifier &&
      statement.exportClause &&
      ts.isNamedExports(statement.exportClause) &&
      !statement.isTypeOnly
    ) {
      for (const element of statement.exportClause.elements) {
        if (element.isTypeOnly) {
          continue;
        }
        const local = element.propertyName?.text || element.name.text;
        const exported = element.name.text;
        const values = named.get(local) || [];
        values.push(exported);
        named.set(local, values);
      }
    }
    if (ts.isExportAssignment(statement) && !statement.isExportEquals) {
      const expression = statement.expression;
      if (ts.isIdentifier(expression)) {
        defaults.add(expression.text);
      }
    }
  }
  return { named, defaults };
}

function declarationEntrypoints(ts, node, localName, exports) {
  const values = [];
  if (hasModifier(ts, node, ts.SyntaxKind.DefaultKeyword)) {
    values.push({ import_kind: "default", export_name: "default" });
  } else if (hasModifier(ts, node, ts.SyntaxKind.ExportKeyword)) {
    values.push({ import_kind: "named", export_name: localName });
  }
  for (const exported of exports.named.get(localName) || []) {
    values.push({ import_kind: "named", export_name: exported });
  }
  if (exports.defaults.has(localName)) {
    values.push({ import_kind: "default", export_name: "default" });
  }
  return dedupeEntrypoints(values);
}

function dedupeEntrypoints(values) {
  const seen = new Set();
  return values.filter((item) => {
    const key = `${item.import_kind}:${item.export_name}:${(item.member_path || []).join(".")}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function isPublicClassMember(ts, node) {
  if (node.name && ts.isPrivateIdentifier(node.name)) {
    return false;
  }
  return (
    !hasModifier(ts, node, ts.SyntaxKind.PrivateKeyword) &&
    !hasModifier(ts, node, ts.SyntaxKind.ProtectedKeyword)
  );
}

function classMemberEntrypoints(ts, classEntrypoints, node) {
  if (!isPublicClassMember(ts, node)) {
    return [];
  }
  const name = ts.isConstructorDeclaration(node)
    ? "constructor"
    : memberName(node);
  const isStatic = hasModifier(ts, node, ts.SyntaxKind.StaticKeyword);
  return classEntrypoints.map((entrypoint) => ({
    ...entrypoint,
    member_path: name === "constructor" ? [] : [name],
    invocation_kind:
      name === "constructor"
        ? "constructor"
        : isStatic
          ? "static_method"
          : "instance_method",
  }));
}

function objectMemberEntrypoints(containerEntrypoints, memberPath) {
  return containerEntrypoints.map((entrypoint) => ({
    ...entrypoint,
    member_path: memberPath,
    invocation_kind: "object_member",
  }));
}

function recordCallableNode(ts, record) {
  if (!ts.isVariableStatement(record.node)) {
    return record.node;
  }
  const declaration = record.node.declarationList.declarations.find(
    (item) =>
      ts.isIdentifier(item.name) && item.name.text === record.local_name,
  );
  return declaration?.initializer || record.node;
}

function directlyReturnedClassNames(ts, record, resolve, classes) {
  const callable = recordCallableNode(ts, record);
  const names = new Set();
  const collectNewExpression = (expression) => {
    const unwrapped = unwrapExpression(ts, expression);
    if (unwrapped && ts.isNewExpression(unwrapped)) {
      const binding = resolve(unwrapped.expression);
      if (classes.has(binding)) {
        names.add(classes.get(binding));
      } else if (!binding && ts.isIdentifier(unwrapped.expression)) {
        names.add(unwrapped.expression.text);
      }
    }
  };
  if (ts.isArrowFunction(callable) && !ts.isBlock(callable.body)) {
    collectNewExpression(callable.body);
    return names;
  }
  const body = callable.body;
  if (!body || !ts.isBlock(body)) {
    return names;
  }
  walkAst(ts, body, (node) => {
    if (
      node !== body &&
      (ts.isFunctionDeclaration(node) ||
        isFunctionValue(ts, node) ||
        ts.isMethodDeclaration(node))
    ) {
      return false;
    }
    if (ts.isReturnStatement(node) && node.expression) {
      collectNewExpression(node.expression);
      return false;
    }
  });
  return names;
}

function linkFactoryMemberEntrypoints(ts, records, resolve) {
  const classes = new Map(
    records
      .filter((record) => record.kind === "class")
      .map((record) => [record.node, record.qualname]),
  );
  const methodsByClass = new Map();
  for (const record of records) {
    if (record.kind !== "class_method" || record.local_name === "constructor") {
      continue;
    }
    const methods = methodsByClass.get(record.scope) || [];
    methods.push(record);
    methodsByClass.set(record.scope, methods);
  }
  for (const factory of records) {
    if (factory.kind !== "function" || factory.entrypoints.length === 0) {
      continue;
    }
    for (const className of directlyReturnedClassNames(
      ts,
      factory,
      resolve,
      classes,
    )) {
      for (const method of methodsByClass.get(className) || []) {
        if (
          !isPublicClassMember(ts, method.node) ||
          hasModifier(ts, method.node, ts.SyntaxKind.StaticKeyword)
        ) {
          continue;
        }
        method.entrypoints = dedupeEntrypoints([
          ...method.entrypoints,
          ...factory.entrypoints.map((entrypoint) => ({
            ...entrypoint,
            member_path: [method.local_name],
            invocation_kind: "factory_method",
            factory_record_id: factory.id,
          })),
        ]);
      }
    }
  }
}

function collectCallableRecords(ts, sourceFile, exports, resolve) {
  const records = [];
  let sequence = 0;
  const add = ({
    node,
    qualname,
    localName,
    kind,
    entrypoints = [],
    scope = "module",
  }) => {
    const range = nodeRange(sourceFile, node);
    const record = {
      id: `callable-${String(++sequence).padStart(4, "0")}`,
      node,
      qualname,
      local_name: localName,
      kind,
      scope,
      entrypoints: dedupeEntrypoints(entrypoints),
      calls: new Set(),
      ...range,
    };
    records.push(record);
    return record;
  };

  const collectNested = (node, parentRecord, parents) => {
    const visit = (child) => {
      if (isFunctionValue(ts, child) && child !== parentRecord.node) {
        const range = nodeRange(sourceFile, child);
        const name = `<callback@${range.start_line}>`;
        const nested = add({
          node: child,
          qualname: [...parents, name].filter(Boolean).join("."),
          localName: name,
          kind: "callback",
          scope: parentRecord.scope,
        });
        parentRecord.calls.add(nested.id);
      }
    };
    ts.forEachChild(node, (child) => walkAst(ts, child, visit));
  };

  const collectObjectMethods = (
    object,
    localName,
    entrypoints,
    parentPath = [],
    recursive = true,
  ) => {
    for (const property of object.properties) {
      const name = memberName(property);
      if (!name) {
        continue;
      }
      const memberPath = [...parentPath, name];
      if (
        ts.isMethodDeclaration(property) ||
        (ts.isPropertyAssignment(property) &&
          isFunctionValue(ts, property.initializer))
      ) {
        const record = add({
          node: property,
          qualname: `${localName}.${memberPath.join(".")}`,
          localName: name,
          kind: "object_method",
          scope: localName,
          entrypoints: objectMemberEntrypoints(entrypoints, memberPath),
        });
        collectNested(property, record, [localName, ...memberPath]);
        continue;
      }
      if (recursive && ts.isPropertyAssignment(property)) {
        const initializer = unwrapExpression(ts, property.initializer);
        if (ts.isObjectLiteralExpression(initializer)) {
          collectObjectMethods(initializer, localName, entrypoints, memberPath);
        }
      }
    }
  };

  for (const statement of sourceFile.statements) {
    if (ts.isFunctionDeclaration(statement)) {
      const localName = declarationName(statement) || "<default>";
      const record = add({
        node: statement,
        qualname: localName,
        localName,
        kind: "function",
        entrypoints: declarationEntrypoints(ts, statement, localName, exports),
      });
      collectNested(statement, record, [localName]);
      continue;
    }

    if (ts.isVariableStatement(statement)) {
      const statementExported = hasModifier(
        ts,
        statement,
        ts.SyntaxKind.ExportKeyword,
      );
      for (const declaration of statement.declarationList.declarations) {
        if (!ts.isIdentifier(declaration.name) || !declaration.initializer) {
          continue;
        }
        const localName = declaration.name.text;
        const entrypoints = statementExported
          ? [{ import_kind: "named", export_name: localName }]
          : declarationEntrypoints(ts, statement, localName, exports);
        if (isFunctionValue(ts, declaration.initializer)) {
          const record = add({
            node: statement,
            qualname: localName,
            localName,
            kind: "function",
            entrypoints,
          });
          collectNested(declaration.initializer, record, [localName]);
          continue;
        }
        if (ts.isObjectLiteralExpression(declaration.initializer)) {
          collectObjectMethods(declaration.initializer, localName, entrypoints);
        }
      }
      continue;
    }

    if (ts.isClassDeclaration(statement) && statement.name) {
      const className = statement.name.text;
      const classEntrypoints = declarationEntrypoints(
        ts,
        statement,
        className,
        exports,
      );
      add({
        node: statement,
        qualname: className,
        localName: className,
        kind: "class",
        scope: className,
        entrypoints: classEntrypoints.map((entrypoint) => ({
          ...entrypoint,
          invocation_kind: "constructor",
        })),
      });
      for (const member of statement.members) {
        if (
          !ts.isMethodDeclaration(member) &&
          !ts.isConstructorDeclaration(member) &&
          !ts.isGetAccessorDeclaration(member) &&
          !ts.isSetAccessorDeclaration(member) &&
          !(
            ts.isPropertyDeclaration(member) &&
            member.initializer &&
            isFunctionValue(ts, member.initializer)
          )
        ) {
          continue;
        }
        const name = ts.isConstructorDeclaration(member)
          ? "constructor"
          : memberName(member);
        if (!name) {
          continue;
        }
        const record = add({
          node: member,
          qualname: `${className}.${name}`,
          localName: name,
          kind: "class_method",
          scope: className,
          entrypoints: classMemberEntrypoints(ts, classEntrypoints, member),
        });
        collectNested(member, record, [className, name]);
      }
      continue;
    }

    if (
      ts.isExportAssignment(statement) &&
      !statement.isExportEquals &&
      ts.isObjectLiteralExpression(statement.expression)
    ) {
      // Default object exports expose direct members; named objects recurse.
      collectObjectMethods(
        statement.expression,
        "default",
        [{ import_kind: "default", export_name: "default" }],
        [],
        false,
      );
    }
  }
  linkFactoryMemberEntrypoints(ts, records, resolve);
  return records;
}

function indexRecordNames(records) {
  const names = new Map();
  const add = (name, id) => {
    if (!name) {
      return;
    }
    const values = names.get(name) || [];
    values.push(id);
    names.set(name, values);
  };
  for (const record of records) {
    add(record.local_name, record.id);
    add(record.qualname, record.id);
    add(`${record.scope}.${record.local_name}`, record.id);
  }
  return names;
}

function collectCallEdges(ts, records, resolve) {
  // All targets in a file share the same call graph and source-order callers.
  const names = indexRecordNames(records);
  const definitions = new Map();
  const addDefinition = (node, id) => {
    if (!node) return;
    const ids = definitions.get(node) || new Set();
    ids.add(id);
    definitions.set(node, ids);
  };
  for (const record of records) {
    const callable = recordCallableNode(ts, record);
    for (const node of [record.node, callable, callable.initializer]) {
      addDefinition(node, record.id);
    }
    // Overload signatures and their implementation share the same binding.
    if (
      ts.isFunctionDeclaration(callable) ||
      ts.isMethodDeclaration(callable)
    ) {
      addDefinition(resolve(callable.name), record.id);
    }
  }
  const callableRoots = new Map(
    records.map((record) => [record.node, record.id]),
  );
  const reverse = new Map();
  const namedReverse = new Map();
  for (const record of records) {
    const namedCalls = new Set(record.calls);
    walkAst(ts, record.node, (node) => {
      const nestedRecordId = callableRoots.get(node);
      if (
        node !== record.node &&
        nestedRecordId &&
        nestedRecordId !== record.id
      ) {
        return false;
      }
      if (ts.isCallExpression(node) || ts.isNewExpression(node)) {
        const callee = node.expression;
        let keys = [];
        if (ts.isIdentifier(callee)) {
          keys = [callee.text];
        } else if (ts.isPropertyAccessExpression(callee)) {
          const receiver = callee.expression;
          if (receiver.kind === ts.SyntaxKind.ThisKeyword) {
            keys = [`${record.scope}.${callee.name.text}`];
          } else if (ts.isIdentifier(receiver)) {
            keys = [`${receiver.text}.${callee.name.text}`, callee.name.text];
          }
        }
        const namedCandidates = new Set(
          keys.flatMap((key) => names.get(key) || []),
        );
        const binding = resolve(callee);
        const candidates = binding
          ? definitions.get(binding) || []
          : namedCandidates;
        for (const id of candidates) {
          if (id !== record.id) {
            record.calls.add(id);
            if (namedCandidates.has(id)) namedCalls.add(id);
          }
        }
      }
    });
    for (const callee of record.calls) {
      const callers = reverse.get(callee) || [];
      callers.push(record.id);
      reverse.set(callee, callers);
    }
    for (const callee of namedCalls) {
      const callers = namedReverse.get(callee) || [];
      callers.push(record.id);
      namedReverse.set(callee, callers);
    }
  }
  return {
    byId: new Map(records.map((record) => [record.id, record])),
    reverse,
    namedReverse,
  };
}

function targetRecord(unit, records) {
  const exact = records.find(
    (record) =>
      record.start_line === Number(unit.start_line) &&
      record.end_line === Number(unit.end_line) &&
      (record.qualname === unit.qualname ||
        record.local_name === unit.qualname),
  );
  if (exact) {
    return exact;
  }
  return (
    records
      .filter(
        (record) =>
          record.start_line <= Number(unit.start_line) &&
          Number(unit.end_line) <= record.end_line,
      )
      .sort(
        (a, b) =>
          a.end_line - a.start_line - (b.end_line - b.start_line) ||
          a.start_line - b.start_line,
      )[0] || null
  );
}

function entrypointSignature(ts, sourceFile, record) {
  let callable = record.node;
  if (ts.isVariableStatement(callable)) {
    const declaration = callable.declarationList.declarations.find(
      (item) => item.initializer && isFunctionValue(ts, item.initializer),
    );
    if (declaration?.initializer) {
      callable = declaration.initializer;
    }
  } else if (
    ts.isPropertyAssignment(callable) &&
    isFunctionValue(ts, callable.initializer)
  ) {
    callable = callable.initializer;
  }
  if (ts.isClassDeclaration(callable)) {
    const className = callable.name?.text || record.local_name;
    const constructor = callable.members.find((member) =>
      ts.isConstructorDeclaration(member),
    );
    const parameters = constructor
      ? constructor.parameters
          .map((parameter) => parameter.getText(sourceFile))
          .join(", ")
      : "";
    return `class ${className} { constructor(${parameters}) }`;
  }
  const body = callable.body;
  const signature = body
    ? `${sourceFile.text.slice(record.node.getStart(sourceFile), body.getStart(sourceFile)).trimEnd()} {}`
    : record.node.getText(sourceFile);
  if (signature.length > MAX_ENTRYPOINT_SIGNATURE_CHARS) {
    return "";
  }
  return signature;
}

function routesToTarget(ts, sourceFile, { byId, reverse }, target) {
  const queue = [{ id: target.id, reversePath: [target.id] }];
  const bestDepth = new Map([[target.id, 0]]);
  const routes = [];
  while (queue.length > 0 && routes.length < MAX_ROUTES_PER_TARGET) {
    const item = queue.shift();
    const record = byId.get(item.id);
    if (!record) {
      continue;
    }
    for (const entrypoint of record.entrypoints) {
      const callableSignature = entrypointSignature(ts, sourceFile, record);
      const factory = entrypoint.factory_record_id
        ? byId.get(entrypoint.factory_record_id)
        : null;
      const factorySignature = factory
        ? entrypointSignature(ts, sourceFile, factory)
        : "";
      const combinedSignature = [factorySignature, callableSignature]
        .filter(Boolean)
        .join("\n");
      const signature =
        combinedSignature.length <= MAX_ENTRYPOINT_SIGNATURE_CHARS
          ? combinedSignature
          : callableSignature;
      if (!signature) {
        continue;
      }
      const callPath = [
        factory?.qualname || "",
        ...[...item.reversePath]
          .reverse()
          .map((id) => byId.get(id)?.qualname || ""),
      ].filter(Boolean);
      routes.push({ record, entrypoint, callPath, signature });
      if (routes.length >= MAX_ROUTES_PER_TARGET) {
        break;
      }
    }
    for (const callerId of reverse.get(item.id) || []) {
      const depth = item.reversePath.length;
      if (bestDepth.has(callerId) && bestDepth.get(callerId) <= depth) {
        continue;
      }
      bestDepth.set(callerId, depth);
      queue.push({
        id: callerId,
        reversePath: [...item.reversePath, callerId],
      });
    }
  }
  return routes;
}

function runtimeModuleExports(ts, sourceFile, explicit) {
  const names = [];
  for (const exportedNames of explicit.named.values()) {
    for (const exportName of exportedNames) {
      names.push({ import_kind: "named", export_name: exportName });
    }
  }
  if (explicit.defaults.size > 0) {
    names.push({ import_kind: "default", export_name: "default" });
  }
  for (const statement of sourceFile.statements) {
    if (!hasModifier(ts, statement, ts.SyntaxKind.ExportKeyword)) {
      continue;
    }
    if (
      ts.isInterfaceDeclaration(statement) ||
      ts.isTypeAliasDeclaration(statement)
    ) {
      continue;
    }
    if (hasModifier(ts, statement, ts.SyntaxKind.DefaultKeyword)) {
      names.push({ import_kind: "default", export_name: "default" });
      continue;
    }
    if (ts.isVariableStatement(statement)) {
      for (const declaration of statement.declarationList.declarations) {
        if (ts.isIdentifier(declaration.name)) {
          names.push({
            import_kind: "named",
            export_name: declaration.name.text,
          });
        }
      }
    } else if (statement.name?.text) {
      names.push({ import_kind: "named", export_name: statement.name.text });
    }
  }
  return dedupeEntrypoints(names);
}

function routePayload(filepath, unit, route, index) {
  const member = route.entrypoint.member_path || [];
  const identity = JSON.stringify([
    filepath,
    unit.unit_id,
    route.entrypoint.import_kind,
    route.entrypoint.export_name,
    member,
    route.callPath,
    index,
  ]);
  return {
    entrypoint_id: `entrypoint-${crypto.createHash("sha1").update(identity).digest("hex").slice(0, 12)}`,
    filepath,
    import_kind: route.entrypoint.import_kind,
    export_name: route.entrypoint.export_name,
    member_path: member,
    invocation_kind: route.entrypoint.invocation_kind || "function",
    qualname: route.record.qualname,
    call_path: route.callPath,
    signature: route.signature,
  };
}

function analyzeFileText(filepath, text, units, ts) {
  const sourceFile = parseSource(ts, filepath, text);
  const exports = explicitExports(ts, sourceFile);
  const resolve = callResolver(ts, sourceFile);
  const records = collectCallableRecords(ts, sourceFile, exports, resolve);
  const graph = collectCallEdges(ts, records, resolve);
  const moduleExports = runtimeModuleExports(ts, sourceFile, exports);
  return units.map((unit) => {
    const record = targetRecord(unit, records);
    if (record) {
      // Prefer surviving name-based routes before adding alias-derived paths.
      const preferred = routesToTarget(
        ts,
        sourceFile,
        { ...graph, reverse: graph.namedReverse },
        record,
      );
      const seen = new Set();
      const routes = [
        ...preferred,
        ...routesToTarget(ts, sourceFile, graph, record),
      ]
        .filter((route) => {
          const key = JSON.stringify([
            route.record.id,
            route.entrypoint,
            route.callPath,
          ]);
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        })
        .slice(0, MAX_ROUTES_PER_TARGET)
        .map((route, index) => routePayload(filepath, unit, route, index));
      return {
        target_unit_id: unit.unit_id,
        accessibility:
          routes.length === 0
            ? "private_unreachable"
            : record.entrypoints.some(
                  (entrypoint) => !entrypoint.factory_record_id,
                )
              ? "public"
              : "private_reachable",
        entrypoints: routes,
      };
    }
    if (["file", "module"].includes(unit.kind) && moduleExports.length > 0) {
      return {
        target_unit_id: unit.unit_id,
        accessibility: "public",
        entrypoints: moduleExports
          .slice(0, MAX_ROUTES_PER_TARGET)
          .map((entrypoint, index) => ({
            entrypoint_id: `entrypoint-${crypto
              .createHash("sha1")
              .update(
                JSON.stringify([filepath, unit.unit_id, entrypoint, index]),
              )
              .digest("hex")
              .slice(0, 12)}`,
            filepath,
            ...entrypoint,
            member_path: [],
            invocation_kind: "value",
            qualname: entrypoint.export_name,
            call_path: [unit.qualname],
            signature: `${entrypoint.import_kind === "default" ? "default" : "export"} ${entrypoint.export_name}`,
          })),
      };
    }
    return {
      target_unit_id: unit.unit_id,
      accessibility: "private_unreachable",
      entrypoints: [],
    };
  });
}

export function publicTargetRoutes(projectRoot, units) {
  const ts = loadTypeScript(projectRoot);
  if (!ts) {
    return {
      source: "buggy-side TypeScript AST public reachability",
      available: false,
      targets: [],
      unreachable_target_unit_ids: (units || []).map((unit) => unit.unit_id),
    };
  }
  const grouped = new Map();
  for (const unit of units || []) {
    const filepath = safeRelativePath(unit.filepath);
    const values = grouped.get(filepath) || [];
    values.push(unit);
    grouped.set(filepath, values);
  }
  const targets = [];
  for (const [filepath, fileUnits] of [...grouped.entries()].sort(([a], [b]) =>
    a.localeCompare(b),
  )) {
    const full = path.join(projectRoot, filepath);
    if (!fs.existsSync(full)) {
      targets.push(
        ...fileUnits.map((unit) => ({
          target_unit_id: unit.unit_id,
          accessibility: "private_unreachable",
          entrypoints: [],
        })),
      );
      continue;
    }
    targets.push(
      ...analyzeFileText(
        filepath,
        fs.readFileSync(full, "utf8"),
        fileUnits,
        ts,
      ),
    );
  }
  return {
    source: "buggy-side TypeScript AST public reachability",
    available: true,
    targets,
    unreachable_target_unit_ids: targets
      .filter((item) => item.accessibility === "private_unreachable")
      .map((item) => item.target_unit_id),
  };
}
