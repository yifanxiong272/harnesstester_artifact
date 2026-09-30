import { test, expect } from "vitest";
import { extractShellCommandFromArgv } from "../../infra/system-run-command";

test("posix shells: whitespace-only extracted commands are treated as absent (null)", () => {
  const cases = [
    ["/bin/sh", "-c", "   "],
    ["/USR/BIN/SH", " -c ", "\t  "],
    ["/bin/bash", "-lc", undefined],
  ];

  const results = cases.map((argv) => extractShellCommandFromArgv(argv as unknown as string[]));
  expect(results).toEqual([null, null, null]);
});
