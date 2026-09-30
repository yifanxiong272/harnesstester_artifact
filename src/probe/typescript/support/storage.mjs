import fs from "node:fs";
import path from "node:path";

/** Walk retained files without following symlink entries. */
export function* walkFiles(directory, { exclude = [], sorted = false } = {}) {
  if (!fs.existsSync(directory)) return;
  const names = fs.readdirSync(directory);
  if (sorted) names.sort();
  for (const name of names) {
    if (exclude.includes(name)) continue;
    const full = path.join(directory, name);
    const stat = fs.lstatSync(full, { throwIfNoEntry: false });
    if (!stat || stat.isSymbolicLink()) continue;
    if (stat.isDirectory()) {
      yield* walkFiles(full, { exclude, sorted });
    } else {
      yield full;
    }
  }
}

export function removeManagedPaths(paths) {
  return paths.map((target) => {
    const record = {
      path: path.resolve(target),
      existed: fs.existsSync(target),
      removed: false,
    };
    try {
      fs.rmSync(target, { recursive: true, force: true });
      record.removed = !fs.existsSync(target);
    } catch (error) {
      record.error = String(error.message || error);
    }
    return record;
  });
}
