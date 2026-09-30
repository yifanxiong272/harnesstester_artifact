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





  __testAugmentVitest_06adeb037ff4.it("normalizes browser.ssrfPolicy.allowPrivateNetwork -> dangerouslyAllowPrivateNetwork_round_002_pass_03", async () => {
    const { normalizeCompatibilityConfigValues } = await __testAugmentLoadTarget_a8b288d3d430();

    const cfg = {
      browser: {
        ssrfPolicy: {
          // legacy boolean
          allowPrivateNetwork: true,
        },
      },
    } as unknown as Record<string, unknown>;

    const result = normalizeCompatibilityConfigValues(cfg as any);
    const browser = (result.config as any).browser as Record<string, unknown> | undefined;

    __testAugmentVitest_06adeb037ff4.expect(browser).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect(browser.ssrfPolicy).toBeTruthy();
    // migrated key must be present and be true
    __testAugmentVitest_06adeb037ff4.expect((browser.ssrfPolicy as any).dangerouslyAllowPrivateNetwork).toBe(true);

    // change message must mention the moved key and the resolved value
    __testAugmentVitest_06adeb037ff4.expect(result.changes.some((c) => String(c).includes("Moved browser.ssrfPolicy.allowPrivateNetwork"))).toBe(true);
  });
});

import * as __testAugmentVitest_06adeb037ff4 from "vitest";

const __testAugmentLoadTarget_a8b288d3d430 = async () => {
  __testAugmentVitest_06adeb037ff4.vi.doUnmock("./doctor-legacy-config.js");
  __testAugmentVitest_06adeb037ff4.vi.resetModules();
  return import("./doctor-legacy-config.js");
};
