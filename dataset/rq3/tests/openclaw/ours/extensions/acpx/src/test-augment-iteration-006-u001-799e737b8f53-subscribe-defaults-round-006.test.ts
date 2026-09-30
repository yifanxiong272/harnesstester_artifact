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













  __testAugmentVitest_78fbbb17e8c5.it("subscribe_defaults_round_006", async () => {
    // Load the target module to access exported subscribeEmbeddedPiSession
    const { subscribeEmbeddedPiSession } = await __testAugmentLoadTarget_ea1b9224ec11();

    // Create a minimal fake session implementation that records subscribe/unsubscribe
    let subscribeCalled = false;
    let unsubCalled = false;
    const params = {
      runId: "run-1",
      session: {
        subscribe: (handler: unknown) => {
          subscribeCalled = true;
          return () => {
            unsubCalled = true;
          };
        },
        isCompacting: false,
      },
    } as any;

    const instance = subscribeEmbeddedPiSession(params);

    // Basic shape and defaults
    __testAugmentVitest_78fbbb17e8c5.expect(instance).toBeTruthy();
    __testAugmentVitest_78fbbb17e8c5.expect(Array.isArray(instance.assistantTexts)).toBe(true);
    __testAugmentVitest_78fbbb17e8c5.expect(instance.assistantTexts.length).toBe(0);
    __testAugmentVitest_78fbbb17e8c5.expect(Array.isArray(instance.toolMetas)).toBe(true);
    __testAugmentVitest_78fbbb17e8c5.expect(instance.toolMetas.length).toBe(0);
    __testAugmentVitest_78fbbb17e8c5.expect(instance.getCompactionCount()).toBe(0);
    __testAugmentVitest_78fbbb17e8c5.expect(instance.didSendViaMessagingTool()).toBe(false);
    __testAugmentVitest_78fbbb17e8c5.expect(instance.didSendDeterministicApprovalPrompt()).toBe(false);
    __testAugmentVitest_78fbbb17e8c5.expect(instance.getLastToolError()).toBeUndefined();
    __testAugmentVitest_78fbbb17e8c5.expect(instance.getUsageTotals()).toBeUndefined();
    __testAugmentVitest_78fbbb17e8c5.expect(instance.isCompacting()).toBe(false);
    __testAugmentVitest_78fbbb17e8c5.expect(instance.isCompactionInFlight()).toBe(false);

    // subscribe should have been called by the constructor
    __testAugmentVitest_78fbbb17e8c5.expect(subscribeCalled).toBe(true);

    // cleanup
    instance.unsubscribe();
    __testAugmentVitest_78fbbb17e8c5.expect(unsubCalled).toBe(true);
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_ea1b9224ec11 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-subscribe.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-subscribe.js");
};
