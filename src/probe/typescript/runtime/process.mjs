import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { limitTimeout } from "../run/deadline.mjs";

const PROCESS_TREE_RUNNER = fileURLToPath(
  new URL("./process_tree_runner.mjs", import.meta.url),
);

function cleanupProcessGroup(pid) {
  if (process.platform === "win32" || !Number.isInteger(pid) || pid <= 0) {
    return { attempted: false, pid: pid || null, signal_sent: false };
  }
  try {
    process.kill(-pid, "SIGKILL");
    return { attempted: true, pid, signal_sent: true };
  } catch (error) {
    if (error?.code === "ESRCH") {
      return { attempted: true, pid, signal_sent: false };
    }
    return {
      attempted: true,
      pid,
      signal_sent: false,
      error: String(error.message || error),
    };
  }
}

export function spawnManagedSync(command, args, options = {}) {
  const timeout = limitTimeout(options.timeout || Infinity);
  const result = spawnSync(
    process.execPath,
    [PROCESS_TREE_RUNNER, command, ...args],
    {
      ...options,
      ...(Number.isFinite(timeout)
        ? { timeout: Math.max(1, Math.ceil(timeout)) }
        : {}),
      detached: process.platform !== "win32",
    },
  );
  const cleanup = cleanupProcessGroup(result.pid);
  limitTimeout();
  return {
    result,
    managed_command: [process.execPath, PROCESS_TREE_RUNNER, command, ...args],
    process_group_cleanup: cleanup,
  };
}
