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
  __testAugmentVitest_c96d761f764a.it("agent_tool_and_context_delegations_round_027_pass_02", async () => {
    const rpcMethods = {
      registerTool: __testAugmentVitest_c96d761f764a.vi.fn(async (p: any) => ({ registered: p })),
      unregisterTool: __testAugmentVitest_c96d761f764a.vi.fn(async (p: any) => ({ unregistered: p })),
      setActiveTools: __testAugmentVitest_c96d761f764a.vi.fn(async (p: any) => ({ active: p })),
      stopBackground: __testAugmentVitest_c96d761f764a.vi.fn(async (p: any) => ({ stopped: true })),
      detachBackground: __testAugmentVitest_c96d761f764a.vi.fn(async (p: any) => ({ detached: true })),
      clearContext: __testAugmentVitest_c96d761f764a.vi.fn(async (p: any) => ({ cleared: true })),
      getBackground: __testAugmentVitest_c96d761f764a.vi.fn(async (p: any) => ({ bg: 'ok' })),
      getBackgroundOutput: __testAugmentVitest_c96d761f764a.vi.fn(async (p: any) => ({ output: 'o' })),
      getContext: __testAugmentVitest_c96d761f764a.vi.fn(async (p: any) => ({ context: [] })),
      getConfig: __testAugmentVitest_c96d761f764a.vi.fn(async (p: any) => ({ cfg: {} })),
      getPermission: __testAugmentVitest_c96d761f764a.vi.fn(async (p: any) => ({ perm: true })),
      getPlan: __testAugmentVitest_c96d761f764a.vi.fn(async (p: any) => ({ plan: null })),
      getUsage: __testAugmentVitest_c96d761f764a.vi.fn(async (p: any) => ({ usage: {} })),
      getTools: __testAugmentVitest_c96d761f764a.vi.fn(async (p: any) => ({ tools: [] })),
    };

    const ensureAgentResumed = __testAugmentVitest_c96d761f764a.vi.fn(async () => ({ rpcMethods }));
    const session: any = { ensureAgentResumed };
    const { SessionAPIImpl } = await __testAugmentLoadTarget_406236b52eab();
    const api = new SessionAPIImpl(session);

    __testAugmentVitest_c96d761f764a.expect(await api.registerTool({ agentId: 'z', name: 't' } as any)).toEqual({ registered: { name: 't' } });
    __testAugmentVitest_c96d761f764a.expect(await api.unregisterTool({ agentId: 'z', name: 't' } as any)).toEqual({ unregistered: { name: 't' } });
    __testAugmentVitest_c96d761f764a.expect(await api.setActiveTools({ agentId: 'z', tools: [] } as any)).toEqual({ active: { tools: [] } });
    __testAugmentVitest_c96d761f764a.expect(await api.stopBackground({ agentId: 'z' } as any)).toEqual({ stopped: true });
    __testAugmentVitest_c96d761f764a.expect(await api.detachBackground({ agentId: 'z' } as any)).toEqual({ detached: true });
    __testAugmentVitest_c96d761f764a.expect(await api.clearContext({ agentId: 'z' } as any)).toEqual({ cleared: true });
    __testAugmentVitest_c96d761f764a.expect(await api.getBackground({ agentId: 'z' } as any)).toEqual({ bg: 'ok' });
    __testAugmentVitest_c96d761f764a.expect(await api.getBackgroundOutput({ agentId: 'z' } as any)).toEqual({ output: 'o' });
    __testAugmentVitest_c96d761f764a.expect(await api.getContext({ agentId: 'z' } as any)).toEqual({ context: [] });
    __testAugmentVitest_c96d761f764a.expect(await api.getConfig({ agentId: 'z' } as any)).toEqual({ cfg: {} });
    __testAugmentVitest_c96d761f764a.expect(await api.getPermission({ agentId: 'z' } as any)).toEqual({ perm: true });
    __testAugmentVitest_c96d761f764a.expect(await api.getPlan({ agentId: 'z' } as any)).toEqual({ plan: null });
    __testAugmentVitest_c96d761f764a.expect(await api.getUsage({ agentId: 'z' } as any)).toEqual({ usage: {} });
    __testAugmentVitest_c96d761f764a.expect(await api.getTools({ agentId: 'z' } as any)).toEqual({ tools: [] });

    __testAugmentVitest_c96d761f764a.expect(ensureAgentResumed).toHaveBeenCalledWith('z');
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
