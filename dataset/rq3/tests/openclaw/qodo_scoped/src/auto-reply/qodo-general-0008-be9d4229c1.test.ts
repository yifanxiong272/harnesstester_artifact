import fs from "node:fs/promises";
import { join } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { loadSessionStore, resolveSessionKey } from "../config/sessions.js";
import { registerGroupIntroPromptCases } from "./reply.triggers.group-intro-prompts.cases.js";
import { registerTriggerHandlingUsageSummaryCases } from "./reply.triggers.trigger-handling.filters-usage-summary-current-model-provider.cases.js";
import {
  expectInlineCommandHandledAndStripped,
  getAbortEmbeddedPiRunMock,
  getCompactEmbeddedPiSessionMock,
  getRunEmbeddedPiAgentMock,
  installTriggerHandlingReplyHarness,
  MAIN_SESSION_KEY,
  makeCfg,
  mockRunEmbeddedPiAgentOk,
  requireSessionStorePath,
  runGreetingPromptForBareNewOrReset,
  withTempHome,
} from "./reply.triggers.trigger-handling.test-harness.js";
import { enqueueFollowupRun, getFollowupQueueDepth, type FollowupRun } from "./reply/queue.js";
import { HEARTBEAT_TOKEN } from "./tokens.js";
import { buildHelpMessage } from "./status.js";
import { buildCommandsMessagePaginated } from "./status.js";
import { buildToolsMessage } from "./status.js";
import { buildStatusMessage } from "./status.js";

type GetReplyFromConfig = typeof import("./reply.js").getReplyFromConfig;

vi.mock("./reply/agent-runner.runtime.js", () => ({
  runReplyAgent: async (params: {
    commandBody: string;
    followupRun: {
      run: {
        provider: string;
        model: string;
        sessionId: string;
        sessionKey?: string;
        sessionFile: string;
        workspaceDir: string;
        config: object;
        extraSystemPrompt?: string;
      };
    };
  }) => {
    const runEmbeddedPiAgentMock = getRunEmbeddedPiAgentMock();
    const normalizeErrorText = (message: string) => {
      if (/context window exceeded/i.test(message)) {
        return "⚠️ Context overflow — prompt too large for this model. Try a shorter message or a larger-context model.";
      }
      const trimmed = message.replace(/\.\s*$/, "");
      return `⚠️ Agent failed before reply: ${trimmed}.\nLogs: openclaw logs --follow`;
    };
    const stripHeartbeat = (text?: string) => {
      const trimmed = text?.trim();
      if (!trimmed || trimmed === HEARTBEAT_TOKEN) {
        return undefined;
      }
      return trimmed.startsWith(`${HEARTBEAT_TOKEN} `)
        ? trimmed.slice(HEARTBEAT_TOKEN.length).trimStart()
        : trimmed;
    };

    try {
      const result = await runEmbeddedPiAgentMock({
        prompt: params.commandBody,
        provider: params.followupRun.run.provider,
        model: params.followupRun.run.model,
        sessionId: params.followupRun.run.sessionId,
        sessionKey: params.followupRun.run.sessionKey,
        sessionFile: params.followupRun.run.sessionFile,
        workspaceDir: params.followupRun.run.workspaceDir,
        config: params.followupRun.run.config,
        extraSystemPrompt: params.followupRun.run.extraSystemPrompt,
      });
      return { text: stripHeartbeat(result?.payloads?.[0]?.text) };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return { text: normalizeErrorText(message) };
    }
  },
}));

let getReplyFromConfig!: GetReplyFromConfig;
installTriggerHandlingReplyHarness((impl) => {
  getReplyFromConfig = impl;
});

const BASE_MESSAGE = {
  Body: "hello",
  From: "+1002",
  To: "+2000",
} as const;

function maybeReplyText(reply: Awaited<ReturnType<GetReplyFromConfig>>) {
  return Array.isArray(reply) ? reply[0]?.text : reply?.text;
}

function mockEmbeddedOkPayload() {
  return mockRunEmbeddedPiAgentOk("ok");
}

