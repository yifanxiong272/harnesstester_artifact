import fs from "node:fs";
import path from "node:path";

import {
  failureEvidence,
  projectFrames,
} from "../../../common/failure_context/typescript.mjs";
import { sameModuleSpecifier } from "../test_seed.mjs";
import { normalizedRelativePath } from "../paths.mjs";
import {
  declarationAtLine,
  exportedNames,
  loadTypeScript,
  nodeLineRange,
  parseTypeScript,
  resolveDeclaration,
} from "../typescript_ast.mjs";

const MAX_CONTEXT_LINES = 90;
const MAX_TOTAL_CONTEXT_LINES = 320;
const DEFINITION_KINDS = new Set([
  "symbol_definition",
  "function_definition",
  "class_definition",
]);
const SOURCE_EXTENSIONS = new Set([
  ".cjs",
  ".cts",
  ".js",
  ".jsx",
  ".mjs",
  ".mts",
  ".ts",
  ".tsx",
]);

function readText(file) {
  try {
    return fs.readFileSync(file, "utf8");
  } catch {
    return "";
  }
}

export function projectSourceFile(projectRoot, filepath) {
  const relpath = normalizedRelativePath(filepath);
  if (!relpath || !SOURCE_EXTENSIONS.has(path.posix.extname(relpath))) {
    return { status: "invalid", relpath, file: null };
  }
  const candidate = path.join(projectRoot, relpath);
  if (!fs.existsSync(candidate)) {
    return { status: "not_found", relpath, file: null };
  }
  const root = fs.realpathSync(projectRoot);
  const file = fs.realpathSync(candidate);
  const relative = path.relative(root, file);
  if (
    !relative ||
    relative === ".." ||
    relative.startsWith(`..${path.sep}`) ||
    path.isAbsolute(relative) ||
    !fs.statSync(file).isFile()
  ) {
    return { status: "invalid", relpath, file: null };
  }
  return { status: "found", relpath, file };
}

function numberedExcerpt(filepath, text, startLine, endLine) {
  const lines = text.split("\n");
  const start = Math.max(1, startLine);
  const end = Math.min(lines.length, endLine);
  const output = [];
  for (let line = start; line <= end; line += 1) {
    output.push(`${String(line).padStart(5, " ")} | ${lines[line - 1] ?? ""}`);
  }
  return {
    path: filepath,
    start_line: start,
    end_line: end,
    code_excerpt: output.join("\n"),
  };
}

export function exportSurfaceForFile(
  projectRoot,
  filepath,
  typescript = loadTypeScript(projectRoot),
) {
  const source = projectSourceFile(projectRoot, filepath);
  if (source.status !== "found") {
    return { filepath, status: source.status, exports: [] };
  }
  try {
    const text = readText(source.file);
    const sourceFile = parseTypeScript(typescript, source.relpath, text);
    return {
      filepath: source.relpath,
      status: "found",
      exports: exportedNames(typescript, sourceFile),
    };
  } catch {
    return { filepath: source.relpath, status: "not_found", exports: [] };
  }
}

function directTargetImports(typescript, node, targetImport) {
  const matches = [];
  function visit(current) {
    if (
      typescript.isImportDeclaration(current) &&
      sameModuleSpecifier(current.moduleSpecifier.text, targetImport)
    ) {
      matches.push(current);
    }
    if (
      typescript.isCallExpression(current) &&
      current.expression.kind === typescript.SyntaxKind.ImportKeyword &&
      typescript.isStringLiteralLike(current.arguments[0]) &&
      sameModuleSpecifier(current.arguments[0].text, targetImport)
    ) {
      matches.push(current);
    }
    typescript.forEachChild(current, visit);
  }
  visit(node);
  return matches;
}

function awaitedLoaderStatement(typescript, node, targetLoader) {
  if (!typescript.isExpressionStatement(node)) return false;
  const expression = node.expression;
  if (!typescript.isAwaitExpression(expression)) return false;
  const call = expression.expression;
  return (
    typescript.isCallExpression(call) &&
    typescript.isIdentifier(call.expression) &&
    call.expression.text === targetLoader &&
    call.arguments.length === 0
  );
}

