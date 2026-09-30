const fs = require("node:fs");
const Module = require("node:module");
const path = require("node:path");
const root = process.env.TESTPILOT_SUBJECT_ROOT
  ? path.resolve(process.env.TESTPILOT_SUBJECT_ROOT)
  : path.resolve(__dirname, "../../../../../../resources/subjects/roo-code");
const requireFromProject = Module.createRequire(path.join(root, "package.json"));

// Preserve the original TestPilot2 raw-import hook and lazy module exports.
const originalLoad = Module._load;
Module._load = function (request, parent, isMain) {
  if (typeof request === "string" && request.endsWith("?raw")) {
    const filename = Module._resolveFilename(request.slice(0, -4), parent, isMain);
    return fs.readFileSync(filename, "utf8");
  }
  return originalLoad.call(this, request, parent, isMain);
};
process.env.TSX_TSCONFIG_PATH ||= path.join(root, "tsconfig.json");
requireFromProject("tsx/cjs");
const subject = {};
for (const { key, filepath } of require("./target-map.json")) {
  Object.defineProperty(subject, key, {
    enumerable: true,
    get: () => require(path.join(root, filepath)),
  });
}
module.exports = subject;
