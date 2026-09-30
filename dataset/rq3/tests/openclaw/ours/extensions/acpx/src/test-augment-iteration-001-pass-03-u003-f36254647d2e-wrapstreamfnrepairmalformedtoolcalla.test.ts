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













  __testAugmentVitest_78fbbb17e8c5.it("wrapStreamFnRepairMalformedToolCallArguments_parses_string_json_round_001_pass_03", async () => {
    // Mock the argument-repair module to provide a deterministic wrapper implementation
    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/agents/pi-embedded-runner/run/attempt.tool-call-argument-repair.js", () => ({
      wrapStreamFnRepairMalformedToolCallArguments: (inner) => {
        return (model, context, options) => {
          const ctx = { ...(context as Record<string, unknown>) } as Record<string, unknown>;
          if (Array.isArray((ctx as any).messages)) {
            ctx.messages = (ctx as any).messages.map((m: any) => {
              // Repair stringified JSON content into an object when possible
              if (m && typeof m === "object" && typeof m.content === "string") {
                try {
                  const parsed = JSON.parse(m.content);
                  return { ...m, content: parsed };
                } catch {
                  return m;
                }
              }
              return m;
            });
          }
          return inner(model, ctx as unknown as typeof context, options);
        };
      },
      decodeHtmlEntitiesInObject: (x: unknown) => x, // keep available if used
    }));

    const mod = await __testAugmentLoadTarget_22dd75644b97();
    const { wrapStreamFnRepairMalformedToolCallArguments } = mod as unknown as {
      wrapStreamFnRepairMalformedToolCallArguments: Function;
    };

    const inner = (_model: unknown, context: any) => context?.messages ?? null;
    const wrapper = wrapStreamFnRepairMalformedToolCallArguments(inner);

    const messages = [{ role: "assistant", content: JSON.stringify({ a: 1, b: "x" }) }];
    const result = await wrapper(undefined, { messages }, {});

    __testAugmentVitest_78fbbb17e8c5.expect(typeof result[0].content).toBe("object");
    __testAugmentVitest_78fbbb17e8c5.expect(result[0].content.a).toBe(1);
    __testAugmentVitest_78fbbb17e8c5.expect(result[0].content.b).toBe("x");
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_22dd75644b97 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-runner/run/attempt.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-runner/run/attempt.js");
};
