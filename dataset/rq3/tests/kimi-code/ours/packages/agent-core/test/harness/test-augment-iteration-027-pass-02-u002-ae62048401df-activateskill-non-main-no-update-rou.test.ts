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
  __testAugmentVitest_c96d761f764a.it("activateSkill_non_main_no_update_round_027_pass_02", async () => {
    // If agentId !== 'main' the prompt-metadata helpers must NOT be invoked.
    // Mock the prompt-metadata module so any accidental call fails loudly.
    __testAugmentVitest_c96d761f764a.vi.doMock('../../src/session/prompt-metadata', () => ({
      promptMetadataTextFromSkill: () => { throw new Error('prompt-metadata.should-not-be-called'); },
      promptMetadataTextFromPayload: () => { throw new Error('payload.should-not-be-called'); },
      titleFromPromptMetadataText: () => 'SHOULD_NOT_USE',
    }));

    // Arrange a session with emitEvent spy and ensureAgentResumed returning an agent RPC
    const emitEvent = __testAugmentVitest_c96d761f764a.vi.fn(async () => {});
    const activateSkill = __testAugmentVitest_c96d761f764a.vi.fn(async () => {});
    const session: any = {
      metadata: {},
      writeMetadata: __testAugmentVitest_c96d761f764a.vi.fn(async () => {}),
      rpc: { emitEvent },
      ensureAgentResumed: __testAugmentVitest_c96d761f764a.vi.fn(async () => ({ rpcMethods: { activateSkill } })),
    };

    const { SessionAPIImpl } = await __testAugmentLoadTarget_406236b52eab();
    const api = new SessionAPIImpl(session);

    // Act: activate skill for a non-main agent should not touch prompt-metadata
    await api.activateSkill({ agentId: 'worker-1', name: 'some-skill', args: 'x' } as any);

    // Assert: agent.activateSkill was called and emitEvent (which updatePromptMetadata would call) was not invoked
    __testAugmentVitest_c96d761f764a.expect(activateSkill).toHaveBeenCalledWith(expect.any(Object));
    __testAugmentVitest_c96d761f764a.expect(emitEvent).not.toHaveBeenCalled();
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
