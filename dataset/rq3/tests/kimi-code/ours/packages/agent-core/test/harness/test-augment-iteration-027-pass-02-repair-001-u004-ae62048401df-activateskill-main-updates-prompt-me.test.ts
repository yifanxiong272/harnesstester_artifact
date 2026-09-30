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
  __testAugmentVitest_c96d761f764a.it("activateSkill_main_updates_prompt_metadata_round_027_pass_02", async () => {
    // Mock prompt-metadata helpers to deterministically produce a lastPrompt and derived title
    __testAugmentVitest_c96d761f764a.vi.doMock('../../src/session/prompt-metadata', () => ({
      promptMetadataTextFromSkill: (payload: any) => `skill:${payload.name}:${payload.args ?? ''}`,
      promptMetadataTextFromPayload: () => 'unused',
      titleFromPromptMetadataText: (t: string) => `TITLE:${t}`,
    }));

    const writeMetadata = __testAugmentVitest_c96d761f764a.vi.fn(async () => {});
    const emitEvent = __testAugmentVitest_c96d761f764a.vi.fn(async () => {});

    // Start with untitled metadata so a new easy title is created
    const session: any = {
      metadata: { title: '', isCustomTitle: false },
      writeMetadata,
      rpc: { emitEvent },
      ensureAgentResumed: __testAugmentVitest_c96d761f764a.vi.fn(async () => ({ rpcMethods: { activateSkill: async (_p: any) => {} } })),
    };

    const { SessionAPIImpl } = await __testAugmentLoadTarget_406236b52eab();
    const api = new SessionAPIImpl(session);

    // Act: activateSkill for main should call agent.activateSkill then updatePromptMetadata
    await api.activateSkill({ agentId: 'main', name: 'cool-skill', args: 'arg1' } as any);

    __testAugmentVitest_c96d761f764a.expect(session.ensureAgentResumed).toHaveBeenCalledWith('main');
    __testAugmentVitest_c96d761f764a.expect(writeMetadata).toHaveBeenCalled();
    __testAugmentVitest_c96d761f764a.expect(emitEvent).toHaveBeenCalled();

    const emitted = emitEvent.mock.calls[0]?.[0];
    __testAugmentVitest_c96d761f764a.expect(emitted).toMatchObject({ type: 'session.meta.updated', agentId: 'main' });
    __testAugmentVitest_c96d761f764a.expect(emitted.title).toBe('TITLE:skill:cool-skill:arg1');
    __testAugmentVitest_c96d761f764a.expect(emitted.patch).toMatchObject({ lastPrompt: 'skill:cool-skill:arg1' });
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
