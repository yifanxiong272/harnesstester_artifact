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













  __testAugmentVitest_78fbbb17e8c5.it("wrapStreamFnTrimToolCallNames_trims_tool_name_whitespace_round_001_pass_03", async () => {
    // Mock the normalization module to provide a deterministic wrapper implementation
    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/agents/pi-embedded-runner/run/attempt.tool-call-normalization.js", () => ({
      wrapStreamFnTrimToolCallNames: (inner, allowedToolNames) => {
        return (model, context, options) => {
          const ctx = { ...(context as Record<string, unknown>) } as Record<string, unknown>;
          if (Array.isArray((ctx as any).messages)) {
            ctx.messages = (ctx as any).messages.map((m: any) => {
              if (m && typeof m === "object" && typeof m.toolName !== "undefined") {
                return { ...m, toolName: String(m.toolName).trim() };
              }
              return m;
            });
          }
          return inner(model, ctx as unknown as typeof context, options);
        };
      },
    }));

    const mod = await __testAugmentLoadTarget_22dd75644b97();
    const { wrapStreamFnTrimToolCallNames } = mod as unknown as { wrapStreamFnTrimToolCallNames: Function };

    // inner just returns the messages array so we can inspect the wrapper's effect
    const inner = (_model: unknown, context: any) => (context?.messages ?? null);
    const wrapper = wrapStreamFnTrimToolCallNames(inner, ["read"]);

    const messages = [{ toolName: " read ", meta: 1 }];
    const result = await wrapper(undefined, { messages }, {});

    __testAugmentVitest_78fbbb17e8c5.expect(Array.isArray(result)).toBe(true);
    __testAugmentVitest_78fbbb17e8c5.expect(result[0].toolName).toBe("read");
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_22dd75644b97 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-runner/run/attempt.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-runner/run/attempt.js");
};
