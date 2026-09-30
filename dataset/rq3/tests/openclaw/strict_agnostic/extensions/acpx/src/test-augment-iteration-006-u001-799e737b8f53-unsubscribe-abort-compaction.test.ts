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













  __testAugmentVitest_78fbbb17e8c5.it("unsubscribe_aborts_compaction_and_calls_session_unsubscribe_round_006", () => {
    // Minimal session mock: indicates compaction in-flight and exposes abortCompaction
    let abortCalled = false;
    let unsubCalled = false;
    const session = {
      isCompacting: true,
      abortCompaction: () => {
        abortCalled = true;
      },
      subscribe: (_handler: unknown) => {
        // Return an unsubscribe function that marks called
        return () => {
          unsubCalled = true;
        };
      },
    } as any;

    const params = { runId: "run-unsub-abort", session } as any;
    const { subscribeEmbeddedPiSession } = __testAugmentTarget_ea1b9224ec11;

    const sess = subscribeEmbeddedPiSession(params);
    // Trigger unsubscribe path which should call abortCompaction and call sessionUnsubscribe
    sess.unsubscribe();

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
