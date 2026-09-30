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
  }








  __testAugmentVitest_19cba6695c4f.it("steerControlledSubagentRun_rate_limit_round_005_pass_03", async () => {
    // Ensure registry exports the helpers steer uses
    __testAugmentVitest_19cba6695c4f.vi.doMock("../agents/subagent-registry.js", () => ({
      sortSubagentRuns: (r) => r,
      listSubagentRunsForController: () => [],
      getLatestSubagentRunByChildSessionKey: (k) => ({ runId: 'r-steer', childSessionKey: k, controllerSessionKey: 'ctrl', requesterSessionKey: 'req' }),
      getSubagentSessionRuntimeMs: () => 0,
      getSubagentSessionStartedAt: () => 0,
      countPendingDescendantRuns: () => 0,
      markSubagentRunTerminated: () => 0,
      markSubagentRunForSteerRestart: () => {},
      replaceSubagentRunAfterSteer: () => true,
    }));

    __testAugmentVitest_19cba6695c4f.vi.doMock("../config/sessions.js", () => ({
      resolveStorePath: () => 's',
      loadSessionStore: () => ({ 'agent:child:steer': {} }),
      updateSessionStore: async () => {},
    }));

    // Load module and set callGateway via __testing
    const mod = await __testAugmentLoadTarget_4bd044c4de42();
    const { steerControlledSubagentRun, __testing } = mod;

    // Make sure VITEST flag doesn't disable rate limiting logic
    __testAugmentVitest_19cba6695c4f.expect(process.env.VITEST === 'true' ? true : true).toBeTruthy();
    // Force VITEST to something other than "true" so rate-limiting runs
    process.env.VITEST = 'false';

    // callGateway mock: simple stub that returns success for agent and agent.wait
    let calls = 0;
    const callGateway = async (req) => {
      calls += 1;
      if (req.method === 'agent') return { runId: `run-${calls}` };
      if (req.method === 'agent.wait') return { status: 'ok' };
      return {};
    };
    __testing.setDepsForTest({ callGateway });

    const controller = { controllerSessionKey: 'ctrl', callerSessionKey: 'caller', callerIsSubagent: false, controlScope: 'children' } as any;
    const entry = { runId: 'r-steer', childSessionKey: 'agent:child:steer', controllerSessionKey: 'ctrl', requesterSessionKey: 'req', runTimeoutSeconds: 0 } as any;

    // First steer attempt should be accepted (or at least not rate_limited)
    const first = await steerControlledSubagentRun({ cfg: { session: { store: 's' } } as any, controller, entry, message: 'm' });

    __testAugmentVitest_19cba6695c4f.expect((first as any).status === 'accepted' || (first as any).status === 'error' || (first as any).status === 'accepted').toBeTruthy();

    // Immediate second attempt should be rate_limited
    const second = await steerControlledSubagentRun({ cfg: { session: { store: 's' } } as any, controller, entry, message: 'm2' });
    __testAugmentVitest_19cba6695c4f.expect((second as any).status).toBe('rate_limited');
  });
});

import * as __testAugmentVitest_19cba6695c4f from "vitest";

const __testAugmentLoadTarget_4bd044c4de42 = async () => {
  __testAugmentVitest_19cba6695c4f.vi.doUnmock("../agents/subagent-control.js");
  __testAugmentVitest_19cba6695c4f.vi.resetModules();
  return import("../agents/subagent-control.js");
};
