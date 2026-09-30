import { mkdtemp, mkdir, readFile, realpath, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'pathe';
import { setTimeout as delay } from 'node:timers/promises';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  createRPC,
  KimiCore,
  type ApprovalResponse,
  type CoreAPI,
  type CoreRPC,
  type Event,
  type SDKAPI,
  type TelemetryClient,
} from '../../src';
import {
  recordingContextTelemetry,
  type TelemetryContextRecord,
} from '../fixtures/telemetry';

describe('HarnessAPI session skills', () => {
  let tmp: string;
  let homeDir: string;
  let workDir: string;

  beforeEach(async () => {
    tmp = await mkdtemp(join(tmpdir(), 'kimi-core-skills-'));
    homeDir = join(tmp, 'home');
    workDir = join(tmp, 'work');
    await mkdir(workDir, { recursive: true });
  });

  afterEach(async () => {
    await rm(tmp, { recursive: true, force: true });
    vi.unstubAllEnvs();
  });
















  async function writeSkill(name: string, lines: readonly string[]): Promise<void> {
    const dir = join(workDir, '.kimi-code', 'skills', name);
    await mkdir(dir, { recursive: true });
    await writeFile(join(dir, 'SKILL.md'), lines.join('\n'));
  }

  async function writeLegacyUserSkill(
    userHomeDir: string,
    name: string,
    description: string,
  ): Promise<void> {
    await writeSkillFile(join(userHomeDir, '.kimi-code', 'skills', name), name, description);
  }

  async function writeBrandUserSkill(
    brandHomeDir: string,
    name: string,
    description: string,
  ): Promise<void> {
    await writeSkillFile(join(brandHomeDir, 'skills', name), name, description);
  }

  async function writeSkillFile(dir: string, name: string, description: string): Promise<void> {
    await mkdir(dir, { recursive: true });
    await writeFile(
      join(dir, 'SKILL.md'),
      ['---', `name: ${name}`, `description: ${description}`, '---', '', `${description}.`].join(
        '\n',
      ),
    );
  }

  async function writeFlatSkill(name: string, lines: readonly string[]): Promise<void> {
    const dir = join(workDir, '.kimi-code', 'skills');
    await mkdir(dir, { recursive: true });
    await writeFile(join(dir, `${name}.md`), lines.join('\n'));
  }

  async function createTestRpc(options?: {
    readonly homeDir?: string;
    readonly telemetry?: TelemetryClient;
  }): Promise<{
    core: KimiCore;
    events: Event[];
    rpc: CoreRPC;
  }> {
    const [coreRpc, sdkRpc] = createRPC<CoreAPI, SDKAPI>();
    const events: Event[] = [];
    const configuredHomeDir = options === undefined ? homeDir : options.homeDir;
    const core = new KimiCore(
      coreRpc,
      { homeDir: configuredHomeDir, telemetry: options?.telemetry },
    );
    const rpc = await sdkRpc({
      emitEvent: (event) => {
        events.push(event);
      },
      requestApproval: vi.fn(async (): Promise<ApprovalResponse> => ({ decision: 'rejected' })),
      requestQuestion: vi.fn(async () => null),
      toolCall: vi.fn(async () => ({ output: '' })),
    });
    return { core, events, rpc };
  }
  __testAugmentVitest_c96d761f764a.it("agent_delegations_various_methods_round_027_pass_02", async () => {
    const ensureAgentResumed = __testAugmentVitest_c96d761f764a.vi.fn(async (agentId: string) => ({
      rpcMethods: {
        steer: async (p: any) => ({ steer: p }),
        cancel: async (p: any) => ({ cancel: p }),
        undoHistory: async (p: any) => ({ undo: p }),
        setModel: async (p: any) => ({ setModel: p }),
        setThinking: async (p: any) => ({ setThinking: p }),
        setPermission: async (p: any) => ({ setPermission: p }),
        getModel: async (p: any) => ({ model: 'm1' }),
        enterPlan: async (p: any) => ({ entered: true }),
        cancelPlan: async (p: any) => ({ canceled: true }),
        clearPlan: async (p: any) => ({ cleared: true }),
        enterSwarm: async (p: any) => ({ swarm: 'ok' }),
        exitSwarm: async (p: any) => ({ exited: true }),
        getSwarmMode: async (p: any) => ({ mode: 'solo' }),
        beginCompaction: async (p: any) => ({ compaction: 'started' }),
        cancelCompaction: async (p: any) => ({ compaction: 'canceled' }),
      },
    }));

    const session: any = { ensureAgentResumed };
    const { SessionAPIImpl } = await __testAugmentLoadTarget_406236b52eab();
    const api = new SessionAPIImpl(session);

    // For brevity call a representative set; each assertion verifies delegation and return
    __testAugmentVitest_c96d761f764a.expect(await api.steer({ agentId: 'a', data: 1 } as any)).toEqual({ steer: { data: 1 } });
    __testAugmentVitest_c96d761f764a.expect(await api.cancel({ agentId: 'a', reason: 'x' } as any)).toEqual({ cancel: { reason: 'x' } });
    __testAugmentVitest_c96d761f764a.expect(await api.undoHistory({ agentId: 'a' } as any)).toEqual({ undo: {} });
    __testAugmentVitest_c96d761f764a.expect(await api.setModel({ agentId: 'a', model: 't' } as any)).toEqual({ setModel: { model: 't' } });
    __testAugmentVitest_c96d761f764a.expect(await api.getModel({ agentId: 'a' } as any)).toEqual({ model: 'm1' });
    __testAugmentVitest_c96d761f764a.expect(await api.enterPlan({ agentId: 'a' } as any)).toEqual({ entered: true });
    __testAugmentVitest_c96d761f764a.expect(await api.cancelPlan({ agentId: 'a' } as any)).toEqual({ canceled: true });
    __testAugmentVitest_c96d761f764a.expect(await api.clearPlan({ agentId: 'a' } as any)).toEqual({ cleared: true });
    __testAugmentVitest_c96d761f764a.expect(await api.enterSwarm({ agentId: 'a' } as any)).toEqual({ swarm: 'ok' });
    __testAugmentVitest_c96d761f764a.expect(await api.getSwarmMode({ agentId: 'a' } as any)).toEqual({ mode: 'solo' });
    __testAugmentVitest_c96d761f764a.expect(await api.beginCompaction({ agentId: 'a' } as any)).toEqual({ compaction: 'started' });
    __testAugmentVitest_c96d761f764a.expect(await api.cancelCompaction({ agentId: 'a' } as any)).toEqual({ compaction: 'canceled' });

    // ensureAgentResumed should have been called at least once with the expected agent id
    __testAugmentVitest_c96d761f764a.expect(ensureAgentResumed).toHaveBeenCalledWith('a');
  });
});

async function waitForEvent(
  events: readonly Event[],
  predicate: (event: Event) => boolean,
): Promise<Event> {
  const deadline = Date.now() + 1_000;
  while (Date.now() < deadline) {
    const event = events.find(predicate);
    if (event !== undefined) return event;
    await delay(10);
  }
  throw new Error('Timed out waiting for event');
}

async function readMainWire(sessionDir: string): Promise<Array<Record<string, unknown>>> {
  const raw = await readFile(join(sessionDir, 'agents', 'main', 'wire.jsonl'), 'utf-8');
  return raw
    .split('\n')
    .filter((line) => line.length > 0)
    .map((line) => JSON.parse(line) as Record<string, unknown>);
}

import * as __testAugmentVitest_c96d761f764a from "vitest";

const __testAugmentLoadTarget_406236b52eab = async () => {
  __testAugmentVitest_c96d761f764a.vi.doUnmock("../../src/session/rpc.js");
  __testAugmentVitest_c96d761f764a.vi.resetModules();
  return import("../../src/session/rpc.js");
};
