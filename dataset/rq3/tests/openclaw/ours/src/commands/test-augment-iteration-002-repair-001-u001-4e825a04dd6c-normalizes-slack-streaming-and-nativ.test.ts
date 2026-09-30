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





  __testAugmentVitest_06adeb037ff4.it("normalizes slack streamMode and sets nativeStreaming with migration messages_round_002", async () => {
    // Mock the streaming helpers deterministically before loading the target
    __testAugmentVitest_06adeb037ff4.vi.doMock("../config/discord-preview-streaming.js", () => ({
      resolveSlackStreamingMode: (entry: Record<string, unknown>) => "partial",
      resolveSlackNativeStreaming: (entry: Record<string, unknown>) => true,
      formatSlackStreamModeMigrationMessage: (pathPrefix: string, mode: string) => `migrated:${pathPrefix}:${mode}`,
      formatSlackStreamingBooleanMigrationMessage: (pathPrefix: string, native: boolean) => `bool:${pathPrefix}:${String(native)}`,
    }));

    const { normalizeCompatibilityConfigValues } = await __testAugmentLoadTarget_a8b288d3d430();

    const cfg = {
      channels: {
        slack: {
          // legacy streamMode present and streaming differs (string case)
          streamMode: "legacy-mode",
          streaming: "off",
          nativeStreaming: false,
        },
      },
    } as unknown as Record<string, unknown>;

    const result = normalizeCompatibilityConfigValues(cfg as any);
    const slack = (result.config.channels as Record<string, any>).slack as Record<string, unknown> | undefined;

    // streaming should be normalized to resolved value
    __testAugmentVitest_06adeb037ff4.expect(slack).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect(slack!.streaming).toBe("partial");
    // nativeStreaming should be set according to our mocked resolver
    __testAugmentVitest_06adeb037ff4.expect(slack!.nativeStreaming).toBe(true);

    // legacy streamMode should be removed
    __testAugmentVitest_06adeb037ff4.expect(slack!.streamMode).toBeUndefined();

    // changes should include the formatted migration message and the normalized-string message
    __testAugmentVitest_06adeb037ff4.expect(result.changes.some((c) => String(c).includes("migrated:channels.slack:partial"))).toBe(true);
    __testAugmentVitest_06adeb037ff4.expect(result.changes.some((c) => String(c).includes("Normalized channels.slack.streami"))).toBe(true);
  });
});

import * as __testAugmentVitest_06adeb037ff4 from "vitest";

const __testAugmentLoadTarget_a8b288d3d430 = async () => {
  __testAugmentVitest_06adeb037ff4.vi.doUnmock("./doctor-legacy-config.js");
  __testAugmentVitest_06adeb037ff4.vi.resetModules();
  return import("./doctor-legacy-config.js");
};
