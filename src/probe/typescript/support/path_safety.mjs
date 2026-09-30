import path from "node:path";

export function normalizePath(value) {
  return String(value || "").replace(/\\/gu, "/");
}

export function safeRelativePath(value) {
  const rel = normalizePath(value).trim();
  if (!rel || path.posix.isAbsolute(rel) || rel.split("/").includes("..")) {
    throw new Error(`unsafe relative path: ${value}`);
  }
  return path.posix.normalize(rel);
}

export function pathWithinRoots(filepath, roots = []) {
  const rel = safeRelativePath(filepath);
  return (
    roots.length === 0 ||
    roots.some(
      (root) =>
        rel === root.replace(/\/$/u, "") ||
        rel.startsWith(`${root.replace(/\/$/u, "")}/`),
    )
  );
}
