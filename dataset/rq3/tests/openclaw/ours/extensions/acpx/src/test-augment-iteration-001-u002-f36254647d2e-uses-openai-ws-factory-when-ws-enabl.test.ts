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













  __testAugmentVitest_78fbbb17e8c5.it("uses websocket factory when ws enabled and api key_round_001", async () => {
    // Mock the openai ws factory to capture arguments and return a sentinel function
    let captured;
    __testAugmentVitest_78fbbb17e8c5.vi.doMock('../../../src/agents/openai-ws-stream.js', () => ({
      createOpenAIWebSocketStreamFn: (key, sessionId, opts) => {
        captured = { key, sessionId, opts };
        return function wsFn() {
          return 'ws-sentinel';
        };
      },
    }));

    const { resolveEmbeddedAgentStreamFn } = await __testAugmentLoadTarget_22dd75644b97();
    const signal = new AbortController().signal;

    const out = resolveEmbeddedAgentStreamFn({
      currentStreamFn: undefined,
      providerStreamFn: undefined,
      shouldUseWebSocketTransport: true,
      wsApiKey: 'my-ws-key',
      sessionId: 'session-ws-1',
      signal,
      model: { provider: 'openai', api: 'openai' },
    });

    __testAugmentVitest_78fbbb17e8c5.expect(typeof out).toBe('function');
    __testAugmentVitest_78fbbb17e8c5.expect(out()).toBe('ws-sentinel');
    __testAugmentVitest_78fbbb17e8c5.expect(captured.key).toBe('my-ws-key');
    __testAugmentVitest_78fbbb17e8c5.expect(captured.sessionId).toBe('session-ws-1');
    __testAugmentVitest_78fbbb17e8c5.expect(captured.opts && captured.opts.signal).toBe(signal);
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_22dd75644b97 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-runner/run/attempt.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-runner/run/attempt.js");
};
