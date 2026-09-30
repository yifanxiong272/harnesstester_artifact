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





  __testAugmentVitest_06adeb037ff4.it("moves dm.allowFrom into top-level allowFrom when top-level missing_round_002_pass_03", async () => {
    const { normalizeCompatibilityConfigValues } = await __testAugmentLoadTarget_a8b288d3d430();

    const cfg = {
      channels: {
        discord: {
          // no top-level allowFrom, legacy dm.allowFrom present
          dm: { allowFrom: ["carol", "dave"] },
        },
      },
    } as unknown as Record<string, unknown>;

    const result = normalizeCompatibilityConfigValues(cfg as any);
    const discord = (result.config.channels as Record<string, any>).discord as Record<string, unknown> | undefined;

    __testAugmentVitest_06adeb037ff4.expect(discord).toBeTruthy();
    // top-level allowFrom should now be set
    __testAugmentVitest_06adeb037ff4.expect(Array.isArray(discord!.allowFrom)).toBe(true);
    __testAugmentVitest_06adeb037ff4.expect(String((discord!.allowFrom as any[]).join(","))).toBe("carol,dave");

    // dm.allowFrom should have been removed (either removed key or dm removed if empty)
    const dm = discord!.dm as Record<string, unknown> | undefined;
    if (dm) {
      __testAugmentVitest_06adeb037ff4.expect(dm.allowFrom).toBeUndefined();
    }

    __testAugmentVitest_06adeb037ff4.expect(result.changes.some((c) => String(c).includes("Moved channels.discord.dm.allowFrom → channels.discord.allowFrom."))).toBe(true);
  });
});

import * as __testAugmentVitest_06adeb037ff4 from "vitest";

const __testAugmentLoadTarget_a8b288d3d430 = async () => {
  __testAugmentVitest_06adeb037ff4.vi.doUnmock("./doctor-legacy-config.js");
  __testAugmentVitest_06adeb037ff4.vi.resetModules();
  return import("./doctor-legacy-config.js");
};
