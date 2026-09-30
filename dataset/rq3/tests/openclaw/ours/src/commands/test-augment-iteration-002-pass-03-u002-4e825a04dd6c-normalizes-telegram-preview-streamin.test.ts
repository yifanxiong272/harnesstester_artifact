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





  __testAugmentVitest_06adeb037ff4.it("normalizes telegram preview streaming when streaming is boolean_round_002_pass_03", async () => {
    // Mock preview streaming resolvers so resolveTelegramPreviewStreamMode returns 'partial'
    __testAugmentVitest_06adeb037ff4.vi.doMock("../config/discord-preview-streaming.js", () => ({
      resolveTelegramPreviewStreamMode: (_entry: Record<string, unknown>) => "partial",
      resolveDiscordPreviewStreamMode: (_entry: Record<string, unknown>) => "off",
      resolveSlackNativeStreaming: (_entry: Record<string, unknown>) => false,
      resolveSlackStreamingMode: (_entry: Record<string, unknown>) => "off",
      formatSlackStreamModeMigrationMessage: (_p: string, _m: string) => "",
      formatSlackStreamingBooleanMigrationMessage: (_p: string, _b: boolean) => "",
    }));

    const { normalizeCompatibilityConfigValues } = await __testAugmentLoadTarget_a8b288d3d430();

    const cfg = {
      channels: {
        telegram: {
          // streaming as boolean should be normalized to enum via resolver
          streaming: true,
        },
      },
    } as unknown as Record<string, unknown>;

    const result = normalizeCompatibilityConfigValues(cfg as any);
    const tg = (result.config.channels as Record<string, any>).telegram as Record<string, unknown> | undefined;

    __testAugmentVitest_06adeb037ff4.expect(tg).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect(tg!.streaming).toBe("partial");

    // boolean normalization should have produced a descriptive change mentioning 'boolean → enum'
    __testAugmentVitest_06adeb037ff4.expect(result.changes.some((c) => String(c).includes("Normalized channels.telegram.streami") && String(c).includes("enum"))).toBe(true);
  });
});

import * as __testAugmentVitest_06adeb037ff4 from "vitest";

const __testAugmentLoadTarget_a8b288d3d430 = async () => {
  __testAugmentVitest_06adeb037ff4.vi.doUnmock("./doctor-legacy-config.js");
  __testAugmentVitest_06adeb037ff4.vi.resetModules();
  return import("./doctor-legacy-config.js");
};