async function writeStoredModelOverride(cfg: ReturnType<typeof makeCfg>): Promise<void> {
  await fs.writeFile(
    requireSessionStorePath(cfg),
    JSON.stringify({
      [MAIN_SESSION_KEY]: {
        sessionId: "main",
        updatedAt: Date.now(),
        providerOverride: "openai",
        modelOverride: "gpt-5.2",
      },
    }),
    "utf-8",
  );
}

function mockSuccessfulCompaction() {
  getCompactEmbeddedPiSessionMock().mockResolvedValue({
    ok: true,
    compacted: true,
    result: {
      summary: "summary",
      firstKeptEntryId: "x",
      tokensBefore: 12000,
    },
  });
}

function makeUnauthorizedWhatsAppCfg(home: string) {
  const baseCfg = makeCfg(home);
  return {
    ...baseCfg,
    channels: {
      ...baseCfg.channels,
      whatsapp: {
        allowFrom: ["+1000"],
      },
    },
  };
}

async function expectResetBlockedForNonOwner(params: { home: string }): Promise<void> {
  const { home } = params;
  const runEmbeddedPiAgentMock = getRunEmbeddedPiAgentMock();
  runEmbeddedPiAgentMock.mockClear();
  const cfg = makeCfg(home);
  cfg.channels ??= {};
  cfg.channels.whatsapp = {
    ...cfg.channels.whatsapp,
    allowFrom: ["+1999"],
  };
  cfg.commands = {
    ...cfg.commands,
    ownerAllowFrom: ["whatsapp:+1999"],
  };
  cfg.session = {
    ...cfg.session,
    store: join(home, "blocked-reset.sessions.json"),
  };
  const res = await getReplyFromConfig(
    {
      Body: "/reset",
      From: "+1003",
      To: "+2000",
      CommandAuthorized: false,
    },
    {},
    cfg,
  );
  expect(res).toBeUndefined();
  expect(runEmbeddedPiAgentMock).not.toHaveBeenCalled();
}

function mockEmbeddedOk() {
  return mockRunEmbeddedPiAgentOk("ok");
}

async function runInlineUnauthorizedCommand(params: { home: string; command: "/status" }) {
  const cfg = makeUnauthorizedWhatsAppCfg(params.home);
  const res = await getReplyFromConfig(
    {
      Body: `please ${params.command} now`,
      From: "+2001",
      To: "+2000",
      Provider: "whatsapp",
      SenderE164: "+2001",
    },
    {},
    cfg,
  );
  return res;
}

