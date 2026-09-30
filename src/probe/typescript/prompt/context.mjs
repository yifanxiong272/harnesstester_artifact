import fs from "node:fs";
import path from "node:path";

import {
  failureEvidence,
  projectFrames,
} from "../../../common/failure_context/typescript.mjs";
import { safeRelativePath, pathWithinRoots } from "../support/path_safety.mjs";
import {
  loadTypeScript,
  parseSource,
  splitSourceLines,
  nodeRange,
  isFunctionValue,
  memberName as nodeName,
} from "../support/typescript.mjs";

import {
  SUPPORTED_CONTEXT_REQUEST_KINDS as SUPPORTED_REQUEST_KINDS,
  extractJson,
  parseRequestList,
} from "./proposal.mjs";

const SOURCE_FILE_RE = /\.(?:ts|tsx|js|jsx)$/u;

function withinDirectory(file, directory) {
  const relative = path.relative(directory, file);
  return (
    relative !== ".." &&
    !relative.startsWith(`..${path.sep}`) &&
    !path.isAbsolute(relative)
  );
}

function contextPathWithinRoots(filepath, sourceRoots = []) {
  const roots = sourceRoots.map(safeRelativePath);
  return roots.includes(".") || pathWithinRoots(filepath, roots);
}

function missingPath(error) {
  return ["ENOENT", "ENOTDIR", "ELOOP"].includes(error.code);
}

function contextFile(projectRoot, sourceRoots = [], filepath) {
  let root;
  let full;
  try {
    root = fs.realpathSync(projectRoot);
    full = fs.realpathSync(path.join(root, filepath));
  } catch (error) {
    if (missingPath(error)) return { status: "not_found" };
    throw error;
  }
  if (!withinDirectory(full, root)) return { status: "invalid" };
  const roots = sourceRoots.length ? sourceRoots : ["."];
  const allowed = roots.some((value) => {
    try {
      const sourceRoot = fs.realpathSync(path.join(root, safeRelativePath(value)));
      return withinDirectory(sourceRoot, root) && withinDirectory(full, sourceRoot);
    } catch (error) {
      if (missingPath(error)) return false;
      throw error;
    }
  });
  if (!allowed) return { status: "invalid" };
  return fs.statSync(full).isFile()
    ? { status: "found", file: full }
    : { status: "not_found" };
}

export function failureTextFromSummary(
  summary = {},
  { maxChars = 20000 } = {},
) {
  const diagnostics = summary.diagnostics
    ? JSON.stringify(summary.diagnostics)
    : "";
  return failureEvidence(
    [summary.failure_excerpt, diagnostics, summary.output_tail],
    { maxChars },
  );
}

function boundedExcerpt(file, startLine, endLine, maxLines) {
  const lines = splitSourceLines(fs.readFileSync(file, "utf8"));
  const lo = Math.max(1, Number(startLine || 1));
  const hi = Math.min(
    lines.length,
    Number(endLine || lines.length),
    lo + Math.max(0, maxLines) - 1,
  );
  const width = String(Math.max(hi, lo)).length;
  return {
    start_line: lo,
    end_line: hi,
    line_count: Math.max(0, hi - lo + 1),
    code: Array.from({ length: Math.max(0, hi - lo + 1) }, (_, offset) => {
      const lineNo = lo + offset;
      return `${String(lineNo).padStart(width, " ")}: ${lines[lineNo - 1]}`;
    }).join("\n"),
  };
}

function indexFileWithAst(rel, file, index, ts) {
  const text = fs.readFileSync(file, "utf8");
  const sourceFile = parseSource(ts, rel, text);
  const add = (node, kind, qualname) => {
    if (qualname) {
      index.set(`${rel}\0${kind}\0${qualname}`, {
        filepath: rel,
        kind,
        qualname,
        ...nodeRange(sourceFile, node),
      });
    }
  };

  const visit = (node, parents = []) => {
    const name = ts.isConstructorDeclaration(node)
      ? "constructor"
      : nodeName(node);
    const qualname = [...parents, name].join(".");
    if (ts.isClassDeclaration(node) && name) {
      add(node, "class_definition", qualname);
      // Classes extend the lookup path; function bodies retain their class scope.
      parents = [...parents, name];
    } else if (
      (ts.isFunctionDeclaration(node) && name) ||
      ts.isMethodDeclaration(node) ||
      ts.isGetAccessorDeclaration(node) ||
      ts.isSetAccessorDeclaration(node) ||
      ts.isConstructorDeclaration(node)
    ) {
      add(node, "function_definition", qualname);
    } else if (ts.isVariableDeclaration(node) && name) {
      add(node, "symbol_definition", qualname);
      if (node.initializer && isFunctionValue(ts, node.initializer)) {
        add(node.parent?.parent || node, "function_definition", qualname);
      }
    } else if (
      (ts.isTypeAliasDeclaration(node) ||
        ts.isInterfaceDeclaration(node) ||
        ts.isEnumDeclaration(node)) &&
      name
    ) {
      add(node, "symbol_definition", qualname);
    }
    ts.forEachChild(node, (child) => visit(child, parents));
  };
  visit(sourceFile);
}

