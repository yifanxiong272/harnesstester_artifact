import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";

const selectMock = vi.hoisted(() => vi.fn());
const createSecretsConfigIOMock = vi.hoisted(() => vi.fn());
const readJsonObjectIfExistsMock = vi.hoisted(() => vi.fn());

const mockedModuleIds = ["@clack/prompts", "./config-io.js", "./storage-scan.js"] as const;

vi.mock("@clack/prompts", () => ({
  confirm: vi.fn(),
  select: (...args: unknown[]) => selectMock(...args),
  text: vi.fn(),
}));

vi.mock("./config-io.js", () => ({
  createSecretsConfigIO: (...args: unknown[]) => createSecretsConfigIOMock(...args),
}));

vi.mock("./storage-scan.js", () => ({
  readJsonObjectIfExists: (...args: unknown[]) => readJsonObjectIfExistsMock(...args),
}));

const { runSecretsConfigureInteractive } = await import("./configure.js");

describe("runSecretsConfigureInteractive", () => {
  beforeEach(() => {
    selectMock.mockReset();
    createSecretsConfigIOMock.mockReset();
    readJsonObjectIfExistsMock.mockReset();
  });

  afterAll(() => {
    for (const id of mockedModuleIds) {
      vi.doUnmock(id);
    }
    vi.resetModules();
  });

  __testAugmentVitest_02ade9ae0d48.it("no_configurable_candidates_error_round_004_pass_02", async () => {
    const vi = __testAugmentVitest_02ade9ae0d48.vi;
    Object.defineProperty(process.stdin, "isTTY", { value: true, configurable: true });

    // Valid snapshot so flow continues
    vi.doMock("./config-io.js", () => ({
      createSecretsConfigIO: () => ({
        readConfigFileSnapshotForWrite: async () => ({
          snapshot: { valid: true, config: {}, resolved: {} },
        }),
      }),
    }));

    // Auth store read ok (no error)
    vi.doMock("./storage-scan.js", () => ({ readJsonObjectIfExists: () => ({ error: null, value: null }) }));

    // Agent helpers
    vi.doMock("../agents/agent-scope.js", () => ({
      listAgentIds: () => ["agent1"],
      resolveAgentDir: () => "/tmp/agent1",
      resolveDefaultAgentId: () => "agent1",
    }));

    // Mock configure-plan to return no candidates, triggering the specific error
    vi.doMock("./configure-plan.js", () => ({
      buildConfigureCandidatesForScope: () => [],
      buildSecretsConfigurePlan: () => ({}),
      collectConfigureProviderChanges: () => ({ original: {}, next: {} }),
      hasConfigurePlanChanges: () => false,
    }));

    // Minimal prompts mock
    vi.doMock("@clack/prompts", () => ({ select: vi.fn(), text: vi.fn(), confirm: vi.fn() }));

    const mod = await __testAugmentLoadTarget_e2f601b3199b();
    const { runSecretsConfigureInteractive } = mod;

    await __testAugmentVitest_02ade9ae0d48.expect(
      runSecretsConfigureInteractive({ skipProviderSetup: true }),
    ).rejects.toThrow("No configurable secret-bearing fields found for this agent scope.");
  });
});

import * as __testAugmentVitest_02ade9ae0d48 from "vitest";

const __testAugmentLoadTarget_e2f601b3199b = async () => {
  __testAugmentVitest_02ade9ae0d48.vi.doUnmock("./configure.js");
  __testAugmentVitest_02ade9ae0d48.vi.resetModules();
  return import("./configure.js");
};
