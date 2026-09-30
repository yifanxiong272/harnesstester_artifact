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













  __testAugmentVitest_78fbbb17e8c5.it("when ws requested but no api key, returns provided currentStreamFn_round_001_pass_02", async () => {
    const { resolveEmbeddedAgentStreamFn } = await __testAugmentLoadTarget_22dd75644b97();

    const current = () => "current-when-no-key";
    const out = resolveEmbeddedAgentStreamFn({
      currentStreamFn: current,
      providerStreamFn: undefined,
      shouldUseWebSocketTransport: true,
      wsApiKey: undefined, // explicitly no key
      sessionId: "s-2",
      signal: undefined,
      model: { provider: "openai" },
    });

    __testAugmentVitest_78fbbb17e8c5.expect(out).toBe(current);
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_22dd75644b97 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-runner/run/attempt.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-runner/run/attempt.js");
};
