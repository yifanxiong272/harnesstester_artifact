import fs from "node:fs/promises";
import path from "node:path";
import "./test-helpers/fast-coding-tools.js";
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import {
  buildEmbeddedRunnerAssistant,
  cleanupEmbeddedPiRunnerTestWorkspace,
  createMockUsage,
  createEmbeddedPiRunnerOpenAiConfig,
  createResolvedEmbeddedRunnerModel,
  createEmbeddedPiRunnerTestWorkspace,
  type EmbeddedPiRunnerTestWorkspace,
  immediateEnqueue,
  makeEmbeddedRunnerAttempt,
} from "./test-helpers/pi-embedded-runner-e2e-fixtures.js";
import { sanitizeUserFacingText } from "./pi-embedded-helpers/errors.js";
import { formatAssistantErrorText } from "./pi-embedded-helpers/errors.js";
import { extractObservedOverflowTokenCount } from "./pi-embedded-helpers/errors.js";

const runEmbeddedAttemptMock = vi.fn();

vi.mock("@mariozechner/pi-ai", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@mariozechner/pi-ai")>();

  const buildAssistantMessage = (model: { api: string; provider: string; id: string }) => ({
    role: "assistant" as const,
    content: [{ type: "text" as const, text: "ok" }],
    stopReason: "stop" as const,
    api: model.api,
    provider: model.provider,
    model: model.id,
    usage: createMockUsage(1, 1),
    timestamp: Date.now(),
  });

  const buildAssistantErrorMessage = (model: { api: string; provider: string; id: string }) => ({
    role: "assistant" as const,
    content: [],
    stopReason: "error" as const,
    errorMessage: "boom",
    api: model.api,
    provider: model.provider,
    model: model.id,
    usage: createMockUsage(0, 0),
    timestamp: Date.now(),
  });

  return {
    ...actual,
    complete: async (model: { api: string; provider: string; id: string }) => {
      if (model.id === "mock-error") {
        return buildAssistantErrorMessage(model);
      }
      return buildAssistantMessage(model);
    },
    completeSimple: async (model: { api: string; provider: string; id: string }) => {
      if (model.id === "mock-error") {
        return buildAssistantErrorMessage(model);
      }
      return buildAssistantMessage(model);
    },
    streamSimple: (model: { api: string; provider: string; id: string }) => {
      const stream = actual.createAssistantMessageEventStream();
      queueMicrotask(() => {
        stream.push({
          type: "done",
          reason: "stop",
          message:
            model.id === "mock-error"
              ? buildAssistantErrorMessage(model)
              : buildAssistantMessage(model),
        });
        stream.end();
      });
      return stream;
    },
  };
});

const installRunEmbeddedMocks = () => {
  vi.doMock("../plugins/hook-runner-global.js", () => ({
    getGlobalHookRunner: vi.fn(() => undefined),
    getGlobalPluginRegistry: vi.fn(() => null),
    hasGlobalHooks: vi.fn(() => false),
    initializeGlobalHookRunner: vi.fn(),
    resetGlobalHookRunner: vi.fn(),
  }));
  vi.doMock("../context-engine/index.js", () => ({
    ensureContextEnginesInitialized: vi.fn(),
    resolveContextEngine: vi.fn(async () => ({
      dispose: async () => undefined,
    })),
  }));
  vi.doMock("./runtime-plugins.js", () => ({
    ensureRuntimePluginsLoaded: vi.fn(),
  }));
  vi.doMock("./pi-embedded-runner/run/attempt.js", () => ({
    runEmbeddedAttempt: (params: unknown) => runEmbeddedAttemptMock(params),
  }));
  vi.doMock("./pi-embedded-runner/model.js", async (importOriginal) => {
    const actual = await importOriginal<typeof import("./pi-embedded-runner/model.js")>();
    return {
      ...actual,
      resolveModelAsync: async (provider: string, modelId: string) =>
        createResolvedEmbeddedRunnerModel(provider, modelId),
    };
  });
  vi.doMock("../plugins/provider-runtime.js", async (importOriginal) => {
    const actual = await importOriginal<typeof import("../plugins/provider-runtime.js")>();
    return {
      ...actual,
      prepareProviderRuntimeAuth: vi.fn(async () => undefined),
    };
  });
  vi.doMock("./models-config.js", async (importOriginal) => {
    const mod = await importOriginal<typeof import("./models-config.js")>();
    return {
      ...mod,
      ensureOpenClawModelsJson: vi.fn(async () => ({ wrote: false })),
    };
  });
};

