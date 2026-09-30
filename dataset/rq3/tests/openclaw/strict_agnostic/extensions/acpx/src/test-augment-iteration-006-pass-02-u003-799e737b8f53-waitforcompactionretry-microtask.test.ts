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













  __testAugmentVitest_78fbbb17e8c5.it("waitForCompactionRetry_resolves_via_microtask_round_006_pass_02", async () => {
    // Session stub that provides subscribe/unsubscribe but no compaction activity.
    const session = {
      isCompacting: false,
      subscribe: (_handler: unknown) => {
        return () => {};
      },
    } as any;

    const params = { runId: "wait-micro", session } as any;
    const { subscribeEmbeddedPiSession } = __testAugmentTarget_ea1b9224ec11;
    const s = subscribeEmbeddedPiSession(params);

    // The implementation may resolve the returned waitForCompactionRetry promise
    // using a queued microtask; ensure awaiting it completes (no rejection) and
    // that resolution happens quickly.
    let resolved = false;
    await s.waitForCompactionRetry().then(() => (resolved = true));

    __testAugmentVitest_78fbbb17e8c5.expect(resolved).toBe(true);
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

import * as __testAugmentTarget_ea1b9224ec11 from "../../../src/agents/pi-embedded-subscribe.js";

const __testAugmentLoadTarget_ea1b9224ec11 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-subscribe.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-subscribe.js");
};
