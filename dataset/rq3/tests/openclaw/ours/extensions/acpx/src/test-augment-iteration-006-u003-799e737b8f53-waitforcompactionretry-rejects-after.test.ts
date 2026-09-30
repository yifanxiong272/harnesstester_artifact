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













  __testAugmentVitest_78fbbb17e8c5.it("waitForCompactionRetry_rejects_after_unsubscribe_round_006", async () => {
    const { subscribeEmbeddedPiSession } = await __testAugmentLoadTarget_ea1b9224ec11();

    const params = {
      runId: "run-3",
      session: {
        subscribe: (_handler: unknown) => {
          return () => {
            /* noop */
          };
        },
        isCompacting: false,
      },
    } as any;

    const instance = subscribeEmbeddedPiSession(params);

    // Unsubscribe first so waitForCompactionRetry immediately rejects with AbortError
    instance.unsubscribe();

    try {
      await instance.waitForCompactionRetry();
      // If it resolves, that's unexpected
      __testAugmentVitest_78fbbb17e8c5.expect(false).toBe(true);
    } catch (err: any) {
      __testAugmentVitest_78fbbb17e8c5.expect(err).toBeInstanceOf(Error);
      __testAugmentVitest_78fbbb17e8c5.expect(err.name).toBe("AbortError");
    }
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_ea1b9224ec11 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-subscribe.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-subscribe.js");
};
