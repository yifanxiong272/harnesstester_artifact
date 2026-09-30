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













  __testAugmentVitest_78fbbb17e8c5.it("messaging_texts_slice_is_copy_round_006_pass_03", () => {
    const session = {
      isCompacting: false,
      subscribe: (_handler: unknown) => {
        return () => {};
      },
    } as any;

    const params = { runId: "slice-texts", session } as any;
    const { subscribeEmbeddedPiSession } = __testAugmentTarget_ea1b9224ec11;

    const s = subscribeEmbeddedPiSession(params);

    // accessor returns a copy - mutating the returned array should not change subsequent calls
    const first = s.getMessagingToolSentTexts();
    __testAugmentVitest_78fbbb17e8c5.expect(Array.isArray(first)).toBe(true);
    first.push("mutated");

    const second = s.getMessagingToolSentTexts();
    __testAugmentVitest_78fbbb17e8c5.expect(second).not.toContain("mutated");
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

import * as __testAugmentTarget_ea1b9224ec11 from "../../../src/agents/pi-embedded-subscribe.js";

const __testAugmentLoadTarget_ea1b9224ec11 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-subscribe.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-subscribe.js");
};
