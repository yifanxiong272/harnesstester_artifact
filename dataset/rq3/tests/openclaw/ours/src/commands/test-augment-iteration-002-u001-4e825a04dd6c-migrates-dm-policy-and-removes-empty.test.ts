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





  __testAugmentVitest_06adeb037ff4.it("migrate dm.policy when dm becomes empty_round_002", async () => {
    const { normalizeCompatibilityConfigValues } = await __testAugmentLoadTarget_a8b288d3d430();

    const cfg = {
      channels: {
        slack: {
          // legacy shape: dm object contains only policy
          dm: {
            policy: "private",
          },
        },
      },
    } as unknown as Record<string, unknown>;

    const result = normalizeCompatibilityConfigValues(cfg as any);

    // dm.policy should be moved to dmPolicy at channels.slack
    __testAugmentVitest_06adeb037ff4.expect(result.config.channels).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect((result.config.channels as Record<string, any>).slack).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect((result.config.channels as Record<string, any>).slack.dmPolicy).toBe("private");

    // original dm should have been removed because it became empty after migration
    __testAugmentVitest_06adeb037ff4.expect((result.config.channels as Record<string, any>).slack.dm).toBeUndefined();

    // changes must include the migration message
    __testAugmentVitest_06adeb037ff4.expect(result.changes.some((c) => String(c).includes("Moved channels.slack.dm.policy"))).toBe(true);
  });
});

import * as __testAugmentVitest_06adeb037ff4 from "vitest";

const __testAugmentLoadTarget_a8b288d3d430 = async () => {
  __testAugmentVitest_06adeb037ff4.vi.doUnmock("./doctor-legacy-config.js");
  __testAugmentVitest_06adeb037ff4.vi.resetModules();
  return import("./doctor-legacy-config.js");
};
