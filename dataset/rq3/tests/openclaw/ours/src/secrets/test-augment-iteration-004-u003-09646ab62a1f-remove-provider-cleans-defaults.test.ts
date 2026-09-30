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

  __testAugmentVitest_02ade9ae0d48.it("remove_provider_cleans_defaults_round_004", async () => {
    const vi = __testAugmentVitest_02ade9ae0d48.vi;
    // Simulate initial config with a provider 'a' and defaults referencing it
    const initialConfig = {
      secrets: {
        providers: {
          a: { source: "env", allowlist: ["FOO"] },
        },
        defaults: { env: "a", file: "a", exec: "a" },
      },
    };

    // select: remove, then pick provider 'a', then continue
    vi.doMock("@clack/prompts", () => ({
      select: vi.fn().mockResolvedValueOnce("remove").mockResolvedValueOnce("a").mockResolvedValueOnce("continue"),
      confirm: vi.fn().mockResolvedValueOnce(true),
      text: vi.fn(),
    }));

    vi.doMock("./config-io.js", () => ({
      createSecretsConfigIO: () => ({
        readConfigFileSnapshotForWrite: async () => ({ snapshot: { valid: true, config: initialConfig, resolved: {} } }),
      }),
    }));

    vi.doMock("./storage-scan.js", () => ({ readJsonObjectIfExists: () => ({ error: null, value: null }) }));

    const runApplyMock = vi.fn().mockResolvedValue({ removed: true });
    vi.doMock("./apply.js", () => ({ runSecretsApply: runApplyMock }));

    Object.defineProperty(process.stdin, "isTTY", { value: true, configurable: true });

    const mod = await __testAugmentLoadTarget_e2f601b3199b();
    const { runSecretsConfigureInteractive } = mod;

    const result = await runSecretsConfigureInteractive({ providersOnly: true });

    // Removing a provider should produce providerChanges and thus call the apply mock
    __testAugmentVitest_02ade9ae0d48.expect(runApplyMock).toHaveBeenCalled();
    __testAugmentVitest_02ade9ae0d48.expect(result.preflight).toEqual({ removed: true });
  });
});

import * as __testAugmentVitest_02ade9ae0d48 from "vitest";

const __testAugmentLoadTarget_e2f601b3199b = async () => {
  __testAugmentVitest_02ade9ae0d48.vi.doUnmock("./configure.js");
  __testAugmentVitest_02ade9ae0d48.vi.resetModules();
  return import("./configure.js");
};
