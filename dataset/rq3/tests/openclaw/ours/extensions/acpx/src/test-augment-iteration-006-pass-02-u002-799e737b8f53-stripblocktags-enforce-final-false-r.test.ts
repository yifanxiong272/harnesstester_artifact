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













  __testAugmentVitest_78fbbb17e8c5.it("stripBlockTags_enforce_final_false_round_006_pass_02", async () => {
    let capturedCtx: any = undefined;
    // Provide a code-spans module where no index is considered inside a code span.
    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/markdown/code-spans.js", () => ({
      createInlineCodeState: () => ({}),
      buildCodeSpanIndex: (_text: string, _state: any) => ({
        isInside: (_idx: number) => false,
        inlineState: {},
      }),
    }));

    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/agents/pi-embedded-subscribe.handlers.js", () => ({
      createEmbeddedPiSessionEventHandler: (ctx: any) => {
        capturedCtx = ctx;
        return () => {};
      },
    }));

    const { subscribeEmbeddedPiSession } = await __testAugmentLoadTarget_ea1b9224ec11();

    const params = {
      runId: "r-str-1",
      enforceFinalTag: false,
      session: {
        subscribe: (_handler: unknown) => () => {},
        isCompacting: false,
      },
    } as any;

    const inst = subscribeEmbeddedPiSession(params);
    __testAugmentVitest_78fbbb17e8c5.expect(capturedCtx).toBeDefined();

    const input = "Hello <final>Secret</final> World";
    const out = capturedCtx.stripBlockTags(input, { thinking: false, final: false, inlineCode: {} });
    // With enforcement disabled we strip the <final> tags but keep inner content
    __testAugmentVitest_78fbbb17e8c5.expect(out).toBe("Hello Secret World");

    inst.unsubscribe();
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_ea1b9224ec11 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-subscribe.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-subscribe.js");
};
