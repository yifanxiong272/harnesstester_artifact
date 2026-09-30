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













  __testAugmentVitest_78fbbb17e8c5.it("ingress-must-explicitly-set-senderIsOwner_round_009", async () => {
    const { agentCommandFromIngress } = __testAugmentTarget_fe80b95b94a1;
    // Call with no senderIsOwner to exercise the early validation branch.
    await __testAugmentVitest_78fbbb17e8c5.expect(
      // agentCommandFromIngress is async; if it throws synchronously it becomes a rejected Promise.
      agentCommandFromIngress({} as any)
    ).rejects.toThrow("senderIsOwner must be explicitly set for ingress agent runs.");
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

import * as __testAugmentTarget_fe80b95b94a1 from "../../../src/agents/agent-command.js";

const __testAugmentLoadTarget_fe80b95b94a1 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/agent-command.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/agent-command.js");
};
