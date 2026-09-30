import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { beforeEach, describe, expect, it } from "vitest";
import { createDoctorRuntime, mockDoctorConfigSnapshot } from "./doctor.e2e-harness.js";
import { loadDoctorCommandForTest, terminalNoteMock } from "./doctor.note-test-helpers.js";
import "./doctor.fast-path-mocks.js";
import { DEFAULT_GOOGLE_API_BASE_URL } from "../infra/google-api-base-url.js";
import { normalizeCompatibilityConfigValues } from "../commands/doctor-legacy-config.js";

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

  it("migrates legacy nano-banana skill into models.providers.google and agents.defaults.imageGenerationModel", () => {
    const input = {
      skills: {
        // single entry so removal of the key results in deleting the entire allowBundled array
        allowBundled: ["nano-banana-pro"],
        entries: {
          "nano-banana-pro": {
            // apiKey should be trimmed and used when env.GEMINI_API_KEY is not present
            apiKey: "  g-API-KEY-123  ",
          },
        },
      },
    } as any;
  
    const { config, changes } = normalizeCompatibilityConfigValues(input);
  
    // models.providers.google.apiKey should be set to trimmed key
    expect((config as any).models).toBeTruthy();
    expect((config as any).models.providers).toBeTruthy();
    const google = (config as any).models.providers.google;
    expect(google).toBeTruthy();
    expect(google.apiKey).toBe("g-API-KEY-123");
  
    // baseUrl should have been filled with the default constant
    expect(google.baseUrl).toBe(DEFAULT_GOOGLE_API_BASE_URL);
  
    // ensure agent default imageGenerationModel.primary set to the expected legacy model id
    expect(config.agents).toBeTruthy();
    expect(config.agents!.defaults).toBeTruthy();
    expect((config.agents!.defaults as any).imageGenerationModel).toBeTruthy();
    expect((config.agents!.defaults as any).imageGenerationModel.primary).toBe(
      "google/gemini-3-pro-image-preview",
    );
  
    // the legacy skill entry should be removed (skills may be removed entirely when empty)
    expect((config as any).skills).toBeFalsy();
  
    // changes should mention moving the API key, removing allowBundled entry and legacy skill removal
    expect(changes.some((c) => String(c).includes("Moved skills.entries.nano-banana-pro"))).toBe(true);
    expect(
      changes.some((c) => String(c).includes("Removed skills.allowBundled entry for nano-banana-pro")),
    ).toBe(true);
    expect(changes.some((c) => String(c).includes("Removed legacy skills.entries.nano-banana-pro"))).toBe(true);
  });


  it("migrates legacy nano-banana skill into models.providers.google and agents.defaults.imageGenerationModel", () => {
    const input = {
      skills: {
        // include nano-banana-pro but keep another entry so array is not removed entirely
        allowBundled: ["nano-banana-pro", "other-skill"],
        entries: {
          "nano-banana-pro": {
            // GEMINI_API_KEY in env should be preferred and trimmed
            env: { GEMINI_API_KEY: "  g-API-KEY-123  " },
            // apiKey present but env should win
            apiKey: "should-not-be-used",
          },
          "other-skill": {
            info: "keep",
          },
        },
      },
    } as any;
  
    const { config, changes } = normalizeCompatibilityConfigValues(input);
  
    // models.providers.google.apiKey should be set to trimmed GEMINI key
    expect(config.models).toBeTruthy();
    expect((config.models as any).providers).toBeTruthy();
    const google = (config.models as any).providers.google;
    expect(google).toBeTruthy();
    expect(google.apiKey).toBe("g-API-KEY-123");
    // baseUrl should have been filled with the default
    expect(google.baseUrl).toBe(DEFAULT_GOOGLE_API_BASE_URL);
    // ensure agent default imageGenerationModel.primary set to the expected legacy model id
    expect(config.agents).toBeTruthy();
    expect(config.agents!.defaults).toBeTruthy();
    expect((config.agents!.defaults as any).imageGenerationModel).toBeTruthy();
    expect((config.agents!.defaults as any).imageGenerationModel.primary).toBe(
      "google/gemini-3-pro-image-preview",
    );
  
    // the legacy skill entry should be removed
    expect((config.skills as any).entries).toBeTruthy();
    expect((config.skills as any).entries["nano-banana-pro"]).toBeUndefined();
  
    // changes should mention moving the API key and removing the legacy skill;
    // when allowBundled contained other keys the implementation emits the "Removed nano-banana-pro from skills.allowBundled." message.
    expect(
      changes.some((c) =>
        String(c).includes("Moved skills.entries.nano-banana-pro") &&
        String(c).includes("agents.defaults.imageGenerationModel.primary")
      ),
    ).toBe(true);
    expect(
      changes.some((c) => String(c).includes("Removed nano-banana-pro from skills.allowBundled.")),
    ).toBe(true);
    expect(
      changes.some((c) => String(c).includes("Removed legacy skills.entries.nano-banana-pro")),
    ).toBe(true);
  });


  it("migrates legacy deepgram settings in tools.media.audio and its models into providerOptions.deepgram", () => {
    const input = {
      tools: {
        media: {
          audio: {
            deepgram: {
              detectLanguage: true,
              punctuate: false,
            },
            models: [
              {
                // deepgram compatibility object on a model entry should also be migrated
                deepgram: {
                  smartFormat: true,
                },
              },
            ],
          },
        },
      },
    } as any;
  
    const { config, changes } = normalizeCompatibilityConfigValues(input);
  
    expect(config).toBeTruthy();
    const audio = (config.tools as any).media.audio;
    expect(audio).toBeTruthy();
    // legacy top-level deepgram should be removed
    expect(audio.deepgram).toBeUndefined();
    // providerOptions.deepgram should exist and contain mapped keys
    expect(audio.providerOptions).toBeTruthy();
    expect(audio.providerOptions.deepgram.detect_language).toBe(true);
    expect(audio.providerOptions.deepgram.punctuate).toBe(false);
  
    // model-level deepgram should be migrated into model.providerOptions.deepgram
    const model = audio.models?.[0];
    expect(model).toBeTruthy();
    expect(model.deepgram).toBeUndefined();
    expect(model.providerOptions).toBeTruthy();
    expect(model.providerOptions.deepgram.smart_format).toBe(true);
  
    // change message should mention the move from tools.media.audio.deepgram
    expect(changes.some((c) => String(c).includes("Moved tools.media.audio.deepgram"))).toBe(true);
  });


  it("moves browser.ssrfPolicy.allowPrivateNetwork to dangerouslyAllowPrivateNetwork", () => {
    const input = {
      browser: {
        ssrfPolicy: {
          allowPrivateNetwork: true,
        },
      },
    } as any;
  
    const { config, changes } = normalizeCompatibilityConfigValues(input);
  
    expect(config).toBeTruthy();
    expect((config.browser as any).ssrfPolicy).toBeTruthy();
    expect((config.browser as any).ssrfPolicy.dangerouslyAllowPrivateNetwork).toBe(true);
    // Ensure the change message mentions the migration and the resolved value.
    const found = changes.some((c) =>
      String(c).includes("Moved browser.ssrfPolicy.allowPrivateNetwork") &&
      String(c).includes("dangerouslyAllowPrivateNetwork") &&
      String(c).includes("true")
    );
    expect(found).toBe(true);
  });


  it("moves legacy deepgram compat fields into providerOptions.deepgram for media and models", () => {
    const input = {
      tools: {
        media: {
          audio: {
            // legacy compat shape should be converted to providerOptions.deepgram with renamed keys
            deepgram: { detectLanguage: true, punctuate: false },
            models: [
              {
                // model-level legacy deepgram should become model.providerOptions.deepgram
                deepgram: { punctuate: true },
              },
            ],
          },
        },
      },
    } as any;
  
    const { config, changes } = normalizeCompatibilityConfigValues(input);
  
    expect(config.tools).toBeTruthy();
    const audio = (config.tools as any).media.audio;
    expect(audio).toBeTruthy();
  
    // top-level audio.deepgram should be removed and providerOptions.deepgram created
    expect(audio.deepgram).toBeUndefined();
    expect(audio.providerOptions).toBeTruthy();
    expect(audio.providerOptions.deepgram).toBeTruthy();
    // keys renamed: detectLanguage -> detect_language
    expect(audio.providerOptions.deepgram.detect_language).toBe(true);
    expect(audio.providerOptions.deepgram.punctuate).toBe(false);
  
    // model-level deepgram moved to model.providerOptions.deepgram
    expect(Array.isArray(audio.models)).toBe(true);
    expect(audio.models[0].deepgram).toBeUndefined();
    expect(audio.models[0].providerOptions).toBeTruthy();
    expect(audio.models[0].providerOptions.deepgram.punctuate).toBe(true);
  
    // changes should indicate migration for audio and its model entry
    expect(
      changes.some((c) => String(c).includes("Moved tools.media.audio.deepgram → tools.media.audio.providerOptions.deepgram")),
    ).toBe(true);
  });


  it("migrates tools.message.allowCrossContextSend=true to canonical crossContext fields", () => {
    const input = {
      tools: {
        message: {
          allowCrossContextSend: true,
        },
      },
    } as any;
  
    const { config, changes } = normalizeCompatibilityConfigValues(input);
  
    expect(config.tools).toBeTruthy();
    const msg = (config.tools as any).message;
    expect(msg).toBeTruthy();
    expect(msg.allowCrossContextSend).toBeUndefined();
    expect(msg.crossContext).toBeTruthy();
    expect(msg.crossContext.allowWithinProvider).toBe(true);
    expect(msg.crossContext.allowAcrossProviders).toBe(true);
  
    expect(
      changes.some((c) =>
        String(c).includes("Moved tools.message.allowCrossContextSend → tools.message.crossContext.allowWithinProvider/allowAcrossProviders (true)"),
      ),
    ).toBe(true);
  });


  it("migrates browser relayBindHost, profile drivers and ssrfPolicy.allowPrivateNetwork", () => {
    const input = {
      browser: {
        // legacy field that should be removed
        relayBindHost: "127.0.0.1",
        // profiles: foo should be migrated from "extension" to "existing-session"
        profiles: {
          foo: { driver: "extension" },
          bar: { driver: "existing-session" }, // should be preserved
        },
        // legacy ssrf policy key that should be normalized
        ssrfPolicy: {
          allowPrivateNetwork: true,
        },
      },
    } as any;
  
    const { config, changes } = normalizeCompatibilityConfigValues(input);
  
    // relayBindHost removed
    expect(config.browser).toBeTruthy();
    expect((config.browser as any).relayBindHost).toBeUndefined();
  
    // profile driver migrated
    expect((config.browser as any).profiles).toBeTruthy();
    expect((config.browser as any).profiles.foo.driver).toBe("existing-session");
    expect((config.browser as any).profiles.bar.driver).toBe("existing-session");
  
    // ssrf policy migrated to dangerouslyAllowPrivateNetwork true
    expect((config.browser as any).ssrfPolicy).toBeTruthy();
    expect((config.browser as any).ssrfPolicy.allowPrivateNetwork).toBeUndefined();
    expect((config.browser as any).ssrfPolicy.dangerouslyAllowPrivateNetwork).toBe(true);
  
    // changes should mention the relay removal, the driver migration and the ssrf policy movement
    expect(changes.some((c) => String(c).includes("relayBindHost"))).toBe(true);
    expect(
      changes.some((c) =>
        String(c).includes('browser.profiles.foo.driver "extension" → "existing-session"'),
      ),
    ).toBe(true);
    expect(
      changes.some((c) =>
        String(c).includes("Moved browser.ssrfPolicy.allowPrivateNetwork → browser.ssrfPolicy.dangerouslyAllowPrivateNetwork"),
      ),
    ).toBe(true);
  });

});
