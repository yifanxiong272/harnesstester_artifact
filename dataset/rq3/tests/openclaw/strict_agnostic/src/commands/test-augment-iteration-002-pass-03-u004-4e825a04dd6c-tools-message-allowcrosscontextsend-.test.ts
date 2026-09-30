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





  __testAugmentVitest_06adeb037ff4.it("removes-tools-message-allowCrossContextSend_false_round_002_pass_03", async () => {
    const mod = await __testAugmentLoadTarget_a8b288d3d430();
    const { normalizeCompatibilityConfigValues } = mod;

    const cfg = {
      tools: {
        message: {
          allowCrossContextSend: false,
        },
      },
    };

    const { config, changes } = normalizeCompatibilityConfigValues(cfg as any);

    // The legacy flag should be removed and a removal message added
    __testAugmentVitest_06adeb037ff4.expect((config.tools as any).message.allowCrossContextSend).toBeUndefined();
    __testAugmentVitest_06adeb037ff4.expect(
      changes.some((c: string) => String(c).includes("Removed tools.message.allowCrossContextSend=false (default cross-context policy already matches canonical settings).")),
    ).toBe(true);
  });
});

import * as __testAugmentVitest_06adeb037ff4 from "vitest";

const __testAugmentLoadTarget_a8b288d3d430 = async () => {
  __testAugmentVitest_06adeb037ff4.vi.doUnmock("./doctor-legacy-config.js");
  __testAugmentVitest_06adeb037ff4.vi.resetModules();
  return import("./doctor-legacy-config.js");
};