describe("trigger handling", () => {
  registerGroupIntroPromptCases();
  registerTriggerHandlingUsageSummaryCases({
    getReplyFromConfig: () => getReplyFromConfig,
  });

  for (const testCase of [
    {
      error: "sandbox is not defined.",
      expected:
        "⚠️ Agent failed before reply: sandbox is not defined.\nLogs: openclaw logs --follow",
    },
    {
      error: "Context window exceeded",
      expected:
        "⚠️ Context overflow — prompt too large for this model. Try a shorter message or a larger-context model.",
    },
  ] as const) {
    it(`surfaces agent error: ${testCase.error}`, async () => {
      await withTempHome(async (home) => {
        const runEmbeddedPiAgentMock = getRunEmbeddedPiAgentMock();
        runEmbeddedPiAgentMock.mockReset();
        runEmbeddedPiAgentMock.mockImplementation(async () => {
          throw new Error(testCase.error);
        });
        const errorRes = await getReplyFromConfig(BASE_MESSAGE, {}, makeCfg(home));
        expect(maybeReplyText(errorRes), testCase.error).toBe(testCase.expected);
        expect(runEmbeddedPiAgentMock, testCase.error).toHaveBeenCalledOnce();
      });
    });
  }

  it("strips heartbeat-only replies and preserves normal text", async () => {
    await withTempHome(async (home) => {
      const runEmbeddedPiAgentMock = getRunEmbeddedPiAgentMock();
      const tokenCases = [
        { text: HEARTBEAT_TOKEN, expected: undefined },
        { text: `${HEARTBEAT_TOKEN} hello`, expected: "hello" },
      ] as const;

      for (const testCase of tokenCases) {
        runEmbeddedPiAgentMock.mockReset();
        runEmbeddedPiAgentMock.mockResolvedValue({
          payloads: [{ text: testCase.text }],
          meta: {
            durationMs: 1,
            agentMeta: { sessionId: "s", provider: "p", model: "m" },
          },
        });
        const res = await getReplyFromConfig(BASE_MESSAGE, {}, makeCfg(home));
        expect(maybeReplyText(res)).toBe(testCase.expected);
        expect(runEmbeddedPiAgentMock).toHaveBeenCalledOnce();
      }
    });
  });

  it("sanitizes thinking directives before the agent run", async () => {
    await withTempHome(async (home) => {
      const thinkCases = [
        {
          label: "context-wrapper",
          request: {
            Body: [
              "[Chat messages since your last reply - for context]",
              "Peter: /thinking high [2025-12-05T21:45:00.000Z]",
              "",
              "[Current message - respond to this]",
              "Give me the status",
            ].join("\n"),
            From: "+1002",
            To: "+2000",
          },
          options: {},
          assertPrompt: true,
        },
        {
          label: "heartbeat",
          request: {
            Body: "HEARTBEAT /think:high",
            From: "+1003",
            To: "+1003",
          },
          options: { isHeartbeat: true },
          assertPrompt: false,
        },
      ] as const;

      for (const testCase of thinkCases) {
        const runEmbeddedPiAgentMock = getRunEmbeddedPiAgentMock();
        runEmbeddedPiAgentMock.mockReset();
        mockRunEmbeddedPiAgentOk();
        const res = await getReplyFromConfig(testCase.request, testCase.options, makeCfg(home));
        const text = maybeReplyText(res);
        expect(text, testCase.label).toBe("ok");
        expect(text, testCase.label).not.toMatch(/Thinking level set/i);
        expect(runEmbeddedPiAgentMock, testCase.label).toHaveBeenCalledOnce();
        if (testCase.assertPrompt) {
          const prompt = runEmbeddedPiAgentMock.mock.calls[0]?.[0]?.prompt ?? "";
          expect(prompt).toContain("Give me the status");
          expect(prompt).not.toContain("/thinking high");
          expect(prompt).not.toContain("/think high");
        }
      }
    });
  });

  it("resolves heartbeat model selection from overrides", async () => {
    await withTempHome(async (home) => {
      const modelCases = [
        {
          label: "heartbeat-override",
          setup: (cfg: ReturnType<typeof makeCfg>) => {
            cfg.agents = {
              ...cfg.agents,
              defaults: {
                ...cfg.agents?.defaults,
                heartbeat: { model: "anthropic/claude-haiku-4-5-20251001" },
              },
            };
          },
          expected: { provider: "anthropic", model: "claude-haiku-4-5-20251001" },
        },
        {
          label: "stored-override",
          setup: () => undefined,
          expected: { provider: "openai", model: "gpt-5.2" },
        },
      ] as const;

      for (const testCase of modelCases) {
        const runEmbeddedPiAgentMock = getRunEmbeddedPiAgentMock();
        runEmbeddedPiAgentMock.mockReset();
        mockEmbeddedOkPayload();
        const cfg = makeCfg(home);
        cfg.session = { ...cfg.session, store: join(home, `${testCase.label}.sessions.json`) };
        await writeStoredModelOverride(cfg);
        testCase.setup(cfg);
        await getReplyFromConfig(BASE_MESSAGE, { isHeartbeat: true }, cfg);

        const call = runEmbeddedPiAgentMock.mock.calls[0]?.[0];
        expect(call?.provider).toBe(testCase.expected.provider);
        expect(call?.model).toBe(testCase.expected.model);
      }
    });
  });

  it("compacts the active main session", async () => {
    await withTempHome(async (home) => {
      const storePath = join(home, "compact-main.sessions.json");
      const cfg = makeCfg(home);
      cfg.session = { ...cfg.session, store: storePath };
      mockSuccessfulCompaction();

      const request = {
        Body: "/compact focus on decisions",
        From: "+1003",
        To: "+2000",
      };

      const res = await getReplyFromConfig(
        {
          ...request,
          CommandAuthorized: true,
        },
        {},
        cfg,
      );
      const text = maybeReplyText(res);
      expect(text?.startsWith("⚙️ Compacted")).toBe(true);
      expect(getCompactEmbeddedPiSessionMock()).toHaveBeenCalledOnce();
      const store = loadSessionStore(storePath);
      const sessionKey = resolveSessionKey("per-sender", request);
      expect(store[sessionKey]?.compactionCount).toBe(1);
    });
  });

  it("compacts worker sessions via the agent session file", async () => {
    await withTempHome(async (home) => {
      getCompactEmbeddedPiSessionMock().mockReset();
      mockSuccessfulCompaction();
      const cfg = makeCfg(home);
      cfg.session = { ...cfg.session, store: join(home, "compact-worker.sessions.json") };
      const res = await getReplyFromConfig(
        {
          Body: "/compact",
          From: "+1004",
          To: "+2000",
          SessionKey: "agent:worker1:telegram:12345",
          CommandAuthorized: true,
        },
        {},
        cfg,
      );

      const text = maybeReplyText(res);
      expect(text?.startsWith("⚙️ Compacted")).toBe(true);
      expect(getCompactEmbeddedPiSessionMock()).toHaveBeenCalledOnce();
      expect(getCompactEmbeddedPiSessionMock().mock.calls[0]?.[0]?.sessionFile).toContain(
        join("agents", "worker1", "sessions"),
      );
    });
  });

  it("aborts native target sessions and clears queued followups", async () => {
    await withTempHome(async (home) => {
      const cfg = makeCfg(home);
      cfg.session = { ...cfg.session, store: join(home, "native-stop.sessions.json") };
      getAbortEmbeddedPiRunMock().mockReset().mockReturnValue(false);
      const storePath = cfg.session?.store;
      if (!storePath) {
        throw new Error("missing session store path");
      }
      const targetSessionKey = "agent:main:telegram:group:123";
      const targetSessionId = "session-target";
      await fs.writeFile(
        storePath,
        JSON.stringify({
          [targetSessionKey]: {
            sessionId: targetSessionId,
            updatedAt: Date.now(),
          },
        }),
      );
      const followupRun: FollowupRun = {
        prompt: "queued",
        enqueuedAt: Date.now(),
        run: {
          agentId: "main",
          agentDir: join(home, "agent"),
          sessionId: targetSessionId,
          sessionKey: targetSessionKey,
          messageProvider: "telegram",
          agentAccountId: "acct",
          sessionFile: join(home, "session.jsonl"),
          workspaceDir: join(home, "workspace"),
          config: cfg,
          provider: "anthropic",
          model: "claude-opus-4-5",
          timeoutMs: 10,
          blockReplyBreak: "text_end",
        },
      };
      enqueueFollowupRun(
        targetSessionKey,
        followupRun,
        { mode: "collect", debounceMs: 0, cap: 20, dropPolicy: "summarize" },
        "none",
      );
      expect(getFollowupQueueDepth(targetSessionKey)).toBe(1);

      const res = await getReplyFromConfig(
        {
          Body: "/stop",
          From: "telegram:111",
          To: "telegram:111",
          ChatType: "direct",
          Provider: "telegram",
          Surface: "telegram",
          SessionKey: "telegram:slash:111",
          CommandSource: "native",
          CommandTargetSessionKey: targetSessionKey,
          CommandAuthorized: true,
        },
        {},
        cfg,
      );

      const text = Array.isArray(res) ? res[0]?.text : res?.text;
      expect(text).toBe("⚙️ Agent was aborted.");
      expect(getAbortEmbeddedPiRunMock()).toHaveBeenCalledWith(targetSessionId);
      const store = loadSessionStore(storePath);
      expect(store[targetSessionKey]?.abortedLastRun).toBe(true);
      expect(getFollowupQueueDepth(targetSessionKey)).toBe(0);
    });
  });

  it("applies native model changes to the target session", async () => {
    await withTempHome(async (home) => {
      const cfg = makeCfg(home);
      cfg.session = { ...cfg.session, store: join(home, "native-model.sessions.json") };
      const runEmbeddedPiAgentMock = getRunEmbeddedPiAgentMock();
      runEmbeddedPiAgentMock.mockReset();
      const storePath = cfg.session?.store;
      if (!storePath) {
        throw new Error("missing session store path");
      }
      const slashSessionKey = "telegram:slash:111";
      const targetSessionKey = MAIN_SESSION_KEY;

      await fs.writeFile(
        storePath,
        JSON.stringify({
          [targetSessionKey]: {
            sessionId: "session-target",
            updatedAt: Date.now(),
          },
        }),
      );

      const res = await getReplyFromConfig(
        {
          Body: "/model openai/gpt-4.1-mini",
          From: "telegram:111",
          To: "telegram:111",
          ChatType: "direct",
          Provider: "telegram",
          Surface: "telegram",
          SessionKey: slashSessionKey,
          CommandSource: "native",
          CommandTargetSessionKey: targetSessionKey,
          CommandAuthorized: true,
        },
        {},
        cfg,
      );

      const text = Array.isArray(res) ? res[0]?.text : res?.text;
      expect(text).toContain("Model set to openai/gpt-4.1-mini");

      const store = loadSessionStore(storePath);
      expect(store[targetSessionKey]?.providerOverride).toBe("openai");
      expect(store[targetSessionKey]?.modelOverride).toBe("gpt-4.1-mini");
      expect(store[slashSessionKey]).toBeUndefined();

      runEmbeddedPiAgentMock.mockReset();
      runEmbeddedPiAgentMock.mockResolvedValue({
        payloads: [{ text: "ok" }],
        meta: {
          durationMs: 5,
          agentMeta: { sessionId: "s", provider: "p", model: "m" },
        },
      });

      await getReplyFromConfig(
        {
          Body: "hi",
          From: "telegram:111",
          To: "telegram:111",
          ChatType: "direct",
          Provider: "telegram",
          Surface: "telegram",
        },
        {},
        cfg,
      );

      expect(runEmbeddedPiAgentMock).toHaveBeenCalledOnce();
      expect(runEmbeddedPiAgentMock.mock.calls[0]?.[0]).toEqual(
        expect.objectContaining({
          provider: "openai",
          model: "gpt-4.1-mini",
        }),
      );
    });
  });

  it("handles bare session reset, inline commands, and unauthorized inline status", async () => {
    await withTempHome(async (home) => {
      await runGreetingPromptForBareNewOrReset({ home, body: "/new", getReplyFromConfig });
      await expectResetBlockedForNonOwner({ home });
      await expectInlineCommandHandledAndStripped({
        home,
        getReplyFromConfig,
        body: "please /whoami now",
        stripToken: "/whoami",
        blockReplyContains: "Identity",
        requestOverrides: { SenderId: "12345" },
      });
      const inlineRunEmbeddedPiAgentMock = mockEmbeddedOk();
      const res = await runInlineUnauthorizedCommand({
        home,
        command: "/status",
      });
      const text = Array.isArray(res) ? res[0]?.text : res?.text;
      expect(text).toBe("ok");
      expect(inlineRunEmbeddedPiAgentMock).toHaveBeenCalled();
      const prompt = inlineRunEmbeddedPiAgentMock.mock.calls.at(-1)?.[0]?.prompt ?? "";
      expect(prompt).toContain("/status");
    });
  });

  it("buildHelpMessage contains core help sections", () => {
    const help = buildHelpMessage();
    expect(help).toContain("ℹ️ Help");
    expect(help).toContain("Session");
    expect(help).toContain("Options");
    expect(help).toContain("Status");
    expect(help).toContain("Skills");
    expect(help).toContain("More: /commands for full list, /tools for available capabilities");
  });


  it("buildCommandsMessagePaginated returns telegram pagination structure", () => {
    // Request telegram surface to trigger paginated output
    const result = buildCommandsMessagePaginated(undefined, [], { page: 1, surface: "telegram" });
    expect(result).toHaveProperty("text");
    // Header includes ℹ️ Commands (current/total)
    expect(result.text).toMatch(/ℹ️ Commands \(\d+\/\d+\)/);
    // metadata fields are present and sensible
    expect(typeof result.totalPages).toBe("number");
    expect(typeof result.currentPage).toBe("number");
    expect(typeof result.hasNext).toBe("boolean");
    expect(typeof result.hasPrev).toBe("boolean");
    // current page should be within 1..totalPages
    expect(result.currentPage).toBeGreaterThanOrEqual(1);
    expect(result.currentPage).toBeLessThanOrEqual(Math.max(1, result.totalPages));
  });


  it("buildToolsMessage shows no tools and lists tools in verbose and compact modes", () => {
    // Empty groups -> no-tools fallback
    const empty = buildToolsMessage({ groups: [], profile: "test-profile" } as any);
    expect(empty).toContain("No tools are available for this agent right now.");
    expect(empty).toContain("Profile: test-profile");
  
    // Compact mode: plugin and channel tools should include their ids in parentheses
    const compact = buildToolsMessage(
      {
        profile: "compact-profile",
        groups: [
          {
            label: "Group One",
            tools: [
              { id: "tool-a", label: "Tool A", description: "Desc A", rawDescription: "Raw A", source: "plugin", pluginId: "pl1" },
              { id: "tool-b", label: "Tool B", description: "Desc B", rawDescription: "Raw B", source: "channel", channelId: "ch1" },
              { id: "tool-c", label: "Tool C", description: "Desc C", rawDescription: "Raw C", source: "local" },
            ],
          },
        ],
      } as any,
      { verbose: false },
    );
    expect(compact).toContain("Available tools");
    expect(compact).toContain("Group One");
    // plugin -> "tool-a (pl1)"
    expect(compact).toContain("tool-a (pl1)");
    // channel -> "tool-b (ch1)"
    expect(compact).toContain("tool-b (ch1)");
    // local -> just id shown
    expect(compact).toContain("tool-c");
  
    // Verbose mode: show descriptive lines with " - "
    const verbose = buildToolsMessage(
      {
        profile: "verbose-profile",
        groups: [
          {
            label: "Group Verbose",
            tools: [
              { id: "tool-x", label: "Tool X", description: "Desc X", rawDescription: "Raw X", source: "plugin", pluginId: "p-x" },
            ],
          },
        ],
      } as any,
      { verbose: true },
    );
    expect(verbose).toContain("What this agent can use right now:");
    // verbose should include human friendly name and the raw/fallback description
    expect(verbose).toContain("Tool X - Raw X");
  });


  it("buildStatusMessage includes detailed queue and cache and media lines", () => {
    const now = Date.now();
    const msg = buildStatusMessage({
      agent: {},
      sessionEntry: {
        sessionId: "s1",
        updatedAt: now - 1000,
        // input/output tokens and cache entries to drive cache line formatting
        inputTokens: 10,
        outputTokens: 5,
        cacheRead: 2,
        cacheWrite: 3,
        totalTokens: 15,
        chatType: "direct",
      },
      sessionKey: "user:1",
      // showDetails true forces the verbose queue details branch
      queue: {
        mode: "collect",
        depth: 3,
        debounceMs: 1500, // should format to 1.5s
        cap: 10,
        dropPolicy: "summarize",
        showDetails: true,
      },
      // mixed media decisions to exercise success, none and skipped branches
      mediaDecisions: [
        {
          capability: "caption",
          outcome: "success",
          // two attachments (count label x2) where one is chosen including provider/model
          attachments: [
            { chosen: { provider: "openai", model: "gpt-test" } },
            { /* other attachment */ },
          ],
        },
        {
          capability: "oac",
          outcome: "no-attachment",
          attachments: [],
        },
        {
          capability: "vision",
          outcome: "skipped",
          attachments: [
            {
              attempts: [{ reason: "quota: limit reached" }],
            },
          ],
        },
      ],
      now,
    });
  
    // Queue details: mode and formatted details
    expect(msg).toContain("Queue: collect (depth 3 · debounce 1.5s · cap 10 · drop summarize)");
    // Cache line: hit rate should be round((2 / (2+3+10)) * 100) => 13%
    expect(msg).toContain("🗄️ Cache: 13% hit · 2 cached, 3 new");
    // Media summary header and parts
    expect(msg).toContain("📎 Media:");
    expect(msg).toContain("caption x2 ok (openai/gpt-test)");
    // Skipped reason trimmed to short reason (before ':')
    expect(msg).toContain("vision skipped (quota)");
  });


  it("buildToolsMessage verbose shows tool names and descriptions", () => {
    const result = buildToolsMessage(
      {
        profile: "p",
        groups: [
          {
            label: "Group A",
            tools: [
              {
                id: "tool-1",
                label: "One",
                description: "A tool",
                rawDescription: "Raw desc of A",
                source: "plugin",
                pluginId: "plug-1",
              },
              {
                id: "tool-2",
                label: "Two",
                description: "Another tool",
                rawDescription: "",
                source: "channel",
                channelId: "chan-1",
              },
            ],
          },
        ],
      } as any,
      { verbose: true },
    );
  
    expect(result).toEqual(expect.stringContaining("Available tools"));
    // verbose mode should include the tool label and some form of description text
    expect(result).toEqual(expect.stringContaining("One -"));
    expect(result).toEqual(expect.stringContaining("Two -"));
    // profile is included
    expect(result).toEqual(expect.stringContaining("Profile: p"));
  });


  it("buildToolsMessage returns placeholder when no tools are available", () => {
    const res = buildToolsMessage({
      profile: "test-profile",
      groups: [],
    } as any);
    expect(res).toEqual(expect.stringContaining("No tools are available for this agent right now."));
    expect(res).toEqual(expect.stringContaining("Profile: test-profile"));
  });


  it("buildStatusMessage includes cache and media information", () => {
    const now = Date.now();
    const msg = buildStatusMessage({
      agent: {},
      sessionEntry: {
        sessionId: "sess1",
        updatedAt: now - 5000,
        chatType: "direct",
        inputTokens: 100,
        outputTokens: 40,
        cacheRead: 10,
        cacheWrite: 5,
        totalTokens: 150,
        compactionCount: 2,
      },
      sessionKey: "user:1",
      mediaDecisions: [
        {
          capability: "vision",
          outcome: "success",
          attachments: [
            {
              chosen: { provider: "openai", model: "gpt-4" },
              attempts: [],
            },
          ],
        },
        {
          capability: "audio",
          outcome: "skipped",
          attachments: [
            {
              attempts: [{ reason: "quota: limit reached" }],
            },
          ],
        },
      ],
      usageLine: "extra-usage",
      timeLine: "time-line",
      subagentsLine: "subagents",
      now,
    });
  
    // Should include cache summary line (hit / cached / new)
    expect(msg).toEqual(expect.stringContaining("🗄️ Cache:"));
    expect(msg).toEqual(expect.stringContaining("cached"));
    expect(msg).toEqual(expect.stringContaining("new"));
  
    // Media decisions should be summarized
    expect(msg).toEqual(expect.stringContaining("📎 Media:"));
    expect(msg).toEqual(expect.stringContaining("vision"));
    expect(msg).toEqual(expect.stringContaining("audio skipped"));
  
    // Basic structural pieces should be present
    expect(msg).toEqual(expect.stringContaining("Session:"));
    expect(msg).toEqual(expect.stringContaining("Context:"));
    expect(msg).toEqual(expect.stringContaining("🧠 Model:"));
  });

});
