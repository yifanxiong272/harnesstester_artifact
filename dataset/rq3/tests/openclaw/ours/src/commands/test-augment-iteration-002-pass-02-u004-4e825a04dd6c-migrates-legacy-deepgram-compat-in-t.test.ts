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





  __testAugmentVitest_06adeb037ff4.it("migrates legacy deepgram compat into providerOptions for tools.media (capability + models)_round_002_pass_02", async () => {
    const { normalizeCompatibilityConfigValues } = await __testAugmentLoadTarget_a8b288d3d430();

    const cfg = {
      tools: {
        media: {
          audio: {
            deepgram: { detectLanguage: true, punctuate: false },
            models: [
              {
                deepgram: { smartFormat: true },
              },
            ],
          },
          models: [
            {
              deepgram: { punctuate: true },
            },
          ],
        },
      },
    } as unknown as Record<string, unknown>;

    const result = normalizeCompatibilityConfigValues(cfg as any);
    const media = (result.config.tools as any).media as Record<string, any> | undefined;

    __testAugmentVitest_06adeb037ff4.expect(media).toBeTruthy();

    // capability-level audio should have providerOptions.deepgram with mapped keys
    __testAugmentVitest_06adeb037ff4.expect(media.audio.providerOptions).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect(media.audio.providerOptions.deepgram).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect(media.audio.providerOptions.deepgram.detect_language).toBe(true);
    // migrateModelList should have converted model entry deepgram -> providerOptions.deepgram.smart_format
    __testAugmentVitest_06adeb037ff4.expect(Array.isArray(media.audio.models)).toBe(true);
    __testAugmentVitest_06adeb037ff4.expect(media.audio.models[0].providerOptions).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect(media.audio.models[0].providerOptions.deepgram.smart_format).toBe(true);

    // top-level tools.media.models entries should also be migrated into providerOptions.deepgram
    __testAugmentVitest_06adeb037ff4.expect(Array.isArray(media.models)).toBe(true);
    __testAugmentVitest_06adeb037ff4.expect(media.models[0].providerOptions).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect(media.models[0].providerOptions.deepgram.punctuate).toBe(true);

    __testAugmentVitest_06adeb037ff4.expect(result.changes.some((c) => String(c).includes("Moved tools.media.audio.deepgram" ) || String(c).includes("Moved tools.media.models"))).toBe(true);
  });
});

import * as __testAugmentVitest_06adeb037ff4 from "vitest";

const __testAugmentLoadTarget_a8b288d3d430 = async () => {
  __testAugmentVitest_06adeb037ff4.vi.doUnmock("./doctor-legacy-config.js");
  __testAugmentVitest_06adeb037ff4.vi.resetModules();
  return import("./doctor-legacy-config.js");
};
