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
  __testAugmentVitest_c96d761f764a.it("prompt_main_preserves_custom_title_no_new_title_round_027_pass_02", async () => {
    // Arrange prompt-metadata helpers to return a determinisitc lastPrompt and a title
    __testAugmentVitest_c96d761f764a.vi.doMock('../../src/session/prompt-metadata', () => ({
      promptMetadataTextFromPayload: () => 'LAST_PROMPT_TEXT',
      promptMetadataTextFromSkill: () => 'SKILL_PROMPT_TEXT',
      titleFromPromptMetadataText: (t: string) => `AUTO:${t}`,
    }));

    const writeMetadata = __testAugmentVitest_c96d761f764a.vi.fn(async () => {});
    const emitEvent = __testAugmentVitest_c96d761f764a.vi.fn(async () => {});

    // Start with a metadata object that indicates a custom title — needUpdateEasyTitle should return false
    const session: any = {
      metadata: { title: 'User Title', isCustomTitle: true },
      writeMetadata,
      rpc: { emitEvent },
      ensureAgentResumed: __testAugmentVitest_c96d761f764a.vi.fn(async () => ({ rpcMethods: { prompt: async () => ({ ok: true }) } })),
    };

    const { SessionAPIImpl } = await __testAugmentLoadTarget_406236b52eab();
    const api = new SessionAPIImpl(session);

    // Act: prompt for main — updatePromptMetadata should set lastPrompt but NOT override the custom title
    const res = await api.prompt({ agentId: 'main', input: 'x' } as any);

    // Assert: agent prompt result returned, lastPrompt set, title left unchanged, and emitEvent called with undefined title
    __testAugmentVitest_c96d761f764a.expect(res).toEqual({ ok: true });
    __testAugmentVitest_c96d761f764a.expect(session.metadata.lastPrompt).toBe('LAST_PROMPT_TEXT');
    __testAugmentVitest_c96d761f764a.expect(session.metadata.title).toBe('User Title');
    __testAugmentVitest_c96d761f764a.expect(writeMetadata).toHaveBeenCalled();
    __testAugmentVitest_c96d761f764a.expect(emitEvent).toHaveBeenCalled();

    const calledWith = emitEvent.mock.calls[0]?.[0];
    // Title should be explicitly undefined in the emitted event when no title change was chosen
    __testAugmentVitest_c96d761f764a.expect(calledWith.title).toBeUndefined();
    __testAugmentVitest_c96d761f764a.expect(calledWith.patch).toMatchObject({ lastPrompt: 'LAST_PROMPT_TEXT' });
    __testAugmentVitest_c96d761f764a.expect(calledWith.patch.title).toBeUndefined();
    __testAugmentVitest_c96d761f764a.expect(calledWith.patch.isCustomTitle).toBeUndefined();
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
