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













  __testAugmentVitest_78fbbb17e8c5.it("compaction_retry_promise_resolves_round_006_pass_03", async () => {
    let capturedCtx: any = undefined;
    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/agents/pi-embedded-subscribe.handlers.js", () => ({
      createEmbeddedPiSessionEventHandler: (ctx: any) => {
        capturedCtx = ctx;
        return () => {};
      },
    }));

    const { subscribeEmbeddedPiSession } = await __testAugmentLoadTarget_ea1b9224ec11();

    const params = { runId: "r-comp-1", session: { subscribe: (_h: unknown) => () => {}, isCompacting: false } } as any;
    const inst = subscribeEmbeddedPiSession(params);
    __testAugmentVitest_78fbbb17e8c5.expect(capturedCtx).toBeDefined();

    // Simulate a compaction retry being noted -> this should create the compaction promise
    capturedCtx.noteCompactionRetry();
    __testAugmentVitest_78fbbb17e8c5.expect(inst.isCompacting()).toBe(true);

    const waitPromise = inst.waitForCompactionRetry();
    __testAugmentVitest_78fbbb17e8c5.expect(waitPromise).toBeInstanceOf(Promise);

    // Now resolve the retry; the promise returned by waitForCompactionRetry should settle
    capturedCtx.resolveCompactionRetry();
    await waitPromise; // should not reject

    // After resolution, isCompacting should be false
    __testAugmentVitest_78fbbb17e8c5.expect(inst.isCompacting()).toBe(false);

    inst.unsubscribe();
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_ea1b9224ec11 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-subscribe.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-subscribe.js");
};
