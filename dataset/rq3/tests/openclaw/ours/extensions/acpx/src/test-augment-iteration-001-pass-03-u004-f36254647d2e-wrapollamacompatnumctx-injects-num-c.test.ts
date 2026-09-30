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













  __testAugmentVitest_78fbbb17e8c5.it("wrapOllamaCompatNumCtx_injects_num_ctx_for_ollama_round_001_pass_03", async () => {
    // Mock the plugin-sdk/ollama module to provide a simple wrapper implementation
    __testAugmentVitest_78fbbb17e8c5.vi.doMock("../../../src/plugin-sdk/ollama.js", () => ({
      wrapOllamaCompatNumCtx: (inner) => {
        return (model: any, context: any, options: any) => {
          if (model && model.provider === "ollama") {
            const nextCtx = { ...(context ?? {}), _ollama_injected_num_ctx: true };
            return inner(model, nextCtx, options);
          }
          return inner(model, context, options);
        };
      },
    }));

    const mod = await __testAugmentLoadTarget_22dd75644b97();
    const { wrapOllamaCompatNumCtx } = mod as unknown as { wrapOllamaCompatNumCtx: Function };

    const inner = (_model: any, context: any) => context ?? null;
    const wrapper = wrapOllamaCompatNumCtx(inner);

    const outOllama = await wrapper({ provider: "ollama" }, { foo: 1 }, {});
    __testAugmentVitest_78fbbb17e8c5.expect(outOllama._ollama_injected_num_ctx).toBe(true);

    const outOther = await wrapper({ provider: "openai" }, { foo: 2 }, {});
    __testAugmentVitest_78fbbb17e8c5.expect(outOther._ollama_injected_num_ctx).toBeUndefined();
  });
});

import * as __testAugmentVitest_78fbbb17e8c5 from "vitest";

const __testAugmentLoadTarget_22dd75644b97 = async () => {
  __testAugmentVitest_78fbbb17e8c5.vi.doUnmock("../../../src/agents/pi-embedded-runner/run/attempt.js");
  __testAugmentVitest_78fbbb17e8c5.vi.resetModules();
  return import("../../../src/agents/pi-embedded-runner/run/attempt.js");
};
