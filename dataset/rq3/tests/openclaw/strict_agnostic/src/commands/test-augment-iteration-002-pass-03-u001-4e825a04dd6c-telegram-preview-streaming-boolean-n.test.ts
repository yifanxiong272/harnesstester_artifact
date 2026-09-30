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





  __testAugmentVitest_06adeb037ff4.it("normalizes-telegram-preview-streaming-boolean-to-enum_round_002_pass_03", async () => {
    // Mock streaming resolvers so normalization is deterministic
    __testAugmentVitest_06adeb037ff4.vi.doMock("../config/discord-preview-streaming.js", () => ({
      resolveDiscordPreviewStreamMode: () => "off",
      resolveTelegramPreviewStreamMode: () => "partial",
      resolveSlackStreamingMode: () => "partial",
      resolveSlackNativeStreaming: () => false,
      formatSlackStreamModeMigrationMessage: () => "",
      formatSlackStreamingBooleanMigrationMessage: () => "",
    }));

    const mod = await __testAugmentLoadTarget_a8b288d3d430();
    const { normalizeCompatibilityConfigValues } = mod;

    const cfg = {
      channels: {
        telegram: {
          // boolean streaming should be normalized to enum returned by resolver
          streaming: true,
        },
      },
    };

    const { config, changes } = normalizeCompatibilityConfigValues(cfg as any);

    __testAugmentVitest_06adeb037ff4.expect(config.channels?.telegram?.streaming).toBe("partial");
    __testAugmentVitest_06adeb037ff4.expect(
      changes.some((c: string) => String(c).includes("Normalized channels.telegram.streaming boolean → enum (partial).")),
    ).toBe(true);
  });
});

import * as __testAugmentVitest_06adeb037ff4 from "vitest";

const __testAugmentLoadTarget_a8b288d3d430 = async () => {
  __testAugmentVitest_06adeb037ff4.vi.doUnmock("./doctor-legacy-config.js");
  __testAugmentVitest_06adeb037ff4.vi.resetModules();
  return import("./doctor-legacy-config.js");
};
