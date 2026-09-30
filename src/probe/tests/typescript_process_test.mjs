import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { fileURLToPath } from "node:url";
import vm from "node:vm";
import test from "node:test";
import { spawnManagedSync } from "../typescript/runtime/process.mjs";
import {
  formalRoot,
  formalPath,
  formalModule,
  sourceModule,
} from "./typescript_support.mjs";

for (const timeout of [false, true]) {
  test(`managed process smoke: timeout ${timeout}`, async () => {
    const runners = [spawnManagedSync];
    if (formalRoot) {
      runners.push(
        (await formalModule("runtime/process.mjs")).spawnManagedSync,
      );
    }
    const outcomes = runners.map((run) => {
      const managed = run(
        process.execPath,
        [
          "-e",
          timeout
            ? "process.stdout.write('ready'); setInterval(() => {}, 1000);"
            : "process.stdout.write('ready'); process.exitCode = 7;",
        ],
        {
          encoding: "utf8",
          timeout: timeout ? 750 : 5000,
        },
      );
      const { result } = managed;
      assert.equal(result.stdout, "ready");
      assert.equal(result.stderr, "");
      assert.equal(
        managed.process_group_cleanup.attempted,
        process.platform !== "win32",
      );
      assert.equal(result.error?.code, timeout ? "ETIMEDOUT" : undefined);
      if (!timeout) assert.equal(result.status, 7);
      return {
        stdout: result.stdout,
        stderr: result.stderr,
        error: result.error?.code,
      };
    });
    for (const outcome of outcomes) assert.deepEqual(outcome, outcomes[0]);
  });
}

function cleanupTrace(file, scenario) {
  let { source, tree, ts } = sourceModule(file);
  for (const node of [...tree.statements].reverse()) {
    if (ts.isImportDeclaration(node)) {
      source = source.slice(0, node.getStart(tree)) + source.slice(node.end);
    }
  }
  const events = [];
  const timers = [];
  const child = new EventEmitter();
  child.pid = 100;
  child.stdout = { pipe: () => events.push(["pipe", "stdout"]) };
  child.stderr = { pipe: () => events.push(["pipe", "stderr"]) };
  const processes = new Map([
    [200, 100],
    [300, 200],
    [400, 100],
  ]);
  const fakeProcess = new EventEmitter();
  const exit = {};
  let monitor;
  Object.assign(fakeProcess, {
    argv:
      scenario === "missing_command"
        ? ["node", file]
        : ["node", file, "fixture", "arg"],
    env: { FIXTURE: "1" },
    cwd: () => "/fixture",
    stdout: {},
    stderr: { write: (text) => events.push(["stderr", text]) },
    exit: (code) => {
      events.push(["exit", code]);
      throw exit;
    },
    kill: (pid, signal) => {
      events.push(["kill", pid, signal]);
      if (scenario === "kill_error" && pid === 300)
        throw new Error("already exited");
      processes.delete(pid);
    },
  });
  const context = vm.createContext({
    process: fakeProcess,
    spawn(command, args, options) {
      events.push(["spawn", command, args, options]);
      return child;
    },
    spawnSync(command, args, options) {
      events.push(["scan", command, args, options]);
      return {
        status: scenario === "scan_error" ? 1 : 0,
        stdout:
          [...processes].map(([pid, parent]) => `${pid} ${parent}`).join("\n") +
          "\ninvalid row\n",
      };
    },
    setInterval(callback, ms) {
      events.push(["monitor", ms]);
      monitor = callback;
      return 1;
    },
    clearInterval(id) {
      events.push(["clear", id]);
    },
    setTimeout(callback, ms) {
      events.push(["timer", ms]);
      timers.push(callback);
      return { unref: () => events.push(["unref"]) };
    },
  });
  try {
    new vm.Script(source, { filename: file }).runInContext(context);
    monitor();
    // An observed child can leave the current tree; a later child can enter it.
    processes.set(300, 1);
    processes.set(500, 100);
    if (scenario === "spawn_error") {
      child.emit("error", { stack: "fixture spawn error" });
    } else if (scenario === "timeout" || scenario === "close_after_stop") {
      fakeProcess.emit("SIGTERM");
      fakeProcess.emit("SIGINT");
      if (scenario === "close_after_stop") child.emit("close", 0, null);
      timers[0]();
    } else {
      child.emit(
        "close",
        scenario === "signal_exit" ? null : 7,
        scenario === "signal_exit" ? "SIGTERM" : null,
      );
    }
  } catch (error) {
    if (error !== exit) throw error;
  }
  return JSON.parse(JSON.stringify(events));
}

for (const scenario of [
  "missing_command",
  "close",
  "timeout",
  "close_after_stop",
  "signal_exit",
  "spawn_error",
  "scan_error",
  "kill_error",
]) {
  test(
    `process-tree cleanup order matches formal: ${scenario}`,
    { skip: !formalRoot },
    () => {
      const actual = cleanupTrace(
        fileURLToPath(
          new URL(
            "../typescript/runtime/process_tree_runner.mjs",
            import.meta.url,
          ),
        ),
        scenario,
      );
      const expected = cleanupTrace(
        formalPath("runtime/process_tree_runner.mjs"),
        scenario,
      );
      assert.deepEqual(actual, expected);
      const codes = {
        missing_command: 2,
        timeout: 124,
        close_after_stop: 124,
        signal_exit: 128,
        spawn_error: 127,
      };
      assert.deepEqual(actual.at(-1), ["exit", codes[scenario] ?? 7]);
      if (["close", "timeout", "close_after_stop"].includes(scenario)) {
        const signals = actual.filter(([event]) => event === "kill");
        assert.deepEqual(
          signals.slice(0, 3).map(([, pid]) => pid),
          [300, 200, 400],
        );
        const freshScan = actual.findIndex(
          ([event], i) => event === "scan" && i > actual.indexOf(signals[2]),
        );
        assert.ok(freshScan > actual.indexOf(signals[2]));
        assert.ok(signals.some(([, pid]) => pid === 500));
      }
    },
  );
}
