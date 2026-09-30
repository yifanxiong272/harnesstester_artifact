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

  __testAugmentVitest_02ade9ae0d48.it("reject_providersOnly_with_skipProviderSetup_round_004", async () => {
    const vi = __testAugmentVitest_02ade9ae0d48.vi;
    // No need to fully mock prompts because function errors early after TTY check
    Object.defineProperty(process.stdin, "isTTY", { value: true, configurable: true });

    // Load fresh module (no additional mocks required)
    const mod = await __testAugmentLoadTarget_e2f601b3199b();
    const { runSecretsConfigureInteractive } = mod;

    await __testAugmentVitest_02ade9ae0d48.expect(
      runSecretsConfigureInteractive({ providersOnly: true, skipProviderSetup: true }),
    ).rejects.toThrow("Cannot combine --providers-only with --skip-provider-setup.");
  });
});

import * as __testAugmentVitest_02ade9ae0d48 from "vitest";

const __testAugmentLoadTarget_e2f601b3199b = async () => {
  __testAugmentVitest_02ade9ae0d48.vi.doUnmock("./configure.js");
  __testAugmentVitest_02ade9ae0d48.vi.resetModules();
  return import("./configure.js");
};
