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













  __testAugmentVitest_78fbbb17e8c5.it("returns anthropic vertex factory for anthropic-vertex provider_round_001", async () => {
    // Mock anthropic-vertex factory to return sentinel function
    const sentinel = () => 'anthropic-sentinel';
    __testAugmentVitest_78fbbb17e8c5.vi.doMock('../../../src/agents/anthropic-vertex-stream.js', () => ({
      createAnthropicVertexStreamFnForModel: (model) => {
        // ensure model passed through
        if (!model || model.provider !== 'anthropic-vertex') {
          throw new Error('unexpected model');
        }
        return sentinel;
      },
    }));

    const { resolveEmbeddedAgentStreamFn } = await __testAugmentLoadTarget_22dd75644b97();

    const out = resolveEmbeddedAgentStreamFn({
      currentStreamFn: () => 'current',
      providerStreamFn: undefined,
      shouldUseWebSocketTransport: false,
      wsApiKey: undefined,
      sessionId: 'anthropic-session',
      signal: undefined,
      model: { provider: 'anthropic-vertex', api: 'anthropic-messages' },
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