export function assertSafeTargetAccess({
  code,
  targetBinding,
  targetImport,
  targetLoader,
  typescript,
}) {
  const sourceFile = parseTypeScript(
    typescript,
    "generated.test.ts",
    String(code ?? ""),
  );
  const allowed = new Set();
  let usesBinding = false;
  let usesLoader = false;
  let usesRuntimeMock = false;

  function inspectStatements(node) {
    if (typescript.isSourceFile(node) || typescript.isBlock(node)) {
      for (let index = 1; index < node.statements.length; index += 1) {
        if (
          awaitedLoaderStatement(
            typescript,
            node.statements[index - 1],
            targetLoader,
          )
        ) {
          for (const directImport of directTargetImports(
            typescript,
            node.statements[index],
            targetImport,
          )) {
            if (typescript.isCallExpression(directImport)) {
              allowed.add(directImport);
            }
          }
        }
      }
    }
    typescript.forEachChild(node, inspectStatements);
  }
  inspectStatements(sourceFile);

  function visit(node) {
    if (
      targetBinding &&
      typescript.isIdentifier(node) &&
      node.text === targetBinding
    ) {
      usesBinding = true;
    }
    if (
      typescript.isCallExpression(node) &&
      typescript.isIdentifier(node.expression) &&
      node.expression.text === targetLoader
    ) {
      usesLoader = true;
    }
    if (
      typescript.isCallExpression(node) &&
      typescript.isPropertyAccessExpression(node.expression) &&
      node.expression.name.text === "doMock"
    ) {
      usesRuntimeMock = true;
    }
    if (
      typescript.isImportDeclaration(node) &&
      sameModuleSpecifier(node.moduleSpecifier.text, targetImport)
    ) {
      throw new Error(
        "proposal must reuse a seed binding or target_loader instead of importing the selected source module",
      );
    }
    if (
      typescript.isCallExpression(node) &&
      node.expression.kind === typescript.SyntaxKind.ImportKeyword &&
      typescript.isStringLiteralLike(node.arguments[0]) &&
      sameModuleSpecifier(node.arguments[0].text, targetImport) &&
      !allowed.has(node)
    ) {
      throw new Error(
        "proposal must reuse a seed binding or target_loader instead of importing the selected source module",
      );
    }
    if (
      typescript.isCallExpression(node) &&
      typescript.isIdentifier(node.expression) &&
      node.expression.text === "require" &&
      typescript.isStringLiteralLike(node.arguments[0]) &&
      sameModuleSpecifier(node.arguments[0].text, targetImport)
    ) {
      throw new Error(
        "proposal must reuse a seed binding or target_loader instead of importing the selected source module",
      );
    }
    typescript.forEachChild(node, visit);
  }
  visit(sourceFile);
  if (usesBinding && (usesLoader || usesRuntimeMock)) {
    throw new Error(
      "proposal must choose one target access path: use the static target_binding without runtime mocks, or use the module returned by target_loader",
    );
  }
}

function boundedSpan(lineCount, startLine, endLine, lineBudget, context = 1) {
  const start = Math.max(1, startLine - context);
  const end = Math.min(lineCount, endLine + context);
  const budget = Math.max(1, Math.min(MAX_CONTEXT_LINES, lineBudget));
  return [start, Math.min(end, start + budget - 1)];
}

/** Load one requested source file before applying its kind-specific excerpt. */
function sourceContext(projectRoot, request, typescript, lineBudget) {
  const source = projectSourceFile(projectRoot, request.filepath);
  if (source.status === "invalid") {
    return {
      request,
      status: "invalid",
      note:
        request.kind === "test_file_context"
          ? "request must name a safe project-local source file"
          : "unsafe filepath",
    };
  }
  if (source.status === "not_found") {
    return { request, status: "not_found" };
  }
  const text = readText(source.file);
  return DEFINITION_KINDS.has(request.kind)
    ? definitionContext(source.relpath, text, request, typescript, lineBudget)
    : fileContext(source.relpath, text, request, lineBudget);
}

function definitionContext(filepath, text, request, typescript, lineBudget) {
  const sourceFile = parseTypeScript(typescript, filepath, text);
  const resolved = resolveDeclaration(typescript, sourceFile, request.qualname);
  if (resolved.status !== "found") {
    return { request, status: resolved.status };
  }
  const declaration = resolved.matches[0];
  if (request.kind === "class_definition" && declaration.kind !== "class") {
    return { request, status: "not_found" };
  }
  if (
    request.kind === "function_definition" &&
    !["function", "method", "accessor", "constructor"].includes(
      declaration.kind,
    )
  ) {
    return { request, status: "not_found" };
  }
  const range = nodeLineRange(sourceFile, declaration.node);
  const [start, end] = boundedSpan(
    text.split("\n").length,
    range.startLine,
    range.endLine,
    lineBudget,
  );
  return {
    request,
    status: "found",
    resolved_qualname: declaration.qualname,
    resolved_kind: declaration.kind,
    ...numberedExcerpt(filepath, text, start, end),
  };
}

function fileContext(filepath, text, request, lineBudget) {
  const testFile = request.kind === "test_file_context";
  const lines = text.split("\n");
  const start = Math.min(
    lines.length,
    Math.max(1, Number(request.start_line ?? 1)),
  );
  const requestedEnd = Math.max(
    start,
    Number(
      request.end_line ?? start + (testFile ? lineBudget : MAX_CONTEXT_LINES) - 1,
    ),
  );
  let end = Math.min(lines.length, requestedEnd, start + lineBudget - 1);
  let excerpt = numberedExcerpt(filepath, text, start, end);
  while (testFile && excerpt.code_excerpt.length > 9000 && end > start) {
    end -= 1;
    excerpt = numberedExcerpt(filepath, text, start, end);
  }
  return {
    request,
    status: "found",
    ...excerpt,
    ...(testFile ? { truncated: start > 1 || end < lines.length } : {}),
  };
}

