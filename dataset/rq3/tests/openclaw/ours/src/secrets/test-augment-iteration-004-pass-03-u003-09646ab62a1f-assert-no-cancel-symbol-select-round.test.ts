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

  __testAugmentVitest_02ade9ae0d48.it("assert_no_cancel_symbol_select_round_004_pass_03", async () => {
    const vi = __testAugmentVitest_02ade9ae0d48.vi;
    Object.defineProperty(process.stdin, "isTTY", { value: true, configurable: true });

    // Make select return a cancellation Symbol() on the very first select call used by configureProvidersInteractive
    const cancelSymbol = Symbol("cancel");
    vi.doMock("@clack/prompts", () => ({ select: vi.fn().mockResolvedValue(cancelSymbol), text: vi.fn(), confirm: vi.fn() }));

    // Snapshot valid so the flow reaches the first select call
    vi.doMock("./config-io.js", () => ({ createSecretsConfigIO: () => ({ readConfigFileSnapshotForWrite: async () => ({ snapshot: { valid: true, config: {}, resolved: {} } }) }) }));
    vi.doMock("./storage-scan.js", () => ({ readJsonObjectIfExists: () => ({ error: null, value: null }) }));

    const mod = await __testAugmentLoadTarget_e2f601b3199b();
    const { runSecretsConfigureInteractive } = mod;

    await __testAugmentVitest_02ade9ae0d48.expect(runSecretsConfigureInteractive({ providersOnly: true })).rejects.toThrow(
      "Secrets configure cancelled.",
    );
  });
});

import * as __testAugmentVitest_02ade9ae0d48 from "vitest";

const __testAugmentLoadTarget_e2f601b3199b = async () => {
  __testAugmentVitest_02ade9ae0d48.vi.doUnmock("./configure.js");
  __testAugmentVitest_02ade9ae0d48.vi.resetModules();
  return import("./configure.js");
};
