import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { describe, expect, it } from "vitest";
import {
  ACPX_BUNDLED_BIN,
  ACPX_PINNED_VERSION,
  createAcpxPluginConfigSchema,
  resolveAcpxPluginRoot,
  resolveAcpxPluginConfig,
} from "./config.js";

describe("acpx plugin config parsing", () => {













  __testAugmentVitest_78fbbb17e8c5.it("reexport_resolveAttemptSpawnWorkspaceDir_round_001_pass_02", async () => {
    // Mock the underlying module that is re-exported so we can verify the re-export points to the same implementation
    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/agents/pi-embedded-runner/run/attempt.thread-helpers.js", () => ({
      resolveAttemptSpawnWorkspaceDir: (opts: unknown) => `spawn-dir-for-${JSON.stringify(opts)}`,
    }));

    const target = await __testAugmentLoadTarget_22dd75644b97();
    const { resolveAttemptSpawnWorkspaceDir } = target;

    const result = resolveAttemptSpawnWorkspaceDir({ sandbox: { enabled: false }, resolvedWorkspace: "/tmp/ws" });
    __testAugmentVitest_78fbbb17e8c5.expect(String(result)).toContain("spawn-dir-for");
    __testAugmentVitest_78fbbb17e8c5.expect(String(result)).toContain("/tmp/ws");
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_22dd75644b97 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-runner/run/attempt.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-runner/run/attempt.js");
};
