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

  __testAugmentVitest_02ade9ae0d48.it("exec_args_parse_error_round_004_pass_03", async () => {
    const vi = __testAugmentVitest_02ade9ae0d48.vi;
    // Simulate interactive TTY
    Object.defineProperty(process.stdin, "isTTY", { value: true, configurable: true });

    // Mock prompts to drive: action(add) -> provider source(exec) -> then the exec provider flow
    // select sequence: action(add), promptProviderSource(exec), outer loop -> continue
    const selectMock = vi.fn()
      .mockResolvedValueOnce("add")
      .mockResolvedValueOnce("exec")
      .mockResolvedValueOnce("continue");

    // text() calls in promptExecProvider and related helpers; provide values in order:
    // provider alias, command, argsRaw (invalid JSON), timeoutMs (blank), no-output timeout (blank),
    // maxOutputBytes (blank), passEnv csv (blank), trustedDirs (blank)
    const textMock = vi.fn()
      .mockResolvedValueOnce("execalias") // provider alias
      .mockResolvedValueOnce("/usr/bin/somecmd") // command
      .mockResolvedValueOnce("{invalid-json}") // argsRaw -> will cause JSON.parse to throw in parseArgsInput
      .mockResolvedValueOnce("") // timeoutMs (promptOptionalPositiveInt)
      .mockResolvedValueOnce("") // no-output timeout
      .mockResolvedValueOnce("") // maxOutputBytes
      .mockResolvedValueOnce("") // passEnv
      .mockResolvedValueOnce(""); // trustedDirs

    const confirmMock = vi.fn()
      .mockResolvedValueOnce(true) // jsonOnly confirm
      .mockResolvedValueOnce(false) // allowInsecurePath
      .mockResolvedValueOnce(false); // allowSymlinkCommand

    vi.doMock("@clack/prompts", () => ({ select: (...args: unknown[]) => selectMock(...args), text: (...args: unknown[]) => textMock(...args), confirm: (...args: unknown[]) => confirmMock(...args) }));

    // Provide a valid config snapshot so provider setup starts
    vi.doMock("./config-io.js", () => ({ createSecretsConfigIO: () => ({ readConfigFileSnapshotForWrite: async () => ({ snapshot: { valid: true, config: {}, resolved: {} } }) }) }));

    // Storage-scan ok
    vi.doMock("./storage-scan.js", () => ({ readJsonObjectIfExists: () => ({ error: null, value: null }) }));

    // runSecretsApply won't be reached, but mock it to be safe
    vi.doMock("./apply.js", () => ({ runSecretsApply: vi.fn().mockResolvedValue({ ok: true }) }));

    const mod = await __testAugmentLoadTarget_e2f601b3199b();
    const { runSecretsConfigureInteractive } = mod;

    // Expect the flow to reject because args JSON is invalid and parseArgsInput will throw during provider config
    await __testAugmentVitest_02ade9ae0d48.expect(runSecretsConfigureInteractive({ providersOnly: true })).rejects.toBeTruthy();
  });
});

import * as __testAugmentVitest_02ade9ae0d48 from "vitest";

const __testAugmentLoadTarget_e2f601b3199b = async () => {
  __testAugmentVitest_02ade9ae0d48.vi.doUnmock("./configure.js");
  __testAugmentVitest_02ade9ae0d48.vi.resetModules();
  return import("./configure.js");
};
