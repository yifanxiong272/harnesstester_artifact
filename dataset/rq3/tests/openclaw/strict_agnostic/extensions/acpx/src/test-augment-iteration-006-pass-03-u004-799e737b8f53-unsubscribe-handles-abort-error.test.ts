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













  __testAugmentVitest_78fbbb17e8c5.it("unsubscribe_handles_abort_compaction_throw_round_006_pass_03", () => {
    let abortCalled = false;
    let unsubCalled = false;
    const session = {
      isCompacting: true,
      abortCompaction: () => {
        abortCalled = true;
        throw new Error("boom abort");
      },
      subscribe: (_handler: unknown) => {
        return () => {
          unsubCalled = true;
        };
      },
    } as any;

    const params = { runId: "abort-throws", session } as any;
    const { subscribeEmbeddedPiSession } = __testAugmentTarget_ea1b9224ec11;

    const s = subscribeEmbeddedPiSession(params);

    // Should not throw even if abortCompaction throws; the implementation catches and continues
    __testAugmentVitest_78fbbb17e8c5.expect(() => s.unsubscribe()).not.toThrow();
    __testAugmentVitest_78fbbb17e8c5.expect(abortCalled).toBe(true);
    __testAugmentVitest_78fbbb17e8c5.expect(unsubCalled).toBe(true);
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

import * as __testAugmentTarget_ea1b9224ec11 from "../../../src/agents/pi-embedded-subscribe.js";

const __testAugmentLoadTarget_ea1b9224ec11 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-subscribe.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-subscribe.js");
};
