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













  __testAugmentVitest_78fbbb17e8c5.it("providerStreamFn_wins_even_if_ws_requested_round_001_pass_02", async () => {
    const providerSentinel = () => "provider-sentinel";
    // Ensure websocket factory would exist but shouldn't be invoked
    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/agents/openai-ws-stream.js", () => ({
      createOpenAIWebSocketStreamFn: () => { throw new Error("ws-factory-should-not-be-called"); },
    }));

    const target = await __testAugmentLoadTarget_22dd75644b97();
    const { resolveEmbeddedAgentStreamFn } = target;

    const out = resolveEmbeddedAgentStreamFn({
      currentStreamFn: () => "current",
      providerStreamFn: providerSentinel,
      shouldUseWebSocketTransport: true,
      wsApiKey: "some-key",
      sessionId: "sess-provider-win",
      model: { provider: "openai", api: "openai-responses", contextWindow: 1 },
    });

    __testAugmentVitest_78fbbb17e8c5.expect(out).toBe(providerSentinel);
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_22dd75644b97 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-runner/run/attempt.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-runner/run/attempt.js");
};
