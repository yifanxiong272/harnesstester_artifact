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













  __testAugmentVitest_78fbbb17e8c5.it("anthropic_vertex_returns_vertex_fn_round_001", async () => { const vertexSentinel = () => "vertex-sentinel"; __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/agents/anthropic-vertex-stream.js", () => ({ createAnthropicVertexStreamFnForModel: (model) => vertexSentinel })); const target = await __testAugmentLoadTarget_22dd75644b97(); const { resolveEmbeddedAgentStreamFn } = target; const out = resolveEmbeddedAgentStreamFn({ currentStreamFn: undefined, providerStreamFn: undefined, shouldUseWebSocketTransport: false, sessionId: 's4', model: { provider: 'anthropic-vertex', api: 'anthropic', contextWindow: 1 } }); __testAugmentVitest_78fbbb17e8c5.expect(out).toBe(vertexSentinel); });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_22dd75644b97 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-runner/run/attempt.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-runner/run/attempt.js");
};
