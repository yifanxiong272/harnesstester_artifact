#!/usr/bin/env node
import { spawn, spawnSync } from "node:child_process";

const [command, ...args] = process.argv.slice(2);
if (!command) {
  process.stderr.write("process_tree_runner: missing command\n");
  process.exit(2);
}

function processRows() {
  const result = spawnSync("ps", ["-axo", "pid=,ppid="], { encoding: "utf8" });
  if (result.status !== 0) {
    return [];
  }
  return result.stdout
    .split(/\r?\n/u)
    .map((line) => line.trim().split(/\s+/u).map(Number))
    .filter(([pid, ppid]) => Number.isInteger(pid) && Number.isInteger(ppid));
}

function descendants(rootPid) {
  const byParent = new Map();
  for (const [pid, ppid] of processRows()) {
    const children = byParent.get(ppid) || [];
    children.push(pid);
    byParent.set(ppid, children);
  }
  const found = [];
  const visit = (pid) => {
    for (const childPid of byParent.get(pid) || []) {
      visit(childPid);
      found.push(childPid);
    }
  };
  visit(rootPid);
  return found;
}

function signalProcesses(pids, signal) {
  for (const pid of pids) {
    try {
      process.kill(pid, signal);
    } catch {
      // Already exited.
    }
  }
}

function signalTree(rootPid, signal) {
  signalProcesses(observedDescendants, signal);
  signalProcesses([...descendants(rootPid), rootPid], signal);
}

const child = spawn(command, args, {
  cwd: process.cwd(),
  env: process.env,
  stdio: ["ignore", "pipe", "pipe"],
});
child.stdout.pipe(process.stdout);
child.stderr.pipe(process.stderr);
const observedDescendants = new Set();
const monitor = setInterval(() => {
  for (const pid of descendants(child.pid)) {
    observedDescendants.add(pid);
  }
}, 50);

let stopping = false;
function stopTree() {
  if (stopping) {
    return;
  }
  stopping = true;
  clearInterval(monitor);
  signalTree(child.pid, "SIGTERM");
  setTimeout(() => {
    signalTree(child.pid, "SIGKILL");
    process.exit(124);
  }, 250).unref();
}

process.on("SIGTERM", stopTree);
process.on("SIGINT", stopTree);
child.on("error", (error) => {
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exit(127);
});
child.on("close", (code, signal) => {
  clearInterval(monitor);
  signalTree(child.pid, "SIGKILL");
  if (stopping) {
    process.exit(124);
  }
  process.exit(code ?? (signal ? 128 : 1));
});
