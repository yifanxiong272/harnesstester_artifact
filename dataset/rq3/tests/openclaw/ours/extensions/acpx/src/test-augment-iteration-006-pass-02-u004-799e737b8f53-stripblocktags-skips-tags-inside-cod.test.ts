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













  __testAugmentVitest_78fbbb17e8c5.it("stripBlockTags_skips_tags_inside_code_spans_round_006_pass_02", async () => {
    let capturedCtx: any = undefined;

    // Build code span index that reports the tag at index 0 is inside a code span
    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/markdown/code-spans.js", () => ({
      createInlineCodeState: () => ({}),
      buildCodeSpanIndex: (text: string, _state: any) => {
        return {
          inlineState: {},
          isInside: (idx: number) => idx === 0, // report index 0 as inside code span
        };
      },
    }));

    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/agents/pi-embedded-subscribe.handlers.js", () => ({
      createEmbeddedPiSessionEventHandler: (ctx: any) => {
        capturedCtx = ctx;
        return () => {};
      },
    }));

    const { subscribeEmbeddedPiSession } = await __testAugmentLoadTarget_ea1b9224ec11();

    const params = {
      runId: "r-str-3",
      enforceFinalTag: false,
      session: { subscribe: (_h: unknown) => () => {}, isCompacting: false },
    } as any;

    const inst = subscribeEmbeddedPiSession(params);
    __testAugmentVitest_78fbbb17e8c5.expect(capturedCtx).toBeDefined();

    // Place a <think> tag at index 0; isInside(0) will be true so tag should NOT be stripped
    const input = "<think>secret</think>VISIBLE";
    const out = capturedCtx.stripBlockTags(input, { thinking: false, final: false, inlineCode: {} });
    __testAugmentVitest_78fbbb17e8c5.expect(out.includes("<think>")).toBe(true);
    __testAugmentVitest_78fbbb17e8c5.expect(out.includes("secret")).toBe(true);

    inst.unsubscribe();
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_ea1b9224ec11 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-subscribe.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-subscribe.js");
};
