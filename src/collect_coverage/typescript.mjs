#!/usr/bin/env node
/** Collect package denominators and per-test coverage using native Vitest. */
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { parseArgs } from "node:util";
import { gzipSync } from "node:zlib";

import { safeRelativePath } from "../augment/typescript/paths.mjs";
import { CoverageFacts } from "./typescript_facts.mjs";

const read = file => JSON.parse(fs.readFileSync(file, "utf8"));
const write = (file, data) => fs.writeFileSync(file, JSON.stringify(data, null, 2) + "\n");

function within(root, relative) {
  if (!safeRelativePath(relative)) throw new Error(`Expected checkout-relative path: ${relative}`);
  const file = fs.realpathSync(path.join(root, relative));
  const rel = path.relative(root, file);
  if (rel === ".." || rel.startsWith(`..${path.sep}`)) throw new Error(`Path escapes checkout: ${relative}`);
  return file;
}

async function execute(command, cwd, log, timeout) {
  const fd = fs.openSync(log, "w");
  const started = performance.now();
  let timedOut = false;
  let interrupted = false;
  let grace;
  const proc = spawn(command[0], command.slice(1), {
    cwd, env: { ...process.env, CI: "true" },
    stdio: ["ignore", fd, fd], detached: process.platform !== "win32",
  });
  const signal = name => {
    if (!proc.pid) return;
    try {
      if (process.platform === "win32") proc.kill(name);
      else process.kill(-proc.pid, name);
    } catch (error) { if (error.code !== "ESRCH") throw error; }
  };
  const stop = () => {
    signal("SIGTERM");
    grace ??= setTimeout(() => signal("SIGKILL"), 3000);
  };
  const interrupt = () => { interrupted = true; stop(); };
  process.once("SIGINT", interrupt);
  process.once("SIGTERM", interrupt);
  const timer = setTimeout(() => { timedOut = true; stop(); }, timeout * 1000);
  try {
    const code = await new Promise((resolve, reject) => {
      proc.once("error", reject);
      proc.once("close", resolve);
    });
    return { status: interrupted ? "interrupted" : timedOut ? "timeout" : code === 0 ? "passed" : "failed",
      exit_code: code, duration_seconds: (performance.now() - started) / 1000 };
  } catch (error) {
    return { status: "error", exit_code: null, error: error.message,
      duration_seconds: (performance.now() - started) / 1000 };
  } finally {
    clearTimeout(timer);
    clearTimeout(grace);
    process.removeListener("SIGINT", interrupt);
    process.removeListener("SIGTERM", interrupt);
    if (timedOut || interrupted) signal("SIGKILL");
    fs.closeSync(fd);
  }
}

