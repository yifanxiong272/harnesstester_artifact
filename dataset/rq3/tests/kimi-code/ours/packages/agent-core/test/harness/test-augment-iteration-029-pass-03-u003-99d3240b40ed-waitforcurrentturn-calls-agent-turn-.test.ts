import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'pathe';

import { APIConnectionError, APIStatusError, type ProviderConfig } from '@moonshot-ai/kosong';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ProviderManager } from '../../src/session/provider-manager';
import type { AgentOptions } from '../../src/agent';
import type { KimiConfig } from '../../src/config';
import { ErrorCodes, KimiError } from '../../src/errors';
import type { HookDef } from '../../src/session/hooks';
import type { ResolvedAgentProfile } from '../../src/profile';
import type { SDKSessionRPC } from '../../src/rpc';
import { Session } from '../../src/session';
import { SessionAPIImpl } from '../../src/session/rpc';
import { createScriptedGenerate } from '../agent/harness/scripted-generate';
import { testKaos } from '../fixtures/test-kaos';

const MOCK_PROVIDER = { type: 'kimi', apiKey: 'test-key', model: 'mock-model' } as const satisfies ProviderConfig;

const tempDirs: string[] = [];
const openSessions: Session[] = [];

function track(session: Session): Session {
  openSessions.push(session);
  return session;
}

afterEach(async () => {
  // Close sessions first so their async metadata/wire writes settle before the
  // temp dirs are removed (otherwise rm races with a write -> ENOTEMPTY).
  await Promise.allSettled(openSessions.splice(0).map((s) => s.close()));
  for (const dir of tempDirs.splice(0)) {
    await rm(dir, { recursive: true, force: true });
  }
});

async function makeTempDir(): Promise<string> {
  const dir = await mkdtemp(join(tmpdir(), 'kimi-goal-session-'));
  tempDirs.push(dir);
  return dir;
}

function testProviderManager(): ProviderManager {
  return new ProviderManager({
    config: {
      providers: { test: { type: MOCK_PROVIDER.type, apiKey: MOCK_PROVIDER.apiKey } },
      models: { [MOCK_PROVIDER.model]: { provider: 'test', model: MOCK_PROVIDER.model, maxContextSize: 1_000_000 } },
    },
  });
}

function goalProfile(tools: readonly string[]): ResolvedAgentProfile {
  return { name: 'test', systemPrompt: () => '<system-prompt>', tools: [...tools] };
}

function createSessionRpc(events: Array<Record<string, unknown>>): SDKSessionRPC {
  return {
    emitEvent: vi.fn(async (event) => {
      events.push(event);
    }),
    requestApproval: vi.fn(async () => ({ decision: 'approved', selectedLabel: 'approve' })),
    requestQuestion: vi.fn(async () => null),
    toolCall: vi.fn(async () => ({ output: '', isError: true })),
  } as unknown as SDKSessionRPC;
}

async function readWireRecords(sessionDir: string): Promise<Array<Record<string, unknown>>> {
  const wire = await readFile(join(sessionDir, 'agents', 'main', 'wire.jsonl'), 'utf-8');
  return wire
    .split('\n')
    .filter((line) => line.trim().length > 0)
    .map((line) => JSON.parse(line) as Record<string, unknown>);
}

async function setupSession(
  sessionDir: string,
  events: Array<Record<string, unknown>>,
  tools: readonly string[],
  generate?: NonNullable<AgentOptions['generate']>,
  hooks?: readonly HookDef[],
  config?: KimiConfig,
) {
  const scripted = createScriptedGenerate();
  const session = track(
    new Session({
      id: 'goal-session',
      kaos: testKaos.withCwd(sessionDir),
      homedir: sessionDir,
      rpc: createSessionRpc(events),
      skills: { explicitDirs: [join(sessionDir, 'missing')] },
      providerManager: testProviderManager(),
      hooks,
      config,
    }),
  );
  const { agent } = await session.createAgent(
    { type: 'main', generate: generate ?? scripted.generate },
    { profile: goalProfile(tools) },
  );
  agent.config.update({ modelAlias: 'mock-model', thinkingLevel: 'off' });
  agent.permission.setMode('yolo');
  return { session, agent, scripted };
}

describe('goal session end-to-end', () => {


















  __testAugmentVitest_bbd9f3a8fa52.it("waitForCurrentTurn_calls_agent_turn_cancel_on_abort_round_029_pass_03", async () => {
    const { TurnFlow } = __testAugmentTarget_2d60f7d1800f;
    const logRecord = __testAugmentVitest_bbd9f3a8fa52.vi.fn();
    const cancelSpy = __testAugmentVitest_bbd9f3a8fa52.vi.fn();
    const agent = { homedir: undefined, type: 'x', records: { logRecord }, telemetry: { track: () => {} }, turn: { cancel: cancelSpy } } as unknown as any;
    const flow = new TurnFlow(agent);

    // Make a non-resolving active turn and set the flow's current id used by waitForCurrentTurn
    (flow as any).activeTurn = { turnId: 7, controller: { abort: () => {} }, promise: new Promise(() => {}), firstRequest: { resolve: () => {} } };
    (flow as any).turnId = 123;

    const ac = new AbortController();
    const promise = flow.waitForCurrentTurn(ac.signal).catch(() => undefined);
    // Abort with a reason and allow the abort handler to run
    // AbortController.abort accepts a reason in modern runtimes
    // Use a simple string as the reason for assertion
    try {
      (ac as any).abort('sig-reason');
    } catch (e) {
      // Some runtimes may not accept a reason argument; if so, call abort() only.
      ac.abort();
    }
    await promise;

    // waitForCurrentTurn registers an onAbort that calls agent.turn.cancel with the flow.currentId
    __testAugmentVitest_bbd9f3a8fa52.expect(cancelSpy).toHaveBeenCalled();
    const calledWith = cancelSpy.mock.calls[0];
    __testAugmentVitest_bbd9f3a8fa52.expect(calledWith[0]).toBe(123);
    // Reason may be undefined on older runtimes; ensure the call happened and the second arg exists (possibly undefined)
    __testAugmentVitest_bbd9f3a8fa52.expect(calledWith.length).toBeGreaterThanOrEqual(2);
  });
});

import * as __testAugmentVitest_bbd9f3a8fa52 from "vitest";

import * as __testAugmentTarget_2d60f7d1800f from "../../src/agent/turn/index.js";

const __testAugmentLoadTarget_2d60f7d1800f = async () => {
  __testAugmentVitest_bbd9f3a8fa52.vi.doUnmock("../../src/agent/turn/index.js");
  __testAugmentVitest_bbd9f3a8fa52.vi.resetModules();
  return import("../../src/agent/turn/index.js");
};
