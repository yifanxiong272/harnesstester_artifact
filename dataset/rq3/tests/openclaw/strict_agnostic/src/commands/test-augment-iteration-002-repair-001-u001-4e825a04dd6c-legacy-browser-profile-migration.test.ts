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





  __testAugmentVitest_06adeb037ff4.it("migrates-browser-extension-driver_and_removes_relayBindHost_round_002", async () => {
    // Load the target module using the provided loader (no external mocks required)
    const mod = await __testAugmentLoadTarget_a8b288d3d430();
    const { normalizeCompatibilityConfigValues } = mod;

    const inputCfg = {
      browser: {
        relayBindHost: "127.0.0.1",
        profiles: {
          // profile with legacy 'extension' driver should be migrated
          chromeExt: { driver: "extension", someOther: 1 },
          // profile with non-extension driver should be left unchanged
          normal: { driver: "manual" },
        },
      },
    };

    const { config, changes } = normalizeCompatibilityConfigValues(inputCfg as any);

    // The migrated config should no longer have relayBindHost
    __testAugmentVitest_06adeb037ff4.expect(config.browser).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect((config.browser as any).relayBindHost).toBeUndefined();

    // The chromeExt profile driver should be changed to 'existing-session'
    __testAugmentVitest_06adeb037ff4.expect((config.browser as any).profiles).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect(((config.browser as any).profiles.chromeExt as any).driver).toBe(
      "existing-session",
    );

    // The normal profile should remain untouched
    __testAugmentVitest_06adeb037ff4.expect(((config.browser as any).profiles.normal as any).driver).toBe(
      "manual",
    );

    // Changes should include the explanatory message for the driver migration
    __testAugmentVitest_06adeb037ff4.expect(
      changes.some((c: string) =>
        String(c).includes("Moved browser.profiles.chromeExt.driver \"extension\" → \"existing-session\" (Chrome MCP attach)."),
      ),
    ).toBe(true);
  });
});

import * as __testAugmentVitest_06adeb037ff4 from "vitest";

const __testAugmentLoadTarget_a8b288d3d430 = async () => {
  __testAugmentVitest_06adeb037ff4.vi.doUnmock("./doctor-legacy-config.js");
  __testAugmentVitest_06adeb037ff4.vi.resetModules();
  return import("./doctor-legacy-config.js");
};
