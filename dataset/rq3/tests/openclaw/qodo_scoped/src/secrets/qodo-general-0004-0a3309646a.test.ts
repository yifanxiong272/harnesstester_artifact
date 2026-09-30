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

  it("add then remove provider results in no secrets changes selected", async () => {
    Object.defineProperty(process.stdin, "isTTY", {
      value: true,
      configurable: true,
    });
    // Snapshot with valid config and no providers initially
    createSecretsConfigIOMock.mockReturnValue({
      readConfigFileSnapshotForWrite: async () => ({
        snapshot: {
          valid: true,
          config: {},
          resolved: {},
        },
      }),
    });
    // Sequence of select calls inside configureProvidersInteractive:
    // 1) action -> "add"
    // 2) provider source -> "file"
    // 3) file mode select -> "json"
    // 4) action -> "remove"
    // 5) remove selection -> alias "default"
    // 6) action -> "continue"
    selectMock
      .mockResolvedValueOnce("add")
      .mockResolvedValueOnce("file")
      .mockResolvedValueOnce("json")
      .mockResolvedValueOnce("remove")
      .mockResolvedValueOnce("default")
      .mockResolvedValueOnce("continue");
    // Acquire the mocked prompt functions and set their responses:
    const prompts = await import("@clack/prompts");
    // text() calls order:
    // 1) provider alias
    // 2) file path
    // 3) timeout ms (promptOptionalPositiveInt) -> blank
    // 4) max bytes (promptOptionalPositiveInt) -> blank
    prompts.text.mockReset();
    prompts.text
      .mockResolvedValueOnce("default") // provider alias
      .mockResolvedValueOnce("/absolute/path/to/secrets.json") // file path
      .mockResolvedValueOnce("") // timeout ms (blank => undefined)
      .mockResolvedValueOnce(""); // max bytes (blank => undefined)
    // confirm() used for remove confirmation
    prompts.confirm.mockReset();
    prompts.confirm.mockResolvedValueOnce(true);
    // Ensure auth store read is not invoked for providers-only flow
    readJsonObjectIfExistsMock.mockReset();
    await expect(runSecretsConfigureInteractive({ providersOnly: true })).rejects.toThrow(
      "No secrets changes were selected.",
    );
    expect(readJsonObjectIfExistsMock).not.toHaveBeenCalled();
  });


  it("throws when the initial provider selection is cancelled", async () => {
    Object.defineProperty(process.stdin, "isTTY", {
      value: true,
      configurable: true,
    });
    // Simulate user cancel by resolving select to a symbol which triggers assertNoCancel
    selectMock.mockResolvedValue(Symbol("cancelled"));
    // Provide an IO that returns a valid snapshot so we reach provider selection
    createSecretsConfigIOMock.mockReturnValue({
      readConfigFileSnapshotForWrite: async () => ({
        snapshot: {
          valid: true,
          config: {},
          resolved: {},
        },
      }),
    });
    await expect(runSecretsConfigureInteractive()).rejects.toThrow("Secrets configure cancelled.");
  });


  it("throws when config snapshot is invalid", async () => {
    Object.defineProperty(process.stdin, "isTTY", {
      value: true,
      configurable: true,
    });
    // Mock interactive select to ensure no unexpected prompt usage
    selectMock.mockResolvedValue("continue");
    // Provide an IO that returns an invalid snapshot
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


  it("errors when --providers-only is combined with --skip-provider-setup", async () => {
    Object.defineProperty(process.stdin, "isTTY", {
      value: true,
      configurable: true,
    });
    // No need to mock IO because the validation happens before any IO reads
    await expect(
      runSecretsConfigureInteractive({ providersOnly: true, skipProviderSetup: true }),
    ).rejects.toThrow("Cannot combine --providers-only with --skip-provider-setup.");
  });


  it("throws if not an interactive TTY", async () => {
    // ensure non-interactive
    Object.defineProperty(process.stdin, "isTTY", {
      value: false,
      configurable: true,
    });
    // Call with no other setup; should short-circuit and throw about TTY
    await expect(runSecretsConfigureInteractive()).rejects.toThrow(
      "secrets configure requires an interactive TTY.",
    );
    // restore for other tests
    Object.defineProperty(process.stdin, "isTTY", {
      value: true,
      configurable: true,
    });
  });

});
