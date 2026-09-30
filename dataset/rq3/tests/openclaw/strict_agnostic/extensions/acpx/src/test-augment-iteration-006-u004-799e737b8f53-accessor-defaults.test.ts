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













  __testAugmentVitest_78fbbb17e8c5.it("accessor_defaults_and_compaction_count_round_006", () => {
    const session = {
      isCompacting: false,
      subscribe: (_handler: unknown) => {
        return () => {};
      },
    } as any;

    const params = { runId: "run-accessors", session } as any;
    const { subscribeEmbeddedPiSession } = __testAugmentTarget_ea1b9224ec11;

    const s = subscribeEmbeddedPiSession(params);

    __testAugmentVitest_78fbbb17e8c5.expect(s.getMessagingToolSentTexts()).toEqual([]);
    __testAugmentVitest_78fbbb17e8c5.expect(s.getMessagingToolSentMediaUrls()).toEqual([]);
    __testAugmentVitest_78fbbb17e8c5.expect(s.getMessagingToolSentTargets()).toEqual([]);
    __testAugmentVitest_78fbbb17e8c5.expect(s.getSuccessfulCronAdds()).toBe(0);
    __testAugmentVitest_78fbbb17e8c5.expect(s.didSendViaMessagingTool()).toBe(false);
    __testAugmentVitest_78fbbb17e8c5.expect(s.didSendDeterministicApprovalPrompt()).toBe(false);
    __testAugmentVitest_78fbbb17e8c5.expect(s.getLastToolError()).toBeUndefined();
    __testAugmentVitest_78fbbb17e8c5.expect(s.getUsageTotals()).toBeUndefined();
    __testAugmentVitest_78fbbb17e8c5.expect(s.getCompactionCount()).toBe(0);
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

import * as __testAugmentTarget_ea1b9224ec11 from "../../../src/agents/pi-embedded-subscribe.js";

const __testAugmentLoadTarget_ea1b9224ec11 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-subscribe.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-subscribe.js");
};
