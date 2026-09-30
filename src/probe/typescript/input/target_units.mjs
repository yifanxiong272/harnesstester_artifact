import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { safeRelativePath } from "../support/path_safety.mjs";
import { splitSourceLines } from "../support/typescript.mjs";

function extractLines(text, startLine, endLine) {
  const lines = splitSourceLines(text);
  const lo = Math.max(1, startLine);
  const hi = Math.min(lines.length, endLine);
  return lines.slice(lo - 1, hi).join("\n");
}

function unitId(unit) {
  return `${unit.filepath}::${unit.qualname}@${unit.start_line}-${unit.end_line}:${unit.kind}`;
}

function dedupeUnits(units) {
  const result = new Map();
  for (const unit of units.sort((a, b) =>
    `${a.filepath}:${a.start_line}:${a.end_line}`.localeCompare(
      `${b.filepath}:${b.start_line}:${b.end_line}`,
    ),
  )) {
    const id = unit.unit_id || unitId(unit);
    if (!result.has(id)) {
      result.set(id, { ...unit, unit_id: id });
    }
  }
  return [...result.values()];
}

function targetFile(projectRoot, filepath) {
  const root = fs.realpathSync(projectRoot);
  const file = fs.realpathSync(path.join(root, filepath));
  const relative = path.relative(root, file);
  if (relative === ".." || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) {
    throw new Error(`target path escapes the checkout: ${filepath}`);
  }
  return file;
}

export function loadTargetUnits(projectRoot, unitSpecs) {
  return dedupeUnits(
    unitSpecs.map((spec) => {
      const filepath = safeRelativePath(spec.filepath || spec.file || "");
      const text = fs.readFileSync(targetFile(projectRoot, filepath), "utf8");
      const startLine = Number(spec.start_line || 1);
      const endLine = Number(spec.end_line || startLine);
      const code = extractLines(text, startLine, endLine);
      return {
        unit_id: spec.unit_id,
        filepath,
        qualname: String(spec.qualname || "<unit>"),
        kind: String(spec.kind || "region"),
        start_line: startLine,
        end_line: endLine,
        selection_source: String(spec.selection_source || "case"),
        code,
        code_sha256: crypto.createHash("sha256").update(code).digest("hex"),
      };
    }),
  );
}

export function sourceFileIndex(projectRoot, files) {
  return [...new Set(files)].sort().flatMap((filepath) => {
    const rel = safeRelativePath(filepath);
    const full = path.join(projectRoot, rel);
    if (!fs.existsSync(full)) {
      return [];
    }
    return [
      {
        path: rel,
        line_count: splitSourceLines(fs.readFileSync(targetFile(projectRoot, rel), "utf8")).length,
      },
    ];
  });
}
