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













  __testAugmentVitest_78fbbb17e8c5.it("wrapStreamFnSanitizeMalformedToolCalls_normalizes_names_round_001_pass_03", async () => {
    // Provide a deterministic sanitize wrapper implementation
    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/agents/pi-embedded-runner/run/attempt.tool-call-normalization.js", () => ({
      wrapStreamFnSanitizeMalformedToolCalls: (inner, allowedToolNames, policy) => {
        return (model, context, options) => {
          const ctx = { ...(context as Record<string, unknown>) } as Record<string, unknown>;
          if (Array.isArray((ctx as any).messages)) {
            ctx.messages = (ctx as any).messages.map((m: any) => {
              // Simulate a sanitizer: trim and collapse internal whitespace
              if (m && typeof m === "object" && typeof m.toolName === "string") {
                const trimmed = m.toolName.trim().replace(/\s+/g, " ");
                return { ...m, toolName: trimmed };
              }
              return m;
            });
          }
          return inner(model, ctx as unknown as typeof context, options);
        };
      },
    }));

    const mod = await __testAugmentLoadTarget_22dd75644b97();
    const { wrapStreamFnSanitizeMalformedToolCalls } = mod as unknown as {
      wrapStreamFnSanitizeMalformedToolCalls: Function;
    };

    const inner = (_model: unknown, context: any) => context?.messages ?? null;
    const wrapper = wrapStreamFnSanitizeMalformedToolCalls(inner, ["read"], { /* policy stub */ });

    const messages = [{ toolName: "  my   tool  ", meta: 2 }];
    const result = await wrapper(undefined, { messages }, {});

    __testAugmentVitest_78fbbb17e8c5.expect(result[0].toolName).toBe("my tool");
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_22dd75644b97 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-runner/run/attempt.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-runner/run/attempt.js");
};
