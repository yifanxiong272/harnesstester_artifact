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





  __testAugmentVitest_06adeb037ff4.it("migrates legacy browser profiles and removes relayBindHost_round_002_pass_02", async () => {
    const { normalizeCompatibilityConfigValues } = await __testAugmentLoadTarget_a8b288d3d430();

    const cfg = {
      browser: {
        relayBindHost: "127.0.0.1",
        profiles: {
          chromiumExt: { driver: "extension" },
          other: { driver: "manual" },
        },
      },
    } as unknown as Record<string, unknown>;

    const result = normalizeCompatibilityConfigValues(cfg as any);
    const browser = (result.config as any).browser as Record<string, any> | undefined;

    __testAugmentVitest_06adeb037ff4.expect(browser).toBeTruthy();
    // relayBindHost should be removed
    __testAugmentVitest_06adeb037ff4.expect(browser.relayBindHost).toBeUndefined();

    // profile with driver 'extension' should be migrated to 'existing-session'
    __testAugmentVitest_06adeb037ff4.expect(browser.profiles).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect(browser.profiles.chromiumExt).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect(browser.profiles.chromiumExt.driver).toBe("existing-session");

    // changes should include both removed relayBindHost and moved driver message
    __testAugmentVitest_06adeb037ff4.expect(result.changes.some((c) => String(c).includes("Removed browser.relayBindHost"))).toBe(true);
    __testAugmentVitest_06adeb037ff4.expect(result.changes.some((c) => String(c).includes("Moved browser.profiles.chromiumExt.driver \"extension\" → \"existing-session\""))).toBe(true);
  });
});

import * as __testAugmentVitest_06adeb037ff4 from "vitest";

const __testAugmentLoadTarget_a8b288d3d430 = async () => {
  __testAugmentVitest_06adeb037ff4.vi.doUnmock("./doctor-legacy-config.js");
  __testAugmentVitest_06adeb037ff4.vi.resetModules();
  return import("./doctor-legacy-config.js");
};
