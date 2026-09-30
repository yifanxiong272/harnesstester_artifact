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

  __testAugmentVitest_02ade9ae0d48.it("add_file_provider_then_continue_round_004", async () => {
    const vi = __testAugmentVitest_02ade9ae0d48.vi;
    // Mock interactive prompts: action -> add, provider source -> file, file mode -> singleValue, then outer action -> continue
    vi.doMock("@clack/prompts", () => ({
      select: vi.fn()
        .mockResolvedValueOnce("add")
        .mockResolvedValueOnce("file")
        .mockResolvedValueOnce("singleValue")
        .mockResolvedValueOnce("continue"),
      text: vi.fn()
        // provider alias
        .mockResolvedValueOnce("myfile")
        // file path
        .mockResolvedValueOnce("/tmp/config.json")
        // timeoutMs (blank)
        .mockResolvedValueOnce("")
        // maxBytes (blank)
        .mockResolvedValueOnce("") ,
      confirm: vi.fn().mockResolvedValue(true),
    }));

    // Provide a minimal config IO snapshot (valid) so provider setup runs
    vi.doMock("./config-io.js", () => ({
      createSecretsConfigIO: () => ({
        readConfigFileSnapshotForWrite: async () => ({
          snapshot: {
            valid: true,
            config: {},
            resolved: {},
          },
        }),
      }),
    }));

    // Ensure storage-scan doesn't interfere
    vi.doMock("./storage-scan.js", () => ({ readJsonObjectIfExists: () => ({ error: null, value: null }) }));

    // Mock runSecretsApply so final preflight is controlled and observable
    const runApplyMock = vi.fn().mockResolvedValue({ mocked: true });
    vi.doMock("./apply.js", () => ({ runSecretsApply: runApplyMock }));

    // Ensure interactive check passes
    Object.defineProperty(process.stdin, "isTTY", { value: true, configurable: true });

    const mod = await __testAugmentLoadTarget_e2f601b3199b();
    const { runSecretsConfigureInteractive } = mod;

    const result = await runSecretsConfigureInteractive({ providersOnly: true });

    // Expect runSecretsApply to be invoked with the generated plan (write: false)
    __testAugmentVitest_02ade9ae0d48.expect(runApplyMock).toHaveBeenCalled();
    __testAugmentVitest_02ade9ae0d48.expect(result.preflight).toEqual({ mocked: true });
  });
});

import * as __testAugmentVitest_02ade9ae0d48 from "vitest";

const __testAugmentLoadTarget_e2f601b3199b = async () => {
  __testAugmentVitest_02ade9ae0d48.vi.doUnmock("./configure.js");
  __testAugmentVitest_02ade9ae0d48.vi.resetModules();
  return import("./configure.js");
};
