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













  __testAugmentVitest_78fbbb17e8c5.it("emitToolOutput_calls_onToolResult_and_noop_on_empty_round_006_pass_03", async () => {
    let capturedCtx: any = undefined;

    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/agents/pi-embedded-subscribe.handlers.js", () => ({
      createEmbeddedPiSessionEventHandler: (ctx: any) => {
        capturedCtx = ctx;
        return () => {};
      },
    }));

    // Mock parsing/filtering helpers used by emitToolResultMessage
    const parseSpy = __testAugmentVitest_78fbbb17e8c5.vi.fn(() => ({ text: "CLEANED", mediaUrls: ["u"] }));
    const filterSpy = __testAugmentVitest_78fbbb17e8c5.vi.fn(() => ["u"]);
    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/auto-reply/reply/reply-directives.js", () => ({
      parseReplyDirectives: parseSpy,
    }));
    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/agents/pi-embedded-subscribe.tools.js", () => ({
      filterToolResultMediaUrls: filterSpy,
    }));

    const onToolResult = __testAugmentVitest_78fbbb17e8c5.vi.fn();
    const { subscribeEmbeddedPiSession } = await __testAugmentLoadTarget_ea1b9224ec11();

    const params = {
      runId: "r-tool-1",
      session: { subscribe: (_h: unknown) => () => {}, isCompacting: false },
      onToolResult,
    } as any;

    const inst = subscribeEmbeddedPiSession(params);
    __testAugmentVitest_78fbbb17e8c5.expect(capturedCtx).toBeDefined();

    // 1) emitToolOutput with falsy output should no-op
    capturedCtx.emitToolOutput("ToolA", "meta", "");
    __testAugmentVitest_78fbbb17e8c5.expect(onToolResult).toHaveBeenCalledTimes(0);

    // 2) emitToolOutput with content should call parse -> filter -> onToolResult
    capturedCtx.emitToolOutput("ToolA", "meta", " actual output ", { some: "result" });
    await new Promise((r) => setTimeout(r, 0));

    __testAugmentVitest_78fbbb17e8c5.expect(parseSpy).toHaveBeenCalled();
    __testAugmentVitest_78fbbb17e8c5.expect(filterSpy).toHaveBeenCalledWith("ToolA", ["u"], { some: "result" });
    __testAugmentVitest_78fbbb17e8c5.expect(onToolResult).toHaveBeenCalledTimes(1);
    const arg = onToolResult.mock.calls[0][0];
    __testAugmentVitest_78fbbb17e8c5.expect(arg.text).toBe("CLEANED");
    __testAugmentVitest_78fbbb17e8c5.expect(arg.mediaUrls).toEqual(["u"]);

    inst.unsubscribe();
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_ea1b9224ec11 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-subscribe.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-subscribe.js");
};
