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













  __testAugmentVitest_78fbbb17e8c5.it("waitForCompactionRetry_rejects_with_aborterror_message_round_006_pass_02", async () => {
    // Session stub
    const session = {
      isCompacting: false,
      subscribe: (_handler: unknown) => {
        return () => {};
      },
    } as any;

    const params = { runId: "wait-unsub-msg", session } as any;
    const { subscribeEmbeddedPiSession } = __testAugmentTarget_ea1b9224ec11;
    const s = subscribeEmbeddedPiSession(params);

    // Unsubscribe first which should cause subsequent waitForCompactionRetry to reject
    s.unsubscribe();

    try {
      await s.waitForCompactionRetry();
      __testAugmentVitest_78fbbb17e8c5.expect(false).toBe(true);
    } catch (err: any) {
      // Verify the reject reason is an AbortError with a helpful message
      __testAugmentVitest_78fbbb17e8c5.expect(err).toBeInstanceOf(Error);
      __testAugmentVitest_78fbbb17e8c5.expect(err.name).toBe("AbortError");
      __testAugmentVitest_78fbbb17e8c5.expect(String(err.message)).toContain("Unsubscribed");
    }
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

import * as __testAugmentTarget_ea1b9224ec11 from "../../../src/agents/pi-embedded-subscribe.js";

const __testAugmentLoadTarget_ea1b9224ec11 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-subscribe.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-subscribe.js");
};