let runEmbeddedPiAgent: typeof import("./pi-embedded-runner/run.js").runEmbeddedPiAgent;
let SessionManager: typeof import("@mariozechner/pi-coding-agent").SessionManager;
let e2eWorkspace: EmbeddedPiRunnerTestWorkspace | undefined;
let agentDir: string;
let workspaceDir: string;
let sessionCounter = 0;
let runCounter = 0;

beforeAll(async () => {
  vi.useRealTimers();
  vi.resetModules();
  installRunEmbeddedMocks();
  ({ runEmbeddedPiAgent } = await import("./pi-embedded-runner/run.js"));
  ({ SessionManager } = await import("@mariozechner/pi-coding-agent"));
  e2eWorkspace = await createEmbeddedPiRunnerTestWorkspace("openclaw-embedded-agent-");
  ({ agentDir, workspaceDir } = e2eWorkspace);
}, 180_000);

afterAll(async () => {
  await cleanupEmbeddedPiRunnerTestWorkspace(e2eWorkspace);
  e2eWorkspace = undefined;
});

beforeEach(() => {
  vi.useRealTimers();
  runEmbeddedAttemptMock.mockReset();
  runEmbeddedAttemptMock.mockImplementation(async () => {
    throw new Error("unexpected extra runEmbeddedAttempt call");
  });
});

const nextSessionFile = () => {
  sessionCounter += 1;
  return path.join(workspaceDir, `session-${sessionCounter}.jsonl`);
};
const nextRunId = (prefix = "run-embedded-test") => `${prefix}-${++runCounter}`;
const nextSessionKey = () => `agent:test:embedded:${nextRunId("session-key")}`;

const runWithOrphanedSingleUserMessage = async (text: string, sessionKey: string) => {
  const sessionFile = nextSessionFile();
  const sessionManager = SessionManager.open(sessionFile);
  sessionManager.appendMessage({
    role: "user",
    content: [{ type: "text", text }],
    timestamp: Date.now(),
  });

  runEmbeddedAttemptMock.mockResolvedValueOnce(
    makeEmbeddedRunnerAttempt({
      assistantTexts: ["ok"],
      lastAssistant: buildEmbeddedRunnerAssistant({
        content: [{ type: "text", text: "ok" }],
      }),
    }),
  );

  const cfg = createEmbeddedPiRunnerOpenAiConfig(["mock-1"]);
  return await runEmbeddedPiAgent({
    sessionId: "session:test",
    sessionKey,
    sessionFile,
    workspaceDir,
    config: cfg,
    prompt: "hello",
    provider: "openai",
    model: "mock-1",
    timeoutMs: 5_000,
    agentDir,
    runId: nextRunId("orphaned-user"),
    enqueue: immediateEnqueue,
  });
};

const textFromContent = (content: unknown) => {
  if (typeof content === "string") {
    return content;
  }
  if (Array.isArray(content) && content[0]?.type === "text") {
    return (content[0] as { text?: string }).text;
  }
  return undefined;
};

const readSessionEntries = async (sessionFile: string) => {
  const raw = await fs.readFile(sessionFile, "utf-8");
  return raw
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line) as { type?: string; customType?: string; data?: unknown });
};

const readSessionMessages = async (sessionFile: string) => {
  const entries = await readSessionEntries(sessionFile);
  return entries
    .filter((entry) => entry.type === "message")
    .map(
      (entry) => (entry as { message?: { role?: string; content?: unknown } }).message,
    ) as Array<{ role?: string; content?: unknown }>;
};

