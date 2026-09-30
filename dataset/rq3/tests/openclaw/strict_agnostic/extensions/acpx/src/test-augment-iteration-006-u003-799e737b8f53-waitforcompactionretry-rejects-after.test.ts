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













  __testAugmentVitest_78fbbb17e8c5.it("waitForCompactionRetry_rejects_if_unsubscribed_round_006", async () => {
    const session = {
      isCompacting: false,
      subscribe: (_handler: unknown) => {
        return () => {};
      },
    } as any;

    const params = { runId: "run-wait-unsub", session } as any;
    const { subscribeEmbeddedPiSession } = __testAugmentTarget_ea1b9224ec11;

    const sess = subscribeEmbeddedPiSession(params);
    // Unsubscribe first - this sets internal unsubscribed flag
    sess.unsubscribe();

    try {
      await sess.waitForCompactionRetry();
      // If it didn't reject, that's a failure
      __testAugmentVitest_78fbbb17e8c5.expect(false).toBe(true);
    } catch (err: any) {
      __testAugmentVitest_78fbbb17e8c5.expect(err).toBeInstanceOf(Error);
      __testAugmentVitest_78fbbb17e8c5.expect(err.name).toBe("AbortError");
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
