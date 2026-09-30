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













  __testAugmentVitest_78fbbb17e8c5.it("assistant_text_via_emitBlockChunk_round_006_pass_03", async () => {
    let capturedCtx: any = undefined;

    // Mock helpers so emitBlockChunk doesn't early-skip or try to emit block replies
    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/agents/pi-embedded-helpers.js", () => ({
      normalizeTextForComparison: (s: string) => (s == null ? "" : String(s).trim().toLowerCase()),
      isMessagingToolDuplicateNormalized: (_norm: string, _list: string[]) => false,
    }));

    // Ensure downgraded tool-call stripping is identity for simplicity
    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/agents/pi-embedded-utils.js", () => ({
      stripDowngradedToolCallText: (s: string) => s,
      formatReasoningMessage: (t: string) => t,
    }));

    // Capture the ctx passed into the session event handler
    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/agents/pi-embedded-subscribe.handlers.js", () => ({
      createEmbeddedPiSessionEventHandler: (ctx: any) => {
        capturedCtx = ctx;
        return () => {};
      },
    }));

    const { subscribeEmbeddedPiSession } = await __testAugmentLoadTarget_ea1b9224ec11();

    const params = {
      runId: "r-as-emit-1",
      // No onBlockReply -> emitBlockChunk will push assistantTexts and return before directive splitting
      session: {
        subscribe: (_handler: unknown) => {
          return () => {};
        },
        isCompacting: false,
      },
    } as any;

    const inst = subscribeEmbeddedPiSession(params);
    __testAugmentVitest_78fbbb17e8c5.expect(capturedCtx).toBeDefined();

    // First emit should add the chunk to assistantTexts
    capturedCtx.emitBlockChunk("Hello world");
    __testAugmentVitest_78fbbb17e8c5.expect(Array.isArray(inst.assistantTexts)).toBe(true);
    __testAugmentVitest_78fbbb17e8c5.expect(inst.assistantTexts.length).toBe(1);
    __testAugmentVitest_78fbbb17e8c5.expect(inst.assistantTexts[0]).toBe("Hello world");

    // Emitting the same trimmed text again should be skipped (deduped)
    capturedCtx.emitBlockChunk("Hello world");
    __testAugmentVitest_78fbbb17e8c5.expect(inst.assistantTexts.length).toBe(1);

    // Emitting different text should append
    capturedCtx.emitBlockChunk("Another chunk");
    __testAugmentVitest_78fbbb17e8c5.expect(inst.assistantTexts.length).toBe(2);
    __testAugmentVitest_78fbbb17e8c5.expect(inst.assistantTexts[1]).toBe("Another chunk");

    inst.unsubscribe();
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_ea1b9224ec11 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-subscribe.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-subscribe.js");
};
