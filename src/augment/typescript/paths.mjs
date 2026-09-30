import path from "node:path";

/** Return a canonical checkout-relative path, or null for invalid input. */
export function normalizedRelativePath(value) {
  const normalized = String(value ?? "").replace(/\\/gu, "/");
  const parsed = path.posix.normalize(normalized);
  const valid = (
    normalized.length > 0 &&
    !normalized.includes("\0") &&
    !path.posix.isAbsolute(normalized) &&
    !/^[a-zA-Z]:\//u.test(normalized) &&
    parsed === normalized &&
    parsed !== ".." &&
    !parsed.startsWith("../")
  );
  return valid ? normalized : null;
}

export function safeRelativePath(value) {
  return normalizedRelativePath(value) !== null;
}
