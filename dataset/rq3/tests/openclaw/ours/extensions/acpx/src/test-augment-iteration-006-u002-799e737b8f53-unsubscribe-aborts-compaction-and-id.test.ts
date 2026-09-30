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













  __testAugmentVitest_78fbbb17e8c5.it("unsubscribe_aborts_compaction_and_idempotent_round_006", async () => {
    const { subscribeEmbeddedPiSession } = await __testAugmentLoadTarget_ea1b9224ec11();

    // Track whether abortCompaction was invoked and whether sessionUnsubscribe was called
    let abortCalled = 0;
    let sessionUnsubCalled = 0;

    const params = {
      runId: "run-2",
      session: {
        // subscribe returns unsubscribe function that increments a counter when called
        subscribe: (handler: unknown) => {
          sessionUnsubCalled += 0; // no-op to demonstrate presence
          return () => {
            sessionUnsubCalled += 1;
          };
        },
        isCompacting: true,
        abortCompaction: () => {
          // Simulate abortCompaction throwing to exercise the catch path in unsubscribe
          abortCalled += 1;
          throw new Error("simulated-abort-error");
        },
      },
    } as any;

    const instance = subscribeEmbeddedPiSession(params);

    // First unsubscribe should attempt to call abortCompaction and call session unsubscribe
    instance.unsubscribe();
    __testAugmentVitest_78fbbb17e8c5.expect(abortCalled).toBeGreaterThanOrEqual(1);
    __testAugmentVitest_78fbbb17e8c5.expect(sessionUnsubCalled).toBe(1);

    // Calling unsubscribe again should be a no-op (idempotent)
    instance.unsubscribe();
    __testAugmentVitest_78fbbb17e8c5.expect(abortCalled).toBeGreaterThanOrEqual(1);
    __testAugmentVitest_78fbbb17e8c5.expect(sessionUnsubCalled).toBe(1);
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_ea1b9224ec11 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-subscribe.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-subscribe.js");
};
