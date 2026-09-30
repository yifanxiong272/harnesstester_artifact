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













  __testAugmentVitest_78fbbb17e8c5.it("falls back to streamSimple when no ws key_round_001", async () => {
    // Provide a sentinel streamSimple and ensure websocket factory is not used
    const sentinel = () => 'streamSimple-sentinel';
    __testAugmentVitest_78fbbb17e8c5.vi.doMock('@mariozechner/pi-ai', () => ({ streamSimple: sentinel }));
    // If the openai ws factory is called this test should fail — mock to throw
    __testAugmentVitest_78fbbb17e8c5.vi.doMock('../../../src/agents/openai-ws-stream.js', () => ({
      createOpenAIWebSocketStreamFn: () => {
        throw new Error('openai ws factory should not be called in this scenario');
      },
    }));

    const { resolveEmbeddedAgentStreamFn } = await __testAugmentLoadTarget_22dd75644b97();

    const out = resolveEmbeddedAgentStreamFn({
      currentStreamFn: undefined, // will default to streamSimple
      providerStreamFn: undefined,
      shouldUseWebSocketTransport: true,
      wsApiKey: undefined, // no key -> should not create ws fn
      sessionId: 's-no-key',
      signal: undefined,
      model: { provider: 'openai' },
    });

    __testAugmentVitest_78fbbb17e8c5.expect(out).toBe(sentinel);
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_22dd75644b97 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-runner/run/attempt.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-runner/run/attempt.js");
};
