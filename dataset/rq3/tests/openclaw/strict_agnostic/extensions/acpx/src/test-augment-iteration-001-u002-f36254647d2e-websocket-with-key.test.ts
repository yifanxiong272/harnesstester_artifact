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













  __testAugmentVitest_78fbbb17e8c5.it("websocket_with_key_uses_openai_ws_round_001", async () => { const wsSentinel = () => "ws-sentinel"; __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/agents/openai-ws-stream.js", () => ({ createOpenAIWebSocketStreamFn: (key, sessionId, opts) => wsSentinel })); const target = await __testAugmentLoadTarget_22dd75644b97(); const { resolveEmbeddedAgentStreamFn } = target; const currentStreamFn = () => "current"; const out = resolveEmbeddedAgentStreamFn({ currentStreamFn, providerStreamFn: undefined, shouldUseWebSocketTransport: true, wsApiKey: 'API-KEY', sessionId: 's2', signal: undefined, model: { provider: 'openai', api: 'openai-responses', contextWindow: 1 } }); __testAugmentVitest_78fbbb17e8c5.expect(out).toBe(wsSentinel); });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_22dd75644b97 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-runner/run/attempt.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-runner/run/attempt.js");
};
