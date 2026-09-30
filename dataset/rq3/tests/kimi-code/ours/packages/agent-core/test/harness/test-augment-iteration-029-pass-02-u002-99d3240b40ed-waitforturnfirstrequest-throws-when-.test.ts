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


















  __testAugmentVitest_bbd9f3a8fa52.it("waitForTurnFirstRequest_throws_when_no_active_turn_round_029_pass_02", async () => {
    const { TurnFlow } = __testAugmentTarget_2d60f7d1800f;
    const records = { logRecord: __testAugmentVitest_bbd9f3a8fa52.vi.fn() };
    const agent = { homedir: undefined, type: 'x', records, telemetry: { track: () => {} } } as unknown as any;
    const flow = new TurnFlow(agent);

    // waitForTurnFirstRequest synchronously throws via ensureActiveTurn when no active turn
    __testAugmentVitest_bbd9f3a8fa52.expect(() => (flow as any).waitForTurnFirstRequest()).toThrowError('No active turn');
  });
});

import * as __testAugmentVitest_bbd9f3a8fa52 from "vitest";

import * as __testAugmentTarget_2d60f7d1800f from "../../src/agent/turn/index.js";

const __testAugmentLoadTarget_2d60f7d1800f = async () => {
  __testAugmentVitest_bbd9f3a8fa52.vi.doUnmock("../../src/agent/turn/index.js");
  __testAugmentVitest_bbd9f3a8fa52.vi.resetModules();
  return import("../../src/agent/turn/index.js");
};
