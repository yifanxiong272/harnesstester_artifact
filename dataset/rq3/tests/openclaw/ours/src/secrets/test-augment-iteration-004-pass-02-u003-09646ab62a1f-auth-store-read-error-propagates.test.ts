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

  __testAugmentVitest_02ade9ae0d48.it("auth_store_read_error_propagates_round_004_pass_02", async () => {
    const vi = __testAugmentVitest_02ade9ae0d48.vi;
    Object.defineProperty(process.stdin, "isTTY", { value: true, configurable: true });

    // Provide a valid snapshot so flow continues into auth store loading
    vi.doMock("./config-io.js", () => ({
      createSecretsConfigIO: () => ({
        readConfigFileSnapshotForWrite: async () => ({
          snapshot: { valid: true, config: {}, resolved: {} },
        }),
      }),
    }));

    // Make reading the auth store fail (simulate unreadable file)
    vi.doMock("./storage-scan.js", () => ({ readJsonObjectIfExists: () => ({ error: "boom", value: null }) }));

    // Ensure agent resolution functions behave (so resolveConfigureAgentId and loadAuthProfileStoreForConfigure run)
    vi.doMock("../agents/agent-scope.js", () => ({
      listAgentIds: () => ["agent1"],
      resolveAgentDir: () => "/tmp/agent1",
      resolveDefaultAgentId: () => "agent1",
    }));

    // Minimal prompts mock (not needed because skipProviderSetup avoids interactive provider setup)
    vi.doMock("@clack/prompts", () => ({ select: vi.fn(), text: vi.fn(), confirm: vi.fn() }));

    const mod = await __testAugmentLoadTarget_e2f601b3199b();
    const { runSecretsConfigureInteractive } = mod;

    // Skip provider setup to reach auth-store loading quickly
    await __testAugmentVitest_02ade9ae0d48.expect(
      runSecretsConfigureInteractive({ skipProviderSetup: true }),
    ).rejects.toThrow(/could not be read/);
  });
});

import * as __testAugmentVitest_02ade9ae0d48 from "vitest";

const __testAugmentLoadTarget_e2f601b3199b = async () => {
  __testAugmentVitest_02ade9ae0d48.vi.doUnmock("./configure.js");
  __testAugmentVitest_02ade9ae0d48.vi.resetModules();
  return import("./configure.js");
};