async function main() {
  const { values } = parseArgs({ options: {
    config: { type: "string" }, "out-dir": { type: "string" }, help: { type: "boolean" },
  } });
  if (values.help) {
    console.log("node typescript.mjs --config collection.json --out-dir NEW_DIRECTORY");
    return;
  }
  if (!values.config || !values["out-dir"]) throw new Error("--config and --out-dir are required");
  const configPath = path.resolve(values.config);
  const config = read(configPath);
  const root = fs.realpathSync(path.resolve(path.dirname(configPath), config.project_root));
  const scope = read(path.resolve(path.dirname(configPath), config.source_files));
  const sources = scope.files ?? scope.locations?.map(item => item.file);
  if (!Array.isArray(sources) || !sources.length || new Set(sources).size !== sources.length) {
    throw new Error("source_files must contain a nonempty unique files array");
  }
  sources.forEach(file => within(root, file));
  if (typeof config.project !== "string" || !config.project || !config.packages?.length) {
    throw new Error("project and a nonempty packages array are required");
  }
  const command = config.command ?? ["pnpm", "exec", "vitest"];
  if (!Array.isArray(command) || !command.length || command.some(item => typeof item !== "string")) {
    throw new Error("command must be an argument array");
  }
  const tests = new Set();
  for (const pkg of config.packages) {
    pkg.cwd = within(root, pkg.cwd ?? ".");
    if (!Array.isArray(pkg.tests) || !pkg.tests.length) throw new Error("each package needs explicit tests");
    for (const test of pkg.tests) {
      const file = within(pkg.cwd, test);
      if (tests.has(file)) throw new Error(`Test listed twice: ${file}`);
      tests.add(file);
    }
  }
  const output = path.resolve(values["out-dir"]);
  let ancestor = output;
  while (!fs.existsSync(ancestor)) ancestor = path.dirname(ancestor);
  const resolved = path.resolve(fs.realpathSync(ancestor), path.relative(ancestor, output));
  const rel = path.relative(root, resolved);
  if (!rel || (!rel.startsWith(`..${path.sep}`) && rel !== ".." && !path.isAbsolute(rel))) {
    throw new Error("out-dir must be outside the checkout");
  }
  const timeout = config.timeout_seconds ?? 300;
  const denominatorTimeout = config.denominator_timeout_seconds ?? 900;
  if (![timeout, denominatorTimeout].every(value => Number.isFinite(value) && value > 0)) {
    throw new Error("timeouts must be positive seconds");
  }
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.mkdirSync(output);
  const records = [];
  const facts = new CoverageFacts(config.project, root, sources);
  const save = () => write(path.join(output, "runs.json"), records);
  for (const [index, pkg] of config.packages.entries()) {
    const cases = [{ denominator: true }, ...pkg.tests.map(test => ({ test }))];
    for (const [number, item] of cases.entries()) {
      const dir = path.join(output, "raw", `${index + 1}_${number}`);
      fs.mkdirSync(dir, { recursive: true });
      // Vitest clears its reports directory before collecting coverage.
      const log = `${dir}.log`;
      const reporter = path.join(dir, "reporter.json");
      const args = [...command, "run", ...(pkg.config ? ["--config", pkg.config] : []),
        ...(pkg.args ?? []), "--coverage", `--coverage.provider=${pkg.provider ?? "v8"}`,
        `--coverage.all=${Boolean(item.denominator)}`, "--coverage.reportOnFailure",
        "--coverage.reporter=json", "--coverage.reportsDirectory", dir,
        ...["lines", "branches", "functions", "statements"].map(name => `--coverage.thresholds.${name}=0`),
        ...(pkg.include ?? ["**/*.{ts,tsx,js,jsx,mjs,cjs}"]).flatMap(glob => ["--coverage.include", glob]),
        ...(pkg.exclude ?? []).flatMap(glob => ["--coverage.exclude", glob]),
        "--reporter=json", "--outputFile", reporter, ...(item.test ? [within(pkg.cwd, item.test)] : [])];
      const row = { package_cwd: path.relative(root, pkg.cwd) || ".",
        ...(item.denominator ? { denominator: true } : { test_file: path.relative(root, path.join(pkg.cwd, item.test)).split(path.sep).join("/") }),
        command: args, ...await execute(args, pkg.cwd, log, item.denominator ? denominatorTimeout : timeout),
        log: path.relative(output, log), coverage_available: false };
      const report = path.join(dir, "coverage-final.json");
      if (fs.existsSync(reporter)) {
        try {
          const data = read(reporter);
          row.test_counts = { total: data.numTotalTests, passed: data.numPassedTests,
            failed: data.numFailedTests, skipped: data.numPendingTests };
          if (row.status === "passed" && data.numFailedTests > 0) row.status = "failed";
          if (item.test && data.testResults?.some(result =>
            path.resolve(pkg.cwd, result.name) !== within(pkg.cwd, item.test))) {
            row.coverage_error = "Vitest selected another test file; use an unambiguous package/test configuration";
          }
        } catch (error) { row.reporter_error = error.message; }
      }
      try {
        if (fs.existsSync(report) && !row.coverage_error) {
          const payload = read(report);
          facts.add(payload, { denominator: item.denominator, testFile: row.test_file });
          fs.writeFileSync(report + ".gz", gzipSync(fs.readFileSync(report)));
          fs.unlinkSync(report);
          row.coverage_available = true;
          row.coverage_json = path.relative(output, report + ".gz");
        }
      } catch (error) { row.coverage_error = error.message; }
      records.push(row);
      save();
      if (row.status === "interrupted") throw new Error("collection interrupted");
      if (row.coverage_error) throw new Error(row.coverage_error);
    }
  }
  if (records.some(row => !row.coverage_available)) {
    throw new Error("Some executions produced no coverage report; inspect runs.json before using this collection");
  }
  write(path.join(output, "coverage.json"), facts.finish());
  console.log(path.join(output, "coverage.json"));
}

main().catch(error => { console.error(error.message); process.exitCode = 1; });
