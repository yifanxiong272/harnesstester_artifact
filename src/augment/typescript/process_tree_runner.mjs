import { spawn } from "node:child_process";

const [command, ...args] = process.argv.slice(2);
const child = spawn(command, args, {
  stdio: ["ignore", "pipe", "pipe"],
});
child.stdout.pipe(process.stdout);
child.stderr.pipe(process.stderr);

let stopping = false;
let exitTimer;
function stopTree() {
  if (stopping) return;
  stopping = true;
  if (process.platform === "win32") child.kill("SIGTERM");
  else process.kill(-process.pid, "SIGTERM");
  // The synchronous caller KILLs our group after we close our output pipes.
  clearTimeout(exitTimer);
  exitTimer = setTimeout(() => {
    if (process.platform === "win32") child.kill("SIGKILL");
    process.exit(124);
  }, 250);
}
process.on("SIGTERM", stopTree);
process.on("SIGINT", stopTree);
child.on("error", (error) => {
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exit(127);
});
// Drain normal output, but do not wait forever for inherited descendant pipes.
child.on("exit", (code, signal) => {
  process.exitCode = stopping ? 124 : (code ?? (signal ? 128 : 1));
  if (!stopping) exitTimer = setTimeout(() => process.exit(), 250);
});
child.on("close", () => {
  clearTimeout(exitTimer);
});