const runDefaultEmbeddedTurn = async (sessionFile: string, prompt: string, sessionKey: string) => {
  const cfg = createEmbeddedPiRunnerOpenAiConfig(["mock-error"]);
  runEmbeddedAttemptMock.mockResolvedValueOnce(
    makeEmbeddedRunnerAttempt({
      assistantTexts: ["ok"],
      lastAssistant: buildEmbeddedRunnerAssistant({
        content: [{ type: "text", text: "ok" }],
      }),
    }),
  );
  await runEmbeddedPiAgent({
    sessionId: "session:test",
    sessionKey,
    sessionFile,
    workspaceDir,
    config: cfg,
    prompt,
    provider: "openai",
    model: "mock-error",
    timeoutMs: 5_000,
    agentDir,
    runId: nextRunId("default-turn"),
    enqueue: immediateEnqueue,
  });
};

describe("runEmbeddedPiAgent", () => {
  it("handles prompt error paths without dropping user state", async () => {
    const sessionFile = nextSessionFile();
    const cfg = createEmbeddedPiRunnerOpenAiConfig(["mock-error"]);
    const sessionKey = nextSessionKey();
    runEmbeddedAttemptMock.mockResolvedValueOnce(
      makeEmbeddedRunnerAttempt({
        promptError: new Error("boom"),
      }),
    );
    await expect(
      runEmbeddedPiAgent({
        sessionId: "session:test",
        sessionKey,
        sessionFile,
        workspaceDir,
        config: cfg,
        prompt: "boom",
        provider: "openai",
        model: "mock-error",
        timeoutMs: 5_000,
        agentDir,
        runId: nextRunId("prompt-error"),
        enqueue: immediateEnqueue,
      }),
    ).rejects.toThrow("boom");

    try {
      const messages = await readSessionMessages(sessionFile);
      const userIndex = messages.findIndex(
        (message) => message?.role === "user" && textFromContent(message.content) === "boom",
      );
      expect(userIndex).toBeGreaterThanOrEqual(0);
    } catch (err) {
      if ((err as NodeJS.ErrnoException | undefined)?.code !== "ENOENT") {
        throw err;
      }
    }
  });

  it(
    "preserves existing transcript entries across an additional turn",
    { timeout: 7_000 },
    async () => {
      const sessionFile = nextSessionFile();
      const sessionKey = nextSessionKey();

      const sessionManager = SessionManager.open(sessionFile);
      sessionManager.appendMessage({
        role: "user",
        content: [{ type: "text", text: "seed user" }],
        timestamp: Date.now(),
      });
      sessionManager.appendMessage({
        role: "assistant",
        content: [{ type: "text", text: "seed assistant" }],
        stopReason: "stop",
        api: "openai-responses",
        provider: "openai",
        model: "mock-1",
        usage: createMockUsage(1, 1),
        timestamp: Date.now(),
      });

      await runDefaultEmbeddedTurn(sessionFile, "hello", sessionKey);

      const messages = await readSessionMessages(sessionFile);
      const seedUserIndex = messages.findIndex(
        (message) => message?.role === "user" && textFromContent(message.content) === "seed user",
      );
      const seedAssistantIndex = messages.findIndex(
        (message) =>
          message?.role === "assistant" && textFromContent(message.content) === "seed assistant",
      );
      expect(seedUserIndex).toBeGreaterThanOrEqual(0);
      expect(seedAssistantIndex).toBeGreaterThan(seedUserIndex);
      expect(messages.length).toBeGreaterThanOrEqual(2);
    },
  );

  it("repairs orphaned user messages and continues", async () => {
    const result = await runWithOrphanedSingleUserMessage("orphaned user", nextSessionKey());

    expect(result.meta.error).toBeUndefined();
    expect(result.payloads?.length ?? 0).toBeGreaterThan(0);
  });

  it("sanitizes user-facing text: strips final tags, collapses duplicates and rewrites prefixed errors when errorContext", () => {
    // Strip final tags
    expect(sanitizeUserFacingText("<final>Goodbye</final>")).toBe("Goodbye");
  
    // Collapse duplicate blocks and trim leading blank lines
    const withDuplicates = "\n\nBlock A\n\n\nBlock A\n\nBlock B\n";
    const sanitized = sanitizeUserFacingText(withDuplicates);
    expect(sanitized).toBe("Block A\n\nBlock B");
  
    // When errorContext is true and the text looks like a prefixed error that is overloaded,
    // the function should rewrite to the overloaded message copy.
    const prefixed = "Error 503: overloaded";
    const rewritten = sanitizeUserFacingText(prefixed, { errorContext: true });
    expect(rewritten).toBe("The AI service is temporarily overloaded. Please try again in a moment.");
  });


  it("formats transport errors and truncates long messages", () => {
    const base: any = {
      role: "assistant",
      content: [],
      stopReason: "error",
      api: "test-api",
      provider: "test-prov",
      model: "m",
      usage: { promptTokens: 0, completionTokens: 0, totalTokens: 0 },
      timestamp: Date.now(),
    };
    const makeMsg = (err: string) => ({ ...base, errorMessage: err });
  
    // Connection refused variants
    expect(
      formatAssistantErrorText(makeMsg("ECONNREFUSED: connect")),
    ).toBe("LLM request failed: connection refused by the provider endpoint.");
    expect(
      formatAssistantErrorText(makeMsg("connection refused by remote host")),
    ).toBe("LLM request failed: connection refused by the provider endpoint.");
  
    // Connection reset / socket hang up -> interrupted
    expect(
      formatAssistantErrorText(makeMsg("socket hang up while streaming")),
    ).toBe("LLM request failed: network connection was interrupted.");
    expect(
      formatAssistantErrorText(makeMsg("ECONNRESET occurred")),
    ).toBe("LLM request failed: network connection was interrupted.");
  
    // DNS lookup failure
    expect(
      formatAssistantErrorText(makeMsg("getaddrinfo ENOTFOUND api.example.com")),
    ).toBe("LLM request failed: DNS lookup for the provider endpoint failed.");
    expect(
      formatAssistantErrorText(makeMsg("no such host: api.example.com")),
    ).toBe("LLM request failed: DNS lookup for the provider endpoint failed.");
  
    // Network unreachable / host unreachable
    expect(
      formatAssistantErrorText(makeMsg("network is unreachable when connecting")),
    ).toBe("LLM request failed: the provider endpoint is unreachable from this host.");
    expect(
      formatAssistantErrorText(makeMsg("host is unreachable for api.example.com")),
    ).toBe("LLM request failed: the provider endpoint is unreachable from this host.");
  
    // Generic network fetch failed
    expect(
      formatAssistantErrorText(makeMsg("Fetch failed: network request failed")),
    ).toBe("LLM request failed: network connection error.");
  
    // Very long raw error should be truncated with an ellipsis
    const longRaw = "x".repeat(610);
    const longOut = formatAssistantErrorText(makeMsg(longRaw));
    expect(longOut).toBeDefined();
    // Should end with ellipsis and be 600 chars + ellipsis (601)
    expect(longOut?.endsWith("…")).toBeTruthy();
    expect(longOut?.length).toBe(601);
  });


  it("extracts observed overflow token counts from known patterns", () => {
    // Comma-separated thousands and plain numbers
    expect(
      extractObservedOverflowTokenCount("Prompt is too long: 1,234 tokens > 512 maximum"),
    ).toBe(1234);
    expect(extractObservedOverflowTokenCount("requested 42 tokens for completion")).toBe(42);
    expect(
      extractObservedOverflowTokenCount("resulted in 7,890 tokens processed by the model"),
    ).toBe(7890);
    // Zero or missing -> undefined
    expect(extractObservedOverflowTokenCount("requested 0 tokens")).toBeUndefined();
    expect(extractObservedOverflowTokenCount("nothing to see here")).toBeUndefined();
  });

});
