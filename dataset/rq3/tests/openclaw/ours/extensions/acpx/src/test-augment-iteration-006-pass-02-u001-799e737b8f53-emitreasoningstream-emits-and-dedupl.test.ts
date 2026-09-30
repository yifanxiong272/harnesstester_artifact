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













  __testAugmentVitest_78fbbb17e8c5.it("emitReasoningStream_emits_and_deduplicates_round_006_pass_02", async () => {
    // Capture ctx from createEmbeddedPiSessionEventHandler and spy on emitAgentEvent
    let capturedCtx: any = undefined;
    const emitAgentEventSpy = __testAugmentVitest_78fbbb17e8c5.vi.fn();
    const formatReasoningMessageSpy = __testAugmentVitest_78fbbb17e8c5.vi.fn((t: string) => `FMT:${t}`);

    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/agents/pi-embedded-subscribe.handlers.js", () => ({
      createEmbeddedPiSessionEventHandler: (ctx: any) => {
        capturedCtx = ctx;
        // Handler returned to session.subscribe is irrelevant for this test.
        return () => {};
      },
    }));
    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/infra/agent-events.js", () => ({
      emitAgentEvent: emitAgentEventSpy,
    }));
    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/agents/pi-embedded-utils.js", () => ({
      formatReasoningMessage: formatReasoningMessageSpy,
      stripDowngradedToolCallText: (s: string) => s,
    }));

    const { subscribeEmbeddedPiSession } = await __testAugmentLoadTarget_ea1b9224ec11();

    const onReasoningStream = __testAugmentVitest_78fbbb17e8c5.vi.fn();
    const params = {
      runId: "r-em-1",
      reasoningMode: "stream",
      onReasoningStream,
      session: {
        subscribe: (_handler: unknown) => {
          // do nothing; returned unsubscribe
          return () => {};
        },
        isCompacting: false,
      },
    } as any;

    const inst = subscribeEmbeddedPiSession(params);
    __testAugmentVitest_78fbbb17e8c5.expect(capturedCtx).toBeDefined();

    // First call should emit
    capturedCtx.emitReasoningStream("hello");
    __testAugmentVitest_78fbbb17e8c5.expect(formatReasoningMessageSpy).toHaveBeenCalledWith("hello");
    __testAugmentVitest_78fbbb17e8c5.expect(emitAgentEventSpy).toHaveBeenCalledTimes(1);
    const firstCallArg = emitAgentEventSpy.mock.calls[0][0];
    __testAugmentVitest_78fbbb17e8c5.expect(firstCallArg.runId).toBe("r-em-1");
    __testAugmentVitest_78fbbb17e8c5.expect(firstCallArg.stream).toBe("thinking");
    __testAugmentVitest_78fbbb17e8c5.expect(firstCallArg.data && firstCallArg.data.text).toBe("FMT:hello");
    __testAugmentVitest_78fbbb17e8c5.expect(onReasoningStream).toHaveBeenCalledWith({ text: "FMT:hello" });

    // Second call with same input should not re-emit due to dedupe
    capturedCtx.emitReasoningStream("hello");
    __testAugmentVitest_78fbbb17e8c5.expect(emitAgentEventSpy).toHaveBeenCalledTimes(1);
    __testAugmentVitest_78fbbb17e8c5.expect(onReasoningStream).toHaveBeenCalledTimes(1);

    // Another different input should emit again
    capturedCtx.emitReasoningStream("updated");
    __testAugmentVitest_78fbbb17e8c5.expect(emitAgentEventSpy).toHaveBeenCalledTimes(2);
    const secondCallArg = emitAgentEventSpy.mock.calls[1][0];
    __testAugmentVitest_78fbbb17e8c5.expect(secondCallArg.data.text).toBe("FMT:updated");

    // cleanup
    inst.unsubscribe();
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_ea1b9224ec11 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-subscribe.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-subscribe.js");
};
