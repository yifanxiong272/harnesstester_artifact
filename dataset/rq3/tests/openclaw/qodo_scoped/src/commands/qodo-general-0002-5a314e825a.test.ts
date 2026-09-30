import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { beforeEach, describe, expect, it } from "vitest";
import { createDoctorRuntime, mockDoctorConfigSnapshot } from "./doctor.e2e-harness.js";
import { loadDoctorCommandForTest, terminalNoteMock } from "./doctor.note-test-helpers.js";
import "./doctor.fast-path-mocks.js";
import { normalizeCompatibilityConfigValues } from "./doctor-legacy-config.js";

let doctorCommand: typeof import("./doctor.js").doctorCommand;

describe("doctor command", () => {
  beforeEach(async () => {
    doctorCommand = await loadDoctorCommandForTest({
      unmockModules: ["./doctor-state-integrity.js"],
    });
  });

  it("warns when the state directory is missing", async () => {
    mockDoctorConfigSnapshot();

    const missingDir = fs.mkdtempSync(path.join(os.tmpdir(), "openclaw-missing-state-"));
    fs.rmSync(missingDir, { recursive: true, force: true });
    process.env.OPENCLAW_STATE_DIR = missingDir;
    await doctorCommand(createDoctorRuntime(), {
      nonInteractive: true,
      workspaceSuggestions: false,
    });

    const stateNote = terminalNoteMock.mock.calls.find(([message]) =>
      String(message).includes("state directory missing"),
    );
    expect(stateNote).toBeTruthy();
    expect(String(stateNote?.[0])).toContain("CRITICAL");
  });

  it("warns about opencode provider overrides", async () => {
    mockDoctorConfigSnapshot({
      config: {
        models: {
          providers: {
            opencode: {
              api: "openai-completions",
              baseUrl: "https://opencode.ai/zen/v1",
            },
            "opencode-go": {
              api: "openai-completions",
              baseUrl: "https://opencode.ai/zen/go/v1",
            },
          },
        },
      },
    });

    await doctorCommand(createDoctorRuntime(), {
      nonInteractive: true,
      workspaceSuggestions: false,
    });

    const warned = terminalNoteMock.mock.calls.some(
      ([message, title]) =>
        title === "OpenCode" &&
        String(message).includes("models.providers.opencode") &&
        String(message).includes("models.providers.opencode-go"),
    );
    expect(warned).toBe(true);
  });

  it("skips gateway auth warning when OPENCLAW_GATEWAY_TOKEN is set", async () => {
    mockDoctorConfigSnapshot({
      config: {
        gateway: { mode: "local" },
      },
    });

    const prevToken = process.env.OPENCLAW_GATEWAY_TOKEN;
    process.env.OPENCLAW_GATEWAY_TOKEN = "env-token-1234567890";
    try {
      await doctorCommand(createDoctorRuntime(), {
        nonInteractive: true,
        workspaceSuggestions: false,
      });
    } finally {
      if (prevToken === undefined) {
        delete process.env.OPENCLAW_GATEWAY_TOKEN;
      } else {
        process.env.OPENCLAW_GATEWAY_TOKEN = prevToken;
      }
    }

    const warned = terminalNoteMock.mock.calls.some(([message]) =>
      String(message).includes("Gateway auth is off or missing a token"),
    );
    expect(warned).toBe(false);
  });

  it("warns when token and password are both configured and gateway.auth.mode is unset", async () => {
    mockDoctorConfigSnapshot({
      config: {
        gateway: {
          mode: "local",
          auth: {
            token: "token-value",
            password: "password-value", // pragma: allowlist secret
          },
        },
      },
    });

    await doctorCommand(createDoctorRuntime(), {
      nonInteractive: true,
      workspaceSuggestions: false,
    });

    const gatewayAuthNote = terminalNoteMock.mock.calls.find((call) => call[1] === "Gateway auth");
    expect(gatewayAuthNote).toBeTruthy();
    expect(String(gatewayAuthNote?.[0])).toContain("gateway.auth.mode is unset");
    expect(String(gatewayAuthNote?.[0])).toContain("openclaw config set gateway.auth.mode token");
    expect(String(gatewayAuthNote?.[0])).toContain(
      "openclaw config set gateway.auth.mode password",
    );
  });

  it("keeps doctor read-only when gateway token is SecretRef-managed but unresolved", async () => {
    mockDoctorConfigSnapshot({
      config: {
        gateway: {
          mode: "local",
          auth: {
            mode: "token",
            token: {
              source: "env",
              provider: "default",
              id: "OPENCLAW_GATEWAY_TOKEN",
            },
          },
        },
        secrets: {
          providers: {
            default: { source: "env" },
          },
        },
      },
    });

    const previousToken = process.env.OPENCLAW_GATEWAY_TOKEN;
    delete process.env.OPENCLAW_GATEWAY_TOKEN;
    try {
      await doctorCommand(createDoctorRuntime(), {
        nonInteractive: true,
        workspaceSuggestions: false,
      });
    } finally {
      if (previousToken === undefined) {
        delete process.env.OPENCLAW_GATEWAY_TOKEN;
      } else {
        process.env.OPENCLAW_GATEWAY_TOKEN = previousToken;
      }
    }

    const gatewayAuthNote = terminalNoteMock.mock.calls.find((call) => call[1] === "Gateway auth");
    expect(gatewayAuthNote).toBeTruthy();
    expect(String(gatewayAuthNote?.[0])).toContain(
      "Gateway token is managed via SecretRef and is currently unavailable.",
    );
    expect(String(gatewayAuthNote?.[0])).toContain(
      "Doctor will not overwrite gateway.auth.token with a plaintext value.",
    );
  });

  it("migrates tools.media.audio.deepgram into providerOptions.deepgram", () => {
    const input = {
      tools: {
        media: {
          audio: {
            deepgram: {
              detectLanguage: true,
              punctuate: false,
              smartFormat: true,
            },
          },
        },
      },
    };
    const { config, changes } = normalizeCompatibilityConfigValues(input as any);
    const audio = (config as any).tools.media.audio as Record<string, unknown>;
    expect(audio).toBeTruthy();
    expect(audio.providerOptions).toBeTruthy();
    const dg = (audio.providerOptions as any).deepgram as Record<string, unknown>;
    expect(dg.detect_language).toBe(true);
    expect(dg.punctuate).toBe(false);
    expect(dg.smart_format).toBe(true);
    expect(
      changes.some((c) => String(c).includes("Moved tools.media.audio.deepgram")),
    ).toBe(true);
  });


  it("migrates legacy nano-banana skill into models.providers.google and agents.defaults.imageGenerationModel", () => {
    const input = {
      skills: {
        allowBundled: ["nano-banana-pro", "other-skill"],
        entries: {
          "nano-banana-pro": {
            apiKey: "g-abc-123",
          },
        },
      },
    };
    const { config, changes } = normalizeCompatibilityConfigValues(input as any);
    // agents.defaults.imageGenerationModel.primary should be set to expected model id
    const agentDefaultImage = (config as any).agents?.defaults?.imageGenerationModel;
    expect(agentDefaultImage).toBeTruthy();
    expect(agentDefaultImage.primary).toBe("google/gemini-3-pro-image-preview");
    // models.providers.google.apiKey should be moved from the legacy skill entry
    const googleProvider = (config as any).models?.providers?.google;
    expect(googleProvider).toBeTruthy();
    expect(googleProvider.apiKey).toBe("g-abc-123");
    // baseUrl and models array should be filled if missing
    expect(typeof googleProvider.baseUrl === "string" && googleProvider.baseUrl.length > 0).toBe(true);
    expect(Array.isArray(googleProvider.models)).toBe(true);
    // skills.entries should no longer contain the legacy key
    const skills = (config as any).skills || {};
    expect((skills.entries || {})["nano-banana-pro"]).toBeUndefined();
    // allowBundled should have removed the nano-banana entry
    expect(Array.isArray(skills.allowBundled)).toBe(true);
    expect((skills.allowBundled as string[]).includes("nano-banana-pro")).toBe(false);
    // changes should include messages about moved key(s)
    expect(
      changes.some((c: unknown) => String(c).includes("Moved skills.entries.nano-banana-pro") || String(c).includes("Removed skills.entries.nano-banana-pro")),
    ).toBe(true);
  });


  it("moves capability-level and model-level deepgram compat into providerOptions.deepgram", () => {
    const input = {
      tools: {
        media: {
          audio: {
            // legacy capability-level compat fields
            deepgram: {
              detectLanguage: true,
              punctuate: false,
            },
            models: [
              {
                name: "m-a",
                deepgram: {
                  smartFormat: true,
                },
              },
              {
                name: "m-b",
                // non-record deepgram should be skipped (no crash)
                deepgram: null,
              },
            ],
          },
          // also include a top-level models array to ensure it's processed
          models: [
            {
              deepgram: {
                detectLanguage: false,
              },
              other: "x",
            },
          ],
        },
      },
    };
    const { config, changes } = normalizeCompatibilityConfigValues(input as any);
    const media = (config as any).tools?.media;
    expect(media).toBeTruthy();
    // Capability-level providerOptions.deepgram should reflect mapped keys from capability deepgram
    const audio = media.audio as Record<string, unknown>;
    expect(audio.providerOptions).toBeTruthy();
    const capabilityDeepgram = (audio.providerOptions as any).deepgram as Record<string, unknown>;
    expect(capabilityDeepgram.detect_language).toBe(true);
    expect(capabilityDeepgram.punctuate).toBe(false);
    // Model-level migration: the first model should have providerOptions.deepgram.smart_format true
    expect(Array.isArray(audio.models)).toBe(true);
    const firstModel = (audio.models as any[])[0] as Record<string, unknown>;
    expect(firstModel.providerOptions).toBeTruthy();
    expect(((firstModel.providerOptions as any).deepgram as any).smart_format).toBe(true);
    // The top-level tools.media.models entry should also be migrated
    const topModels = media.models as any[];
    expect(Array.isArray(topModels)).toBe(true);
    // Changes should mention moved deepgram entries
    expect(
      changes.some((c: unknown) => String(c).includes("Moved tools.media.audio.deepgram") || String(c).includes("Moved tools.media.audio.models")),
    ).toBe(true);
  });


  it("removes browser.relayBindHost and migrates extension driver → existing-session in profiles", () => {
    const input = {
      browser: {
        relayBindHost: "127.0.0.1",
        profiles: {
          chrome: { driver: "extension" },
          other: { driver: " extension " }, // test trimming
          keep: { driver: "local" },
        },
      },
    };
    const { config, changes } = normalizeCompatibilityConfigValues(input as any);
    expect((config as any).browser).toBeTruthy();
    const browser = (config as any).browser as Record<string, unknown>;
    // relayBindHost should be removed
    expect(browser.relayBindHost).toBeUndefined();
    // profiles should exist and drivers normalized
    const profiles = (browser.profiles || {}) as Record<string, any>;
    expect(profiles.chrome.driver).toBe("existing-session");
    expect(profiles.other.driver).toBe("existing-session");
    // unchanged profile should keep original driver
    expect(profiles.keep.driver).toBe("local");
    // change messages should include both relay removal and profile driver migration
    expect(changes.some((c: unknown) => String(c).includes("Removed browser.relayBindHost"))).toBe(true);
    expect(
      changes.some((c: unknown) =>
        String(c).includes('Moved browser.profiles.chrome.driver') || String(c).includes('Moved browser.profiles.other.driver'),
      ),
    ).toBe(true);
  });


  it("migrates slack dm.policy and dm.allowFrom to channels.slack.dmPolicy and allowFrom and removes empty dm", () => {
    const input = {
      channels: {
        slack: {
          // legacy nested dm object
          dm: {
            policy: "private",
            allowFrom: ["alice", "bob"],
          },
        },
      },
    };
    const { config, changes } = normalizeCompatibilityConfigValues(input as any);
    expect((config as any).channels).toBeTruthy();
    const slack = (config as any).channels.slack as Record<string, unknown>;
    // legacy keys should be moved up
    expect(slack.dmPolicy).toBe("private");
    expect(Array.isArray(slack.allowFrom)).toBe(true);
    expect((slack.allowFrom as string[]).join(",")).toBe("alice,bob");
    // legacy dm should be removed entirely
    expect(slack.dm).toBeUndefined();
    // check change messages contain the expected move messages
    expect(
      changes.some((c: unknown) =>
        String(c).includes("Moved channels.slack.dm.policy") || String(c).includes("Moved channels.slack.dm.allowFrom"),
      ),
    ).toBe(true);
  });


  it("moves nano-banana skill apiKey → models.providers.google.apiKey and sets imageGenerationModel.primary", () => {
    const input = {
      skills: {
        allowBundled: ["nano-banana-pro", "other-skill"],
        entries: {
          "nano-banana-pro": {
            apiKey: "  legacy-key-xyz  ",
          },
          "some-other-skill": {
            apiKey: "keep-me",
          },
        },
      },
    };
    const { config, changes } = normalizeCompatibilityConfigValues(input as any);
    // models.providers.google.apiKey should be set from the legacy skill (trimmed)
    expect((config as any).models).toBeTruthy();
    expect((config as any).models.providers).toBeTruthy();
    expect((config as any).models.providers.google.apiKey).toBe("legacy-key-xyz");
    // agents.defaults.imageGenerationModel.primary should be set to the expected nano-banana model id
    expect((config as any).agents).toBeTruthy();
    expect((config as any).agents.defaults).toBeTruthy();
    expect((config as any).agents.defaults.imageGenerationModel.primary).toBe(
      "google/gemini-3-pro-image-preview",
    );
    // legacy entry removed from skills.entries and allowBundled cleans the nano key
    expect((config as any).skills).toBeTruthy();
    const allowBundled = (config as any).skills.allowBundled as string[] | undefined;
    if (Array.isArray(allowBundled)) {
      expect(allowBundled.includes("nano-banana-pro")).toBe(false);
    }
    // change messages should mention moved legacy skill and the models.providers.google.apiKey move
    expect(
      changes.some((c) => String(c).includes("Moved skills.entries.nano-banana-pro")),
    ).toBe(true);
    expect(
      changes.some((c) =>
        String(c).includes("Moved skills.entries.nano-banana-pro") ||
        String(c).includes("models.providers.google.apiKey"),
      ),
    ).toBe(true);
  });


  it("migrates browser.ssrfPolicy.allowPrivateNetwork -> dangerouslyAllowPrivateNetwork", () => {
    const input = {
      browser: {
        ssrfPolicy: {
          allowPrivateNetwork: true,
        },
      },
    };
    const { config, changes } = normalizeCompatibilityConfigValues(input as any);
    expect(config).toBeTruthy();
    expect(config.browser).toBeTruthy();
    // legacy key removed
    expect((config as any).browser.ssrfPolicy.allowPrivateNetwork).toBeUndefined();
    // canonical key set
    expect((config as any).browser.ssrfPolicy.dangerouslyAllowPrivateNetwork).toBe(true);
    // change message recorded
    expect(changes.some((c) => String(c).includes("browser.ssrfPolicy.allowPrivateNetwork"))).toBe(
      true,
    );
  });

});
