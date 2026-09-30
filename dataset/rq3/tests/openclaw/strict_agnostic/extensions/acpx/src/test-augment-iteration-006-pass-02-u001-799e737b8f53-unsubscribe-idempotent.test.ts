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













  __testAugmentVitest_78fbbb17e8c5.it("unsubscribe_is_idempotent_round_006_pass_02", () => {
    // Track subscribe/unsubscribe lifecycle calls
    let subscribeCalled = false;
    let unsubCalledCount = 0;
    const session = {
      isCompacting: false,
      abortCompaction: () => {
        // not used in this test
      },
      subscribe: (handler: unknown) => {
        subscribeCalled = true;
        // Return an unsubscribe function that increments a counter
        return () => {
          unsubCalledCount += 1;
        };
      },
    } as any;

    const params = { runId: "idemp", session } as any;
    const { subscribeEmbeddedPiSession } = __testAugmentTarget_ea1b9224ec11;

    const s = subscribeEmbeddedPiSession(params);
    // Calling unsubscribe multiple times should be safe and only call the underlying
    // session unsubscribe once (the internal guard prevents double-teardown).
    s.unsubscribe();
    s.unsubscribe();
    s.unsubscribe();

    __testAugmentVitest_78fbbb17e8c5.expect(subscribeCalled).toBe(true);
    // Underlying subscribe returned unsubscribe should be invoked exactly once
    __testAugmentVitest_78fbbb17e8c5.expect(unsubCalledCount).toBe(1);
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

import * as __testAugmentTarget_ea1b9224ec11 from "../../../src/agents/pi-embedded-subscribe.js";

const __testAugmentLoadTarget_ea1b9224ec11 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-subscribe.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-subscribe.js");
};
