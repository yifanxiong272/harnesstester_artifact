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













  __testAugmentVitest_78fbbb17e8c5.it("websocket_no_key_keeps_current_round_001", async () => { const target = await __testAugmentLoadTarget_22dd75644b97(); const { resolveEmbeddedAgentStreamFn } = target; const currentStreamFn = () => "current-only"; const out = resolveEmbeddedAgentStreamFn({ currentStreamFn, providerStreamFn: undefined, shouldUseWebSocketTransport: true, /* no wsApiKey */ sessionId: 's3', model: { provider: 'openai', api: 'openai-responses', contextWindow: 1 } }); __testAugmentVitest_78fbbb17e8c5.expect(out).toBe(currentStreamFn); });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_22dd75644b97 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-runner/run/attempt.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-runner/run/attempt.js");
};