export function resolveContextRequests({
  projectRoot,
  objective,
  requests,
  visibleContext = [],
  typescript = loadTypeScript(projectRoot),
}) {
  const records = [];
  let remainingLines = MAX_TOTAL_CONTEXT_LINES;
  const seenRequests = new Set();
  const seenSpans = new Set();
  for (const request of requests) {
    const requestKey = JSON.stringify([
      request.kind,
      request.filepath,
      request.qualname,
      request.start_line,
      request.end_line,
    ]);
    if (seenRequests.has(requestKey)) continue;
    seenRequests.add(requestKey);

    let record;
    if (request.kind === "export_surface") {
      const filepath = request.filepath || objective.filepath;
      record = {
        request,
        status: "found",
        export_surface: exportSurfaceForFile(projectRoot, filepath, typescript),
      };
    } else if (
      request.kind === "module_context" ||
      request.kind === "test_file_context" ||
      DEFINITION_KINDS.has(request.kind)
    ) {
      record = sourceContext(
        projectRoot,
        request,
        typescript,
        Math.min(MAX_CONTEXT_LINES, remainingLines),
      );
    } else {
      record = {
        request,
        status: "unsupported",
        note: `unsupported request kind: ${request.kind}`,
      };
    }
    const span = `${record?.path ?? ""}:${record?.start_line ?? 0}:${record?.end_line ?? 0}`;
    if (record?.status === "found" && record.path && seenSpans.has(span)) {
      continue;
    }
    if (
      record?.status === "found" &&
      contextAlreadyVisible(record, visibleContext)
    ) {
      continue;
    }
    records.push(record);
    if (record?.status === "found" && record.start_line && record.end_line) {
      seenSpans.add(span);
      remainingLines -= record.end_line - record.start_line + 1;
    }
    if (remainingLines <= 0) {
      break;
    }
  }
  return records;
}

function contextAlreadyVisible(record, visibleContext) {
  const path = String(record.path ?? "");
  const start = Number(record.start_line ?? 0);
  const end = Number(record.end_line ?? 0);
  if (!path || start <= 0 || end < start) return false;
  const covered = new Set();
  for (const item of visibleContext) {
    const itemPath = String(item?.path ?? item?.filepath ?? "");
    if (itemPath !== path) continue;
    const itemStart = Number(item?.start_line ?? 0);
    const itemEnd = Number(item?.end_line ?? 0);
    for (let line = itemStart; line > 0 && line <= itemEnd; line += 1) {
      covered.add(line);
    }
  }
  for (let line = start; line <= end; line += 1) {
    if (!covered.has(line)) return false;
  }
  return true;
}

export function tracebackContextFromFailure({
  projectRoot,
  failure,
  sourceRoots = ["."],
  typescript = loadTypeScript(projectRoot),
}) {
  const text = failureEvidence([
    ...(failure?.failure_snippets ?? []),
    failure?.failure_output ?? "",
    failure?.output_tail ?? "",
  ]);
  const records = [];
  const frames = projectFrames({ text, projectRoot, sourceRoots, maxFrames: 3 });
  for (const frame of frames) {
    const resolved = projectSourceFile(projectRoot, frame.filepath);
    if (resolved.status !== "found") {
      continue;
    }
    const key = `${frame.filepath}:${frame.line}`;
    const source = readText(resolved.file);
    if (source) {
      const sourceFile = parseTypeScript(typescript, frame.filepath, source);
      const owner = declarationAtLine(typescript, sourceFile, frame.line);
      const range = owner
        ? nodeLineRange(sourceFile, owner.node)
        : null;
      let [start, end] = range
        ? boundedSpan(
            source.split("\n").length,
            range.startLine,
            range.endLine,
            MAX_CONTEXT_LINES,
          )
        : [Math.max(1, frame.line - 8), frame.line + 8];
      // Recenter a truncated declaration only when it omits the failing line.
      if (range && frame.line > end) {
        start = Math.max(
          range.startLine,
          Math.min(
            frame.line - Math.floor(MAX_CONTEXT_LINES / 2),
            range.endLine - MAX_CONTEXT_LINES + 1,
          ),
        );
        end = Math.min(range.endLine, start + MAX_CONTEXT_LINES - 1);
      }
      records.push({
        request: {
          kind: "traceback_context",
          filepath: frame.filepath,
          qualname: owner?.qualname ?? "",
          reason: key,
        },
        status: "found",
        ...numberedExcerpt(frame.filepath, source, start, end),
      });
    }
  }
  return records;
}
