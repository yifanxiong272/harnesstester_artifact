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

  __testAugmentVitest_02ade9ae0d48.it("add_env_provider_with_allowlist_round_004", async () => {
    const vi = __testAugmentVitest_02ade9ae0d48.vi;
    // select: add -> env -> continue
    vi.doMock("@clack/prompts", () => ({
      select: vi.fn().mockResolvedValueOnce("add").mockResolvedValueOnce("env").mockResolvedValueOnce("continue"),
      text: vi.fn()
        // provider alias
        .mockResolvedValueOnce("env1")
        // allowlist csv for env provider
        .mockResolvedValueOnce("FOO, BAR") ,
      confirm: vi.fn().mockResolvedValue(true),
    }));

    vi.doMock("./config-io.js", () => ({
      createSecretsConfigIO: () => ({
        readConfigFileSnapshotForWrite: async () => ({ snapshot: { valid: true, config: {}, resolved: {} } }),
      }),
    }));

    vi.doMock("./storage-scan.js", () => ({ readJsonObjectIfExists: () => ({ error: null, value: null }) }));

    const runApplyMock = vi.fn().mockResolvedValue({ envApplied: true });
    vi.doMock("./apply.js", () => ({ runSecretsApply: runApplyMock }));

    Object.defineProperty(process.stdin, "isTTY", { value: true, configurable: true });

    const mod = await __testAugmentLoadTarget_e2f601b3199b();
    const { runSecretsConfigureInteractive } = mod;

    const result = await runSecretsConfigureInteractive({ providersOnly: true });

    __testAugmentVitest_02ade9ae0d48.expect(runApplyMock).toHaveBeenCalled();
    __testAugmentVitest_02ade9ae0d48.expect(result.preflight).toEqual({ envApplied: true });
  });
});

import * as __testAugmentVitest_02ade9ae0d48 from "vitest";

const __testAugmentLoadTarget_e2f601b3199b = async () => {
  __testAugmentVitest_02ade9ae0d48.vi.doUnmock("./configure.js");
  __testAugmentVitest_02ade9ae0d48.vi.resetModules();
  return import("./configure.js");
};
