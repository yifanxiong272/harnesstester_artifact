import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import { test } from "node:test";

import { createPackageVitestAdapter } from "../typescript/package_vitest_adapter.mjs";

const LAUNCHER = `
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
const mode = process.argv[2];
const args = process.argv.slice(3);
fs.writeFileSync("launcher.pid", String(process.pid));
process.stdout.write("launcher stdout\\n");
process.stderr.write("launcher stderr\\n");
function report() {
  const coverageDir = args[args.indexOf("--coverage.reportsDirectory") + 1];
  const reporter = args[args.indexOf("--outputFile") + 1];
  fs.writeFileSync(path.join(coverageDir, "coverage-final.json"), "{}");
  fs.writeFileSync(reporter, JSON.stringify({
    numTotalTests: 1, numPassedTests: 1, numFailedTests: 0, numPendingTests: 0,
  }));
}
if (mode === "normal") { report(); process.exit(0); }
if (mode === "output") {
  report();
  process.stdout.write("x".repeat(1024 * 1024) + "OUTPUT_END\\n", () => process.exit(0));
}
if (mode === "failed") process.exit(7);
process.on("SIGTERM", () => {
  fs.writeFileSync("launcher.term", "received");
  if (mode === "timeout") process.exit(0);
});
// Self-expiry bounds a regression run even if production cleanup is broken.
setTimeout(() => process.exit(99), 6000).unref();
setInterval(() => {}, 1000);
if (mode === "resistant-tree" || mode === "orphan") {
  const descendant = spawn(process.execPath, ["-e", \`
    const fs = require("node:fs");
    process.on("SIGTERM", () => fs.writeFileSync("descendant.term", "received"));
    fs.writeFileSync("descendant.pid", String(process.pid));
    setInterval(() => {}, 1000);
    setTimeout(() => process.exit(99), 6000).unref();
    process.send("ready");
    process.disconnect();
  \`], {stdio: ["ignore", "inherit", "inherit", "ipc"]});
  descendant.on("message", () => {
    if (mode === "orphan") { report(); process.exit(0); }
  });
}
`;

function isRunning(pid) {
  try {
    process.kill(pid, 0);
  } catch (error) {
    if (error.code === "ESRCH") return false;
    throw error;
  }
  // Orphans can briefly remain as zombies until the OS reaps them.
  const state = spawnSync("ps", ["-o", "stat=", "-p", String(pid)], {
    encoding: "utf8", timeout: 1000, killSignal: "SIGKILL",
  });
  assert.ifError(state.error);
  assert([0, 1].includes(state.status), state.stderr);
  return state.status === 0 && !state.stdout.trim().startsWith("Z");
}

async function assertStopped(pids) {
  const deadline = Date.now() + 2000;
  while (pids.some(isRunning) && Date.now() < deadline) await delay(20);
  assert.deepEqual(pids.filter(isRunning), [], "launcher/descendant still running");
}

function fixture(t, mode) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "augment-ts-process-"));
  const pids = () => ["launcher.pid", "descendant.pid"]
    .map((file) => path.join(root, file))
    .filter((file) => fs.existsSync(file))
    .map((file) => Number(fs.readFileSync(file, "utf8")));
  t.after(async () => {
    try {
      for (const pid of pids()) {
        try { process.kill(pid, "SIGKILL"); }
        catch (error) { if (error.code !== "ESRCH") throw error; }
      }
      await assertStopped(pids());
    } finally {
      fs.rmSync(root, {recursive: true, force: true});
    }
  });
  const launcher = path.join(root, "launcher.mjs");
  fs.writeFileSync(launcher, LAUNCHER);
  const adapter = createPackageVitestAdapter({
    packages: [{name: "root", cwd: "."}],
    launcher: mode === "missing" ? [path.join(root, "nonexistent")]
      : [process.execPath, launcher, mode],
  });
  return {root, pids, adapter, request: {
    projectRoot: root, sourceProjectRoot: root,
    testFile: "test/generated.test.ts", testName: "generated test",
    outDir: path.join(root, "out"), timeoutSeconds: 0.75,
  }};
}

const posix = {skip: process.platform === "win32", timeout: 15000};

for (const method of ["validateGeneratedTest", "measureTestFileCoverage"]) {
  test(`actual adapter ${method}: normal result is preserved`, posix, async (t) => {
    const {adapter, request, pids} = fixture(t, "normal");
    const result = adapter[method](request);
    assert.equal(result.status, "passed");
    assert.equal(result.exit_code, 0);
    assert.equal(result.timed_out, false);
    assert.deepEqual(result.test_counts, {total: 1, passed: 1, failed: 0, skipped: 0});
    assert.match(result.output_tail, /launcher stdout/);
    assert.match(result.output_tail, /launcher stderr/);
    assert.equal(pids().length, 1);
    await assertStopped(pids());
  });
}

for (const mode of ["timeout", "resistant-tree"]) {
  test(`actual adapter timeout cleanup: ${mode}`, posix, async (t) => {
    const {root, adapter, request, pids} = fixture(t, mode);
    const start = performance.now();
    const result = adapter.validateGeneratedTest(request);
    assert(performance.now() - start < 3000, "timeout exceeded bounded cleanup grace");
    assert.equal(result.status, "timeout");
    assert.equal(result.timed_out, true);
    assert.equal(result.exit_code, 124);
    assert.equal(fs.readFileSync(path.join(root, "launcher.term"), "utf8"), "received");
    assert.equal(pids().length, mode === "timeout" ? 1 : 2);
    if (mode === "resistant-tree") {
      assert.equal(fs.readFileSync(path.join(root, "descendant.term"), "utf8"), "received");
    }
    await assertStopped(pids());
  });
}

test("actual adapter drains normal output before returning", posix, async (t) => {
  const {adapter, request, pids} = fixture(t, "output");
  const result = adapter.validateGeneratedTest(request);
  assert.equal(result.status, "passed");
  assert.match(result.output_tail, /OUTPUT_END/);
  await assertStopped(pids());
});

test("actual adapter cleans orphan retaining output pipes after normal exit", posix, async (t) => {
  const {adapter, request, pids} = fixture(t, "orphan");
  const result = adapter.validateGeneratedTest(request);
  assert.equal(result.status, "passed");
  assert.equal(result.timed_out, false);
  assert.equal(pids().length, 2);
  await assertStopped(pids());
});

for (const mode of ["failed", "missing"]) {
  test(`actual adapter preserves failed outcome: ${mode}`, posix, async (t) => {
    const {adapter, request, pids} = fixture(t, mode);
    const result = adapter.validateGeneratedTest(request);
    assert.equal(result.status, "failed");
    assert.equal(result.timed_out, false);
    assert.equal(result.exit_code, mode === "failed" ? 7 : 127);
    await assertStopped(pids());
  });
}
