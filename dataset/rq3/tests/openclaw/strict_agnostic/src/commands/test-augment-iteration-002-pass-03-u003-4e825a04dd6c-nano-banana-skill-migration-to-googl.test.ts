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





  __testAugmentVitest_06adeb037ff4.it("migrates-nano-banana-skill-into-models-and-agents_round_002_pass_03", async () => {
    const mod = await __testAugmentLoadTarget_a8b288d3d430();
    const { normalizeCompatibilityConfigValues } = mod;

    const cfg = {
      skills: {
        allowBundled: ["nano-banana-pro", "other"],
        entries: {
          "nano-banana-pro": {
            env: { GEMINI_API_KEY: "  KEY-ABC  " },
            apiKey: undefined,
          },
        },
      },
      // make sure no existing google provider api key so migration will set it
      models: {},
    };

    const { config, changes } = normalizeCompatibilityConfigValues(cfg as any);

    // Agents.defaults.imageGenerationModel.primary should be set
    __testAugmentVitest_06adeb037ff4.expect(config.agents?.defaults?.imageGenerationModel?.primary).toBe(
      "google/gemini-3-pro-image-preview",
    );

    // models.providers.google.apiKey should be set to trimmed legacy env key
    __testAugmentVitest_06adeb037ff4.expect((config.models as any).providers.google.apiKey).toBe("KEY-ABC");

    // skills.entries.nano-banana-pro should be removed and changes include removal messages
    __testAugmentVitest_06adeb037ff4.expect(
      !(config.skills && (config.skills as any).entries && (config.skills as any).entries["nano-banana-pro"]),
    ).toBe(true);
    __testAugmentVitest_06adeb037ff4.expect(
      changes.some((c: string) => String(c).includes("Moved skills.entries.nano-banana-pro")),
    ).toBe(true);
    __testAugmentVitest_06adeb037ff4.expect(
      changes.some((c: string) => String(c).includes("Removed legacy skills.entries.nano-banana-pro.")),
    ).toBe(true);
  });
});

import * as __testAugmentVitest_06adeb037ff4 from "vitest";

const __testAugmentLoadTarget_a8b288d3d430 = async () => {
  __testAugmentVitest_06adeb037ff4.vi.doUnmock("./doctor-legacy-config.js");
  __testAugmentVitest_06adeb037ff4.vi.resetModules();
  return import("./doctor-legacy-config.js");
};
