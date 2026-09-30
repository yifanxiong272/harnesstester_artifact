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













  __testAugmentVitest_78fbbb17e8c5.it("emitBlockReply_safely_handles_throwing_callback_round_006_pass_03", async () => {
    // Mock handler factory to capture ctx and mock dependent modules
    let capturedCtx: any = undefined;

    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/agents/pi-embedded-subscribe.handlers.js", () => ({
      createEmbeddedPiSessionEventHandler: (ctx: any) => {
        capturedCtx = ctx;
        return () => {};
      },
    }));

    // Mock consumePendingToolMediaIntoReply to return payload as-is so emitBlockReply can proceed
    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/agents/pi-embedded-subscribe.handlers.messages.js", () => ({
      consumePendingToolMediaIntoReply: (state: any, payload: any) => payload,
    }));

    // Spy the logger.warn to validate the catch path when callback throws
    const warnSpy = __testAugmentVitest_78fbbb17e8c5.vi.fn();
    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/logging/subsystem.js", () => ({
      createSubsystemLogger: () => ({ warn: warnSpy, debug: () => {} }),
    }));

    const { subscribeEmbeddedPiSession } = await __testAugmentLoadTarget_ea1b9224ec11();

    // First scenario: onBlockReply throws asynchronously; emitBlockReply should swallow the error
    let seenPayloads: any[] = [];
    const params1 = {
      runId: "r-br-1",
      session: { subscribe: (_h: unknown) => () => {}, isCompacting: false },
      onBlockReply: (p: any) => {
        // throw to exercise the catch branch in emitBlockReplySafely
        throw new Error("boom");
      },
    } as any;

    const inst1 = subscribeEmbeddedPiSession(params1);
    __testAugmentVitest_78fbbb17e8c5.expect(capturedCtx).toBeDefined();

    // Call emitBlockReply with a simple payload; it should schedule the callback and catch the error
    capturedCtx.emitBlockReply({ text: "hi" });

    // allow microtasks to run so the Promise.resolve().then() settles
    await new Promise((r) => setTimeout(r, 0));

    __testAugmentVitest_78fbbb17e8c5.expect(warnSpy.mock.calls.length).toBeGreaterThanOrEqual(1);
    __testAugmentVitest_78fbbb17e8c5.expect(String(warnSpy.mock.calls[0][0])).toContain("block reply callback failed");

    inst1.unsubscribe();

    // Second scenario: onBlockReply receives the consumed payload and we observe it
    const params2 = {
      runId: "r-br-2",
      session: { subscribe: (_h: unknown) => () => {}, isCompacting: false },
      onBlockReply: (p: any) => {
        seenPayloads.push(p);
      },
    } as any;

    const inst2 = subscribeEmbeddedPiSession(params2);
    // Ensure capturedCtx is referring to the latest ctx (createEmbeddedPiSessionEventHandler called per subscription)
    __testAugmentVitest_78fbbb17e8c5.expect(typeof capturedCtx.emitBlockReply).toBe("function");
    capturedCtx.emitBlockReply({ text: "final text", extra: 1 });
    await new Promise((r) => setTimeout(r, 0));

    __testAugmentVitest_78fbbb17e8c5.expect(seenPayloads.length).toBe(1);
    __testAugmentVitest_78fbbb17e8c5.expect(seenPayloads[0].text).toBe("final text");

    inst2.unsubscribe();
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_ea1b9224ec11 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-subscribe.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-subscribe.js");
};
