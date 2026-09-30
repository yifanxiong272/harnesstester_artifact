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





  __testAugmentVitest_06adeb037ff4.it("moves single-account top-level keys into default account_round_002", async () => {
    // Mock shouldMoveSingleAccountChannelKey so it returns true for a movable key 'displayName'
    __testAugmentVitest_06adeb037ff4.vi.doMock("../channels/plugins/setup-helpers.js", () => ({
      shouldMoveSingleAccountChannelKey: ({ key }: { key: string }) => key === "displayName",
    }));

    const { normalizeCompatibilityConfigValues } = await __testAugmentLoadTarget_a8b288d3d430();

    const cfg = {
      channels: {
        testchan: {
          accounts: {
            acct1: {},
          },
          // a top-level key that is allowed to be moved (not 'enabled')
          displayName: "My Bot",
          // some other top-level value that should not be moved
          other: 42,
        },
      },
    } as unknown as Record<string, unknown>;

    const result = normalizeCompatibilityConfigValues(cfg as any);
    const channel = (result.config.channels as Record<string, any>).testchan as Record<string, any> | undefined;

    __testAugmentVitest_06adeb037ff4.expect(channel).toBeTruthy();

    // default account must exist and include displayName moved from top-level
    __testAugmentVitest_06adeb037ff4.expect(channel.accounts).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect(channel.accounts.default).toBeTruthy();
    __testAugmentVitest_06adeb037ff4.expect(channel.accounts.default.displayName).toBe("My Bot");

    // original top-level displayName should be removed
    __testAugmentVitest_06adeb037ff4.expect(channel.displayName).toBeUndefined();

    // change message should indicate the move
    __testAugmentVitest_06adeb037ff4.expect(result.changes.some((c) => String(c).includes("Moved channels.testchan single-account top-level values"))).toBe(true);
  });
});

import * as __testAugmentVitest_06adeb037ff4 from "vitest";

const __testAugmentLoadTarget_a8b288d3d430 = async () => {
  __testAugmentVitest_06adeb037ff4.vi.doUnmock("./doctor-legacy-config.js");
  __testAugmentVitest_06adeb037ff4.vi.resetModules();
  return import("./doctor-legacy-config.js");
};
