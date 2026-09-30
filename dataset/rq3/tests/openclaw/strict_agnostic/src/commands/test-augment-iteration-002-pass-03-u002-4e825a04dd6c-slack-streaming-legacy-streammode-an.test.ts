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





  __testAugmentVitest_06adeb037ff4.it("migrates-slack-legacy-streamMode-and-boolean-streaming_round_002_pass_03", async () => {
    __testAugmentVitest_06adeb037ff4.vi.doMock("../config/discord-preview-streaming.js", () => ({
      resolveDiscordPreviewStreamMode: () => "off",
      resolveTelegramPreviewStreamMode: () => "partial",
      resolveSlackStreamingMode: (entry: Record<string, unknown>) => "partial",
      resolveSlackNativeStreaming: (entry: Record<string, unknown>) => true,
      formatSlackStreamModeMigrationMessage: (p: string, r: string) => `MIGRATE:${p}:${r}`,
      formatSlackStreamingBooleanMigrationMessage: (p: string, r: boolean) => `BOOL:${p}:${r}`,
    }));

    const mod = await __testAugmentLoadTarget_a8b288d3d430();
    const { normalizeCompatibilityConfigValues } = mod;

    const cfg = {
      channels: {
        slack: {
          // legacy presence of streamMode triggers migration
          streamMode: "legacy-mode",
          // legacy streaming boolean value should be normalized
          streaming: false,
          // nativeStreaming absent so it will be set to resolved true
        },
      },
    };

    const { config, changes } = normalizeCompatibilityConfigValues(cfg as any);

    // Expect streamMode removed, streaming updated to resolvedStreaming, nativeStreaming set
    __testAugmentVitest_06adeb037ff4.expect(config.channels?.slack?.streamMode).toBeUndefined();
    __testAugmentVitest_06adeb037ff4.expect(config.channels?.slack?.streaming).toBe("partial");
    __testAugmentVitest_06adeb037ff4.expect(config.channels?.slack?.nativeStreaming).toBe(true);

    __testAugmentVitest_06adeb037ff4.expect(
      changes.some((c: string) => String(c).includes("MIGRATE:channels.slack:partial")),
    ).toBe(true);
    __testAugmentVitest_06adeb037ff4.expect(
      changes.some((c: string) => String(c).includes("BOOL:channels.slack:true")),
    ).toBe(true);
  });
});

import * as __testAugmentVitest_06adeb037ff4 from "vitest";

const __testAugmentLoadTarget_a8b288d3d430 = async () => {
  __testAugmentVitest_06adeb037ff4.vi.doUnmock("./doctor-legacy-config.js");
  __testAugmentVitest_06adeb037ff4.vi.resetModules();
  return import("./doctor-legacy-config.js");
};
