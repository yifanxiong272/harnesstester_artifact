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





  __testAugmentVitest_06adeb037ff4.it("converts-ssrf-allowPrivateNetwork-to-dangerouslyAllowPrivateNetwork_round_002_pass_02", async () => {
    const mod = await __testAugmentLoadTarget_a8b288d3d430();
    const { normalizeCompatibilityConfigValues } = mod;

    const cfg = {
      browser: {
        ssrfPolicy: {
          allowPrivateNetwork: true,
        },
      },
    };

    const { config, changes } = normalizeCompatibilityConfigValues(cfg as any);

    __testAugmentVitest_06adeb037ff4.expect((config.browser as any).ssrfPolicy).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect(((config.browser as any).ssrfPolicy as any).allowPrivateNetwork).toBeUndefined();
    __testAugmentVitest_06adeb037ff4.expect(((config.browser as any).ssrfPolicy as any).dangerouslyAllowPrivateNetwork).toBe(true);
    __testAugmentVitest_06adeb037ff4.expect(
      changes.some((c: string) => String(c).includes("Moved browser.ssrfPolicy.allowPrivateNetwork → browser.ssrfPolicy.dangerouslyAllowPrivateNetwork (true).")),
    ).toBe(true);
  });
});

import * as __testAugmentVitest_06adeb037ff4 from "vitest";

const __testAugmentLoadTarget_a8b288d3d430 = async () => {
  __testAugmentVitest_06adeb037ff4.vi.doUnmock("./doctor-legacy-config.js");
  __testAugmentVitest_06adeb037ff4.vi.resetModules();
  return import("./doctor-legacy-config.js");
};
