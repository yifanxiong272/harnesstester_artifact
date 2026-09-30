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





  __testAugmentVitest_06adeb037ff4.it("removes dm.allowFrom when top-level allowFrom equals legacy dm.allowFrom_round_002_pass_02", async () => {
    const { normalizeCompatibilityConfigValues } = await __testAugmentLoadTarget_a8b288d3d430();

    const cfg = {
      channels: {
        slack: {
          // top-level allowFrom already set
          allowFrom: ["alice", "bob"],
          // legacy dm.allowFrom with whitespace differences that should be considered equal
          dm: { allowFrom: [" alice ", "bob"] },
        },
      },
    } as unknown as Record<string, unknown>;

    const result = normalizeCompatibilityConfigValues(cfg as any);
    const slack = (result.config.channels as Record<string, any>).slack as Record<string, unknown> | undefined;

    __testAugmentVitest_06adeb037ff4.expect(slack).toBeTruthy();
    // top-level allowFrom must be preserved and equal to original
    __testAugmentVitest_06adeb037ff4.expect(Array.isArray(slack!.allowFrom)).toBe(true);
    __testAugmentVitest_06adeb037ff4.expect(String((slack!.allowFrom as any[]).join(","))).toBe("alice,bob");

    // legacy dm.allowFrom should have been removed from dm (dm may be removed or dm without that key)
    const dm = slack!.dm as Record<string, unknown> | undefined;
    if (dm) {
      __testAugmentVitest_06adeb037ff4.expect(dm.allowFrom).toBeUndefined();
    }

    // changes should include the removal message for dm.allowFrom
    __testAugmentVitest_06adeb037ff4.expect(result.changes.some((c) => String(c).includes("Removed channels.slack.dm.allowFrom"))).toBe(true);
  });
});

import * as __testAugmentVitest_06adeb037ff4 from "vitest";

const __testAugmentLoadTarget_a8b288d3d430 = async () => {
  __testAugmentVitest_06adeb037ff4.vi.doUnmock("./doctor-legacy-config.js");
  __testAugmentVitest_06adeb037ff4.vi.resetModules();
  return import("./doctor-legacy-config.js");
};
