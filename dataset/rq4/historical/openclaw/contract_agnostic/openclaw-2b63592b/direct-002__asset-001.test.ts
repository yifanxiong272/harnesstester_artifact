import { test, expect } from "vitest";
import { extractShellCommandFromArgv } from "../../infra/system-run-command";

test("posix wrapper empty/whitespace-only embedded command should be null", () => {
  const r1 = extractShellCommandFromArgv(["/bin/sh", "-lc", ""]);
  const r2 = extractShellCommandFromArgv(["/bin/sh", "-c", "   "]);
  const r3 = extractShellCommandFromArgv(["bash", "-c", "\t"]);
  expect([r1, r2, r3]).toEqual([null, null, null]);
});
