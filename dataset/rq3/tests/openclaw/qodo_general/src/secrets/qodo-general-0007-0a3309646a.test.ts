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

  it("does not load auth-profiles when running providers-only", async () => {
    Object.defineProperty(process.stdin, "isTTY", {
      value: true,
      configurable: true,
    });

    selectMock.mockResolvedValue("continue");
    createSecretsConfigIOMock.mockReturnValue({
      readConfigFileSnapshotForWrite: async () => ({
        snapshot: {
          valid: true,
          config: {},
          resolved: {},
        },
      }),
    });
    readJsonObjectIfExistsMock.mockReturnValue({
      error: "boom",
      value: null,
    });

    await expect(runSecretsConfigureInteractive({ providersOnly: true })).rejects.toThrow(
      "No secrets changes were selected.",
    );
    expect(readJsonObjectIfExistsMock).not.toHaveBeenCalled();
  });

  it("edit existing file provider but make no changes (providers-only)", async () => {
    Object.defineProperty(process.stdin, "isTTY", {
      value: true,
      configurable: true,
    });
    // Arrange snapshot with one existing file provider
    createSecretsConfigIOMock.mockReturnValue({
      readConfigFileSnapshotForWrite: async () => ({
        snapshot: {
          valid: true,
          config: {
            secrets: {
              providers: {
                p1: {
                  source: "file",
                  path: "/abs/path/file.json",
                  mode: "json",
                },
              },
            },
          },
          resolved: {},
        },
      }),
    });
    // Prompt sequence:
    // 1) top-level action -> 'edit'
    // 2) select provider to edit -> 'p1'
    // 3) promptProviderSource -> 'file'
    // 4) file path (text) -> '/abs/path/file.json' (same as existing)
    // 5) file mode (select) -> 'json' (same)
    // 6) timeout ms (text) -> '' (blank)
    // 7) max bytes (text) -> '' (blank)
    // 8) top-level action -> 'continue'
    selectMock
      .mockResolvedValueOnce("edit") // choose Edit provider
      .mockResolvedValueOnce("p1")   // pick provider 'p1' to edit
      .mockResolvedValueOnce("file") // promptProviderSource -> file
      .mockResolvedValueOnce("json") // file mode select -> json
      .mockResolvedValueOnce("continue"); // finish
    // Configure text/confirm mocks
    const prompts = await import("@clack/prompts");
    prompts.text.mockReset();
    // text call order inside edit/file flow:
    // - file path -> '/abs/path/file.json'
    // - promptOptionalPositiveInt (timeoutMs) -> ''
    // - promptOptionalPositiveInt (maxBytes) -> ''
    prompts.text
      .mockResolvedValueOnce("/abs/path/file.json")
      .mockResolvedValueOnce("") // timeout ms blank
      .mockResolvedValueOnce(""); // max bytes blank
    // No confirm needed for edit
    readJsonObjectIfExistsMock.mockReturnValue({ error: "boom", value: null });
  
    await expect(runSecretsConfigureInteractive({ providersOnly: true })).rejects.toThrow(
      "No secrets changes were selected.",
    );
    // verify IO helper was used
    expect(createSecretsConfigIOMock).toHaveBeenCalled();
  });


  it("add then remove env provider when providers-only (providers add/remove flow)", async () => {
    Object.defineProperty(process.stdin, "isTTY", {
      value: true,
      configurable: true,
    });
    // Arrange: valid config snapshot with no providers initially
    createSecretsConfigIOMock.mockReturnValue({
      readConfigFileSnapshotForWrite: async () => ({
        snapshot: {
          valid: true,
          config: {},
          resolved: {},
        },
      }),
    });
    // Prepare prompt sequence:
    // 1) top-level action -> 'add'
    // 2) provider source -> 'env'
    // 3) provider alias (text) -> 'myalias'
    // 4) env allowlist (text) -> 'FOO,BAR'
    // 5) top-level action -> 'remove'
    // 6) select provider to remove -> 'myalias'
    // 7) confirm removal -> true
    // 8) top-level action -> 'continue'
    selectMock
      .mockResolvedValueOnce("add")     // choose Add provider
      .mockResolvedValueOnce("env")     // choose env source (promptProviderSource)
      .mockResolvedValueOnce("remove")  // after add, choose Remove provider
      .mockResolvedValueOnce("myalias") // select the provider to remove
      .mockResolvedValueOnce("continue"); // finish
    // Configure text/confirm mocks from mocked @clack/prompts
    const prompts = await import("@clack/prompts");
    // Reset any previous state on text/confirm
    prompts.text.mockReset();
    prompts.confirm.mockReset();
    // text call order:
    // - promptProviderAlias -> 'myalias'
    // - promptEnvNameCsv (allowlist) -> 'FOO,BAR'
    prompts.text
      .mockResolvedValueOnce("myalias")
      .mockResolvedValueOnce("FOO,BAR");
    // confirm for removal
    prompts.confirm.mockResolvedValueOnce(true);
    // Ensure readJsonObjectIfExists is not accidentally called (auth store shouldn't be read)
    readJsonObjectIfExistsMock.mockReturnValue({ error: "boom", value: null });
  
    await expect(runSecretsConfigureInteractive({ providersOnly: true })).rejects.toThrow(
      "No secrets changes were selected.",
    );
    expect(readJsonObjectIfExistsMock).not.toHaveBeenCalled();
  });


  it("throws when config invalid", async () => {
    Object.defineProperty(process.stdin, "isTTY", {
      value: true,
      configurable: true,
    });
    // Mock IO to return an invalid snapshot
    createSecretsConfigIOMock.mockReturnValue({
      readConfigFileSnapshotForWrite: async () => ({
        snapshot: {
          valid: false,
          config: {},
          resolved: {},
        },
      }),
    });
    await expect(runSecretsConfigureInteractive()).rejects.toThrow(
      "Cannot run interactive secrets configure because config is invalid.",
    );
  });


  it("throws when providersOnly and skipProviderSetup combined", async () => {
    Object.defineProperty(process.stdin, "isTTY", {
      value: true,
      configurable: true,
    });
    await expect(
      runSecretsConfigureInteractive({ providersOnly: true, skipProviderSetup: true }),
    ).rejects.toThrow("Cannot combine --providers-only with --skip-provider-setup.");
  });


  it("throws when not tty", async () => {
    // ensure not interactive
    Object.defineProperty(process.stdin, "isTTY", {
      value: false,
      configurable: true,
    });
    // call should reject early due to missing TTY
    await expect(runSecretsConfigureInteractive()).rejects.toThrow(
      "secrets configure requires an interactive TTY.",
    );
    // restore TTY for other tests
    Object.defineProperty(process.stdin, "isTTY", {
      value: true,
      configurable: true,
    });
  });

});
