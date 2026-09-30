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





  __testAugmentVitest_06adeb037ff4.it("merges legacy deepgram compat into existing providerOptions.deepgram (merged branch)_round_002_pass_03", async () => {
    const { normalizeCompatibilityConfigValues } = await __testAugmentLoadTarget_a8b288d3d430();

    const cfg = {
      tools: {
        media: {
          audio: {
            // canonical providerOptions.deepgram already has punctuate:true
            providerOptions: { deepgram: { punctuate: true } },
            // legacy compat supplies detectLanguage that should be merged
            deepgram: { detectLanguage: true },
          },
        },
      },
    } as unknown as Record<string, unknown>;

    const result = normalizeCompatibilityConfigValues(cfg as any);
    const media = (result.config.tools as any).media as Record<string, unknown> | undefined;

    __testAugmentVitest_06adeb037ff4.expect(media).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect(media.audio).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect(media.audio.providerOptions).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect(media.audio.providerOptions.deepgram.detect_language).toBe(true);
    __testAugmentVitest_06adeb037ff4.expect(media.audio.providerOptions.deepgram.punctuate).toBe(true);

    // change message must indicate a merge (filled missing canonical fields from legacy)
    __testAugmentVitest_06adeb037ff4.expect(result.changes.some((c) => String(c).includes("Merged tools.media.audio.deepgram" ) || String(c).includes("Merged tools.media"))).toBe(true);
  });
});

import * as __testAugmentVitest_06adeb037ff4 from "vitest";

const __testAugmentLoadTarget_a8b288d3d430 = async () => {
  __testAugmentVitest_06adeb037ff4.vi.doUnmock("./doctor-legacy-config.js");
  __testAugmentVitest_06adeb037ff4.vi.resetModules();
  return import("./doctor-legacy-config.js");
};
