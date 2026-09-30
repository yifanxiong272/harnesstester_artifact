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
  __testAugmentVitest_c96d761f764a.it("goal_lifecycle_delegations_round_027_pass_03", async () => {
    const methods = {
      createGoal: __testAugmentVitest_c96d761f764a.vi.fn(async (p: any) => ({ created: p })),
      getGoal: __testAugmentVitest_c96d761f764a.vi.fn(async (p: any) => ({ goal: p })),
      pauseGoal: __testAugmentVitest_c96d761f764a.vi.fn(async (p: any) => ({ paused: true })),
      resumeGoal: __testAugmentVitest_c96d761f764a.vi.fn(async (p: any) => ({ resumed: true })),
      cancelGoal: __testAugmentVitest_c96d761f764a.vi.fn(async (p: any) => ({ canceled: true })),
    };
    const ensureAgentResumed = __testAugmentVitest_c96d761f764a.vi.fn(async () => ({ rpcMethods: methods }));
    const session: any = { ensureAgentResumed };

    const { SessionAPIImpl } = await __testAugmentLoadTarget_406236b52eab();
    const api = new SessionAPIImpl(session);

    const cg = await api.createGoal({ agentId: 'z', title: 'T' } as any);
    __testAugmentVitest_c96d761f764a.expect(cg).toEqual({ created: { title: 'T' } });
    __testAugmentVitest_c96d761f764a.expect(methods.createGoal).toHaveBeenCalled();

    const gg = await api.getGoal({ agentId: 'z' } as any);
    __testAugmentVitest_c96d761f764a.expect(gg).toEqual({ goal: {} });
    __testAugmentVitest_c96d761f764a.expect(methods.getGoal).toHaveBeenCalled();

    __testAugmentVitest_c96d761f764a.expect(await api.pauseGoal({ agentId: 'z' } as any)).toEqual({ paused: true });
    __testAugmentVitest_c96d761f764a.expect(await api.resumeGoal({ agentId: 'z' } as any)).toEqual({ resumed: true });
    __testAugmentVitest_c96d761f764a.expect(await api.cancelGoal({ agentId: 'z' } as any)).toEqual({ canceled: true });

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