function buildContextIndex(projectRoot, sourceRoots, filepaths) {
  const index = new Map();
  const ts = loadTypeScript(projectRoot);
  if (!ts) {
    return index;
  }
  for (const filepath of new Set(filepaths)) {
    let safe = "";
    try {
      safe = safeRelativePath(filepath);
    } catch {
      continue;
    }
    const resolved = contextFile(projectRoot, sourceRoots, safe);
    if (
      SOURCE_FILE_RE.test(safe) &&
      !safe.endsWith(".d.ts") &&
      resolved.status === "found"
    ) {
      indexFileWithAst(safe, resolved.file, index, ts);
    }
  }
  return index;
}

export function parseContextRequests(content, { maxRequests = 1 } = {}) {
  const data = contextPayload(content);
  return parseRequestList(data?.requests || [], maxRequests);
}

export function parseHarnessRepairDecision(content, { maxRequests = 0 } = {}) {
  const data = contextPayload(content);
  const action = String(data?.action || "").trim();
  const diagnosis = String(data?.diagnosis || "").trim();
  if (action === "request_context") {
    if (maxRequests <= 0) {
      throw new Error("repair-time context requests are disabled");
    }
    const { requests, errors } = parseContextRequests(data, { maxRequests });
    if (requests.length === 0) {
      throw new Error("request_context decision must contain a valid request");
    }
    return { decision: { action, diagnosis, requests }, errors };
  }
  if (action === "repair") {
    return { decision: { action, diagnosis, proposal: data }, errors: [] };
  }
  if (action === "retain_original") {
    return { decision: { action, diagnosis }, errors: [] };
  }
  throw new Error(`unsupported harness repair action: ${action}`);
}

function contextPayload(content) {
  return typeof content === "string"
    ? extractJson(content, "context payload")
    : content;
}

function resolveOne({ projectRoot, sourceRoots, index, request, maxLines }) {
  let filepath = "";
  try {
    filepath = safeRelativePath(request.filepath);
  } catch {
    return { ...request, status: "invalid" };
  }
  const base = { ...request, filepath };
  if (
    !SUPPORTED_REQUEST_KINDS.has(request.kind) ||
    !contextPathWithinRoots(filepath, sourceRoots)
  ) {
    return { ...base, status: "invalid" };
  }
  const resolved = contextFile(projectRoot, sourceRoots, filepath);
  if (resolved.status !== "found") {
    return { ...base, status: resolved.status };
  }
  const range =
    request.kind === "module_context"
      ? { start_line: 1, end_line: Infinity }
      : index.get(`${filepath}\0${request.kind}\0${request.qualname}`);
  if (!range) {
    return { ...base, status: "not_found" };
  }
  return {
    ...base,
    status: "found",
    ...boundedExcerpt(resolved.file, range.start_line, range.end_line, maxLines),
  };
}

export function resolveContextRequests({
  projectRoot,
  sourceRoots,
  requests,
  maxRequests = 1,
  maxTotalLines = 220,
  maxModuleLines = 90,
  source = "buggy-side exact context requests",
}) {
  const result = {
    source,
    max_requests: maxRequests,
    max_total_lines: maxTotalLines,
    requests: [],
  };
  if (!Array.isArray(requests) || requests.length === 0 || maxRequests <= 0) {
    return result;
  }
  const selectedRequests = requests.slice(0, maxRequests);
  const indexPaths = selectedRequests.flatMap((request) => {
    let filepath;
    try {
      filepath = safeRelativePath(request.filepath);
    } catch {
      return [];
    }
    return contextPathWithinRoots(filepath, sourceRoots) ? [filepath] : [];
  });
  const index = buildContextIndex(
    projectRoot,
    sourceRoots,
    indexPaths,
  );
  let remaining = maxTotalLines;
  for (const request of selectedRequests) {
    const resolved = resolveOne({
      projectRoot,
      sourceRoots,
      index,
      request,
      maxLines: Math.min(maxModuleLines, Math.max(0, remaining)),
    });
    remaining = Math.max(0, remaining - Number(resolved.line_count || 0));
    result.requests.push(resolved);
  }
  return result;
}

export function projectTracebackContext({
  projectRoot,
  sourceRoots = ["."],
  failureText,
  maxFrames = 3,
  maxLines = 90,
}) {
  const frames = projectFrames({
    text: failureText,
    projectRoot,
    sourceRoots,
    maxFrames,
  });
  const index = buildContextIndex(
    projectRoot,
    sourceRoots,
    frames.map((frame) => frame.filepath),
  );
  const contexts = [];
  for (const frame of frames) {
    const resolved = contextFile(projectRoot, sourceRoots, frame.filepath);
    if (resolved.status !== "found") {
      continue;
    }
    const owner = [...index.values()]
      .filter(
        (symbol) =>
          symbol.filepath === frame.filepath &&
          symbol.start_line <= frame.line &&
          frame.line <= symbol.end_line,
      )
      .sort(
        (left, right) =>
          left.end_line - left.start_line - (right.end_line - right.start_line),
      )[0];
    let start = Math.max(1, frame.line - Math.floor(maxLines / 3));
    let end = start + maxLines - 1;
    if (owner) {
      start = Math.max(owner.start_line, frame.line - Math.floor(maxLines / 2));
      end = Math.min(owner.end_line, start + maxLines - 1);
      start = Math.max(owner.start_line, end - maxLines + 1);
    }
    const excerpt = boundedExcerpt(resolved.file, start, end, maxLines);
    contexts.push({
      filepath: frame.filepath,
      line: frame.line,
      qualname: owner?.qualname || "",
      source: "vitest_traceback_project_frame",
      ...excerpt,
    });
  }
  return contexts;
}
