import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ANSI_ESCAPE_RE = /\u001B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])/gu;
const STACK_FRAME_RE = /(?:at\s+.*?\()?([^()\s]+?\.(?:[cm]?[jt]s|[jt]sx)):(\d+)(?::(\d+))?(?:\)|\s|$)/gu;
const SOURCE_EXTENSIONS = new Set([".cjs", ".cts", ".js", ".jsx", ".mjs", ".mts", ".ts", ".tsx"]);
const EXCLUDED_PARTS = new Set(["node_modules", "dist", "build", "coverage", "test", "tests", "__tests__", "fixtures", "__fixtures__"]);

export function failureEvidence(parts, { maxChars = 20000 } = {}) {
  const values = parts.map((part) => String(part || "")).filter(Boolean);
  return [...new Set(values)].join("\n").replace(ANSI_ESCAPE_RE, "").slice(-maxChars);
}

export function projectFrames({ text, projectRoot, sourceRoots = ["."], maxFrames = 3 }) {
  const frames = [];
  const seen = new Set();
  for (const match of String(text || "").matchAll(STACK_FRAME_RE)) {
    const filepath = canonicalProjectPath(match[1], { projectRoot, sourceRoots });
    const line = Number(match[2]);
    const key = `${filepath}:${line}`;
    if (!filepath || !line || seen.has(key)) continue;
    seen.add(key);
    frames.push({
      raw_path: match[1],
      filepath,
      line,
      column: Number(match[3] || 0),
      offset: match.index,
    });
    if (frames.length >= maxFrames) break;
  }
  return frames;
}

export function canonicalProjectPath(rawPath, { projectRoot, sourceRoots = ["."] }) {
  const root = fs.realpathSync(projectRoot);
  let normalized = String(rawPath || "").replace(/\\/gu, "/");
  if (normalized.startsWith("file://")) {
    try {
      normalized = fileURLToPath(normalized).replace(/\\/gu, "/");
    } catch {
      return "";
    }
  }
  if (path.isAbsolute(normalized)) {
    const relative = path.relative(root, normalized).replace(/\\/gu, "/");
    if (!relative.startsWith("..") && !path.isAbsolute(relative)) {
      const direct = validCandidate(relative, { root, sourceRoots });
      if (direct) return direct;
    }
  }
  const candidates = new Set();
  if (!path.isAbsolute(normalized)) candidates.add(normalized.replace(/^\.\//u, ""));
  const parts = normalized.split("/").filter(Boolean);
  for (let index = 0; index < parts.length; index += 1) {
    candidates.add(parts.slice(index).join("/"));
  }
  const matches = new Set(
    [...candidates]
      .map((candidate) => validCandidate(candidate, { root, sourceRoots }))
      .filter(Boolean),
  );
  return matches.size === 1 ? [...matches][0] : "";
}

function validCandidate(candidate, { root, sourceRoots }) {
  const normalized = path.posix.normalize(candidate);
  const parts = normalized.split("/");
  if (
    !candidate ||
    normalized !== candidate ||
    normalized === ".." ||
    normalized.startsWith("../") ||
    path.posix.isAbsolute(normalized) ||
    parts.some((part) => EXCLUDED_PARTS.has(part)) ||
    !SOURCE_EXTENSIONS.has(path.posix.extname(normalized)) ||
    !withinSourceRoots(normalized, sourceRoots)
  ) {
    return "";
  }
  const file = path.join(root, normalized);
  if (!fs.existsSync(file) || !fs.statSync(file).isFile()) return "";
  const resolved = fs.realpathSync(file);
  const relative = path.relative(root, resolved);
  if (!relative || relative === ".." || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) {
    return "";
  }
  return relative.replace(/\\/gu, "/");
}

function withinSourceRoots(filepath, sourceRoots) {
  return sourceRoots.some((value) => {
    const root = String(value || ".").replace(/\\/gu, "/").replace(/^\.\//u, "").replace(/\/$/u, "");
    return !root || root === "." || filepath === root || filepath.startsWith(`${root}/`);
  });
}
