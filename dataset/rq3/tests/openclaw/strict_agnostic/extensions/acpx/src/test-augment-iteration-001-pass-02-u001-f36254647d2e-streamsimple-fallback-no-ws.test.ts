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













  __testAugmentVitest_78fbbb17e8c5.it("streamSimple_fallback_no_ws_round_001_pass_02", async () => {
    const sentinel = () => "stream-simple-sentinel";
    __testAugmentVitest_78fbbb17e8c5.vi.doMock("@mariozechner/pi-ai", () => ({ streamSimple: sentinel }));
    const target = await __testAugmentLoadTarget_22dd75644b97();
    const { resolveEmbeddedAgentStreamFn } = target;

    const out = resolveEmbeddedAgentStreamFn({
      currentStreamFn: undefined,
      providerStreamFn: undefined,
      shouldUseWebSocketTransport: false,
      sessionId: "sess-fallback-1",
      model: { provider: "not-anthropic", api: "x", contextWindow: 1 },
    });

    // Should return the mocked streamSimple function when no currentStreamFn is provided
    __testAugmentVitest_78fbbb17e8c5.expect(out).toBe(sentinel);
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_22dd75644b97 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-runner/run/attempt.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-runner/run/attempt.js");
};
