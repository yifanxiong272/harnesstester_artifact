import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { beforeEach, describe, expect, it } from "vitest";
import { createDoctorRuntime, mockDoctorConfigSnapshot } from "./doctor.e2e-harness.js";
import { loadDoctorCommandForTest, terminalNoteMock } from "./doctor.note-test-helpers.js";
import "./doctor.fast-path-mocks.js";

let doctorCommand: typeof import("./doctor.js").doctorCommand;

describe("doctor command", () => {
  beforeEach(async () => {
    doctorCommand = await loadDoctorCommandForTest({
      unmockModules: ["./doctor-state-integrity.js"],
    });
  });





  __testAugmentVitest_06adeb037ff4.it("migrates nano-banana skill into agents.defaults.imageGenerationModel and models.providers.google.apiKey_round_002", async () => {
    const { normalizeCompatibilityConfigValues } = await __testAugmentLoadTarget_a8b288d3d430();

    const cfg = {
      skills: {
        allowBundled: ["nano-banana-pro"],
        entries: {
          "nano-banana-pro": {
            env: { GEMINI_API_KEY: "gem-key-xyz" },
            apiKey: undefined,
          },
        },
      },
      agents: {},
      models: {},
    } as unknown as Record<string, unknown>;

    const result = normalizeCompatibilityConfigValues(cfg as any);

    // agents.defaults.imageGenerationModel.primary should be set to the expected nano-banana model constant
    const agents = (result.config as any).agents;
    __testAugmentVitest_06adeb037ff4.expect(agents).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect(agents.defaults).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect(agents.defaults.imageGenerationModel).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect(agents.defaults.imageGenerationModel.primary).toBe("google/gemini-3-pro-image-preview");

    // models.providers.google.apiKey should be populated from the legacy env key
    __testAugmentVitest_06adeb037ff4.expect((result.config.models as any).providers).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect((result.config.models as any).providers.google).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect((result.config.models as any).providers.google.apiKey).toBe("gem-key-xyz");

    // legacy skills.entries nano-banana-pro should be removed
    __testAugmentVitest_06adeb037ff4.expect((result.config.skills as any)?.entries?.["nano-banana-pro"]).toBeUndefined();

    // changes should include both the image generation migration and the apiKey migration
    __testAugmentVitest_06adeb037ff4.expect(result.changes.some((c) => String(c).includes("Moved skills.entries.nano-banana-pro → agents.defaults.imageGenerationModel.primary"))).toBe(true);
    __testAugmentVitest_06adeb037ff4.expect(result.changes.some((c) => String(c).includes("Moved skills.entries.nano-banana-pro.env.GEMINI_API_KEY"))).toBe(true);
  });
});

import * as __testAugmentVitest_06adeb037ff4 from "vitest";

const __testAugmentLoadTarget_a8b288d3d430 = async () => {
  __testAugmentVitest_06adeb037ff4.vi.doUnmock("./doctor-legacy-config.js");
  __testAugmentVitest_06adeb037ff4.vi.resetModules();
  return import("./doctor-legacy-config.js");
};
