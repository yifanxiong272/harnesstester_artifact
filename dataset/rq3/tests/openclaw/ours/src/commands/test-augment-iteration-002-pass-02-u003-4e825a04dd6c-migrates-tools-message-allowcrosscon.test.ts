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





  __testAugmentVitest_06adeb037ff4.it("migrates tools.message.allowCrossContextSend=true into crossContext policy_round_002_pass_02", async () => {
    const { normalizeCompatibilityConfigValues } = await __testAugmentLoadTarget_a8b288d3d430();

    const cfg = {
      tools: {
        message: {
          allowCrossContextSend: true,
        },
      },
    } as unknown as Record<string, unknown>;

    const result = normalizeCompatibilityConfigValues(cfg as any);

    const tools = (result.config as any).tools as Record<string, any> | undefined;
    __testAugmentVitest_06adeb037ff4.expect(tools).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect(tools.message).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect(tools.message.allowCrossContextSend).toBeUndefined();

    const cross = tools.message.crossContext as Record<string, unknown> | undefined;
    __testAugmentVitest_06adeb037ff4.expect(cross).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect(cross.allowWithinProvider).toBe(true);
    __testAugmentVitest_06adeb037ff4.expect(cross.allowAcrossProviders).toBe(true);

    __testAugmentVitest_06adeb037ff4.expect(result.changes.some((c) => String(c).includes("Moved tools.message.allowCrossContextSend"))).toBe(true);
  });
});

import * as __testAugmentVitest_06adeb037ff4 from "vitest";

const __testAugmentLoadTarget_a8b288d3d430 = async () => {
  __testAugmentVitest_06adeb037ff4.vi.doUnmock("./doctor-legacy-config.js");
  __testAugmentVitest_06adeb037ff4.vi.resetModules();
  return import("./doctor-legacy-config.js");
};
