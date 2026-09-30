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













  __testAugmentVitest_78fbbb17e8c5.it("providerStreamFn_precedence_round_001", async () => { const target = await __testAugmentLoadTarget_22dd75644b97(); const { resolveEmbeddedAgentStreamFn } = target; const providerStreamFn = () => "provider-ok"; const currentStreamFn = () => "current-ok"; const out = resolveEmbeddedAgentStreamFn({ currentStreamFn, providerStreamFn, shouldUseWebSocketTransport: false, sessionId: 'sess-1', model: { provider: 'some', api: 'x', contextWindow: 1 } }); __testAugmentVitest_78fbbb17e8c5.expect(out).toBe(providerStreamFn); });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_22dd75644b97 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-runner/run/attempt.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-runner/run/attempt.js");
};
