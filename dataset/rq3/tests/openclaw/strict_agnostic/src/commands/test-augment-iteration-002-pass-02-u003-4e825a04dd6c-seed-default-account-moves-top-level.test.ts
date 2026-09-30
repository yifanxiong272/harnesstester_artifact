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





  __testAugmentVitest_06adeb037ff4.it("moves-single-account-top-level-keys_into_default_account_round_002_pass_02", async () => {
    // Mock the helper that decides which keys to move so behavior is deterministic
    __testAugmentVitest_06adeb037ff4.vi.doMock("../channels/plugins/setup-helpers.js", () => ({
      shouldMoveSingleAccountChannelKey: () => true,
    }));

    const mod = await __testAugmentLoadTarget_a8b288d3d430();
    const { normalizeCompatibilityConfigValues } = mod;

    const cfg = {
      channels: {
        sample: {
          accounts: {
            primary: { id: "x" },
          },
          // top-level keys that should be moved into default account per mocked helper
          token: "tkn",
          enabled: undefined, // should not be considered for moving
        },
      },
    };

    const { config, changes } = normalizeCompatibilityConfigValues(cfg as any);

    // Expect the token to be moved into accounts.default
    __testAugmentVitest_06adeb037ff4.expect(((config.channels as any).sample as any).accounts.default.token).toBe(
      "tkn",
    );
    // The top-level token should be removed from the channel
    __testAugmentVitest_06adeb037ff4.expect(((config.channels as any).sample as any).token).toBeUndefined();
    __testAugmentVitest_06adeb037ff4.expect(
      changes.some((c: string) => String(c).includes("Moved channels.sample single-account top-level values into channels.sample.accounts.default.")),
    ).toBe(true);
  });
});

import * as __testAugmentVitest_06adeb037ff4 from "vitest";

const __testAugmentLoadTarget_a8b288d3d430 = async () => {
  __testAugmentVitest_06adeb037ff4.vi.doUnmock("./doctor-legacy-config.js");
  __testAugmentVitest_06adeb037ff4.vi.resetModules();
  return import("./doctor-legacy-config.js");
};
