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













  __testAugmentVitest_78fbbb17e8c5.it("returns providerStreamFn when provided_round_001", async () => {
    // No mocks needed: ensure providerStreamFn is returned verbatim regardless of other params
    const { resolveEmbeddedAgentStreamFn } = await __testAugmentLoadTarget_22dd75644b97();
    const providerFn = () => {
      return "provider-fn";
    };

    const out = resolveEmbeddedAgentStreamFn({
      providerStreamFn: providerFn,
      currentStreamFn: undefined,
      shouldUseWebSocketTransport: true,
      wsApiKey: "irrelevant",
      sessionId: "session-1",
      signal: new AbortController().signal,
      model: { provider: "openai", api: "x" },
    });

    __testAugmentVitest_78fbbb17e8c5.expect(out).toBe(providerFn);
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_22dd75644b97 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-runner/run/attempt.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-runner/run/attempt.js");
};
