import { existsSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'pathe';
import { setTimeout as delay } from 'node:timers/promises';

import type { Kaos } from '@moonshot-ai/kaos';
import {
  APIConnectionError,
  APIEmptyResponseError,
  APIStatusError,
  APITimeoutError,
  type ChatProvider,
  type ModelCapability,
  type ToolCall,
} from '@moonshot-ai/kosong';
import { describe, expect, it, vi } from 'vitest';

import { HookEngine } from '../../src/session/hooks';
import { abortError } from '../../src/utils/abort';
import type { AgentOptions } from '../../src/agent';
import { ErrorCodes, KimiError } from '../../src/errors';
import type { Logger, LogPayload } from '../../src/logging';
import type {
  QueuedSubagentRunResult,
  QueuedSubagentTask,
  SessionSubagentHost,
} from '../../src/session/subagent-host';
import { recordingTelemetry, type TelemetryRecord } from '../fixtures/telemetry';
import { createFakeKaos } from '../tools/fixtures/fake-kaos';
import { createCommandKaos, testAgent, type TestAgentOptions } from './harness/agent';
import { executeTool } from '../tools/fixtures/execute-tool';

type GenerateFn = NonNullable<AgentOptions['generate']>;

interface CapturedLogEntry {
  readonly level: 'error' | 'warn' | 'info' | 'debug';
  readonly message: string;
  readonly payload: LogPayload | undefined;
}

function captureLogs(): { logger: Logger; entries: CapturedLogEntry[] } {
  const entries: CapturedLogEntry[] = [];
  const capture =
    (level: CapturedLogEntry['level']) => (message: string, payload?: LogPayload) => {
      entries.push({ level, message, payload });
    };
  const logger: Logger = {
    error: capture('error'),
    warn: capture('warn'),
    info: capture('info'),
    debug: capture('debug'),
    createChild: () => logger,
  };
  return { logger, entries };
}

describe('Agent turn flow', () => {









































  __testAugmentVitest_7a552f14125f.it("toKosong_unknown_provider_type_throws_round_031_pass_03", async () => {
    const { ProviderManager } = __testAugmentTarget_bf11b5895865;

    const cfg = {
      providers: {
        'p-unknown': {
          // deliberately unsupported provider type to hit the default branch
          type: 'mystery-provider',
          model: 'mx',
        },
      },
      models: {
        'm-unk': { provider: 'p-unknown', model: 'mx', maxContextSize: 10 },
      },
    } as any;

    const pm = new ProviderManager({ config: cfg });
    try {
      pm.resolveProviderConfig('m-unk');
      __testAugmentVitest_7a552f14125f.expect(false).toBe(true);
    } catch (e) {
      __testAugmentVitest_7a552f14125f.expect(e).toBeInstanceOf(KimiError);
      __testAugmentVitest_7a552f14125f.expect((e as KimiError).code).toBe(ErrorCodes.MODEL_CONFIG_INVALID);
      __testAugmentVitest_7a552f14125f.expect(String((e as Error).message)).toContain('Unsupported provider type');
    }
  });
});

const abortableGenerate: GenerateFn = async (
  _chat,
  _systemPrompt,
  _tools,
  _history,
  _callbacks,
  options,
) => {
  await new Promise<void>((_resolve, reject) => {
    const rejectAbort = () => {
      const error = new Error('Aborted');
      error.name = 'AbortError';
      reject(error);
    };
    if (options?.signal?.aborted === true) {
      rejectAbort();
      return;
    }
    options?.signal?.addEventListener('abort', rejectAbort, { once: true });
  });
  throw new Error('abortableGenerate unexpectedly completed');
};

function eventIndex(
  ctx: Pick<ReturnType<typeof testAgent>, 'allEvents'>,
  type: string,
  event: string,
): number {
  return ctx.allEvents.findIndex((entry) => entry.type === type && entry.event === event);
}

function bashCall(): ToolCall {
  return bashCallWithId('call_bash', 'printf should-not-run');
}

function bashCallWithId(id: string, command: string): ToolCall {
  return {
    type: 'function',
    id,
    name: 'Bash',
    arguments: JSON.stringify({ command, timeout: 60 }),
  };
}

function agentSwarmCall(): ToolCall {
  return {
    type: 'function',
    id: 'call_swarm',
    name: 'AgentSwarm',
    arguments: JSON.stringify({
      description: 'Review files',
      prompt_template: 'Review {{item}}',
      items: ['src/a.ts', 'src/b.ts'],
    }),
  };
}

function mockSubagentHost<T extends Partial<SessionSubagentHost>>(
  host: T,
): T & SessionSubagentHost {
  return { spawn: vi.fn(), resume: vi.fn(), runQueued: vi.fn(), ...host } as unknown as T &
    SessionSubagentHost;
}

interface ApiErrorTelemetryCase {
  readonly name: string;
  readonly createError: () => Error;
  readonly errorType: string;
  readonly statusCode?: number;
}

function singleAttemptAgentOptions(): Pick<TestAgentOptions, 'initialConfig'> {
  return {
    initialConfig: {
      providers: {},
      loopControl: { maxRetriesPerStep: 1 },
    },
  };
}

const MP4_HEADER = Buffer.concat([
  Buffer.from([0x00, 0x00, 0x00, 0x18]),
  Buffer.from('ftyp'),
  Buffer.from('mp42'),
  Buffer.from([0x00, 0x00, 0x00, 0x00]),
  Buffer.from('mp42isom'),
]);

const DEFAULT_MEDIA_STAT = {
  stMode: 0o100644,
  stIno: 0,
  stDev: 0,
  stNlink: 1,
  stUid: 0,
  stGid: 0,
  stSize: MP4_HEADER.length,
  stAtime: 0,
  stMtime: 0,
  stCtime: 0,
};

function createVideoKaos(): Kaos {
  return createFakeKaos({
    stat: vi.fn<Kaos['stat']>().mockResolvedValue(DEFAULT_MEDIA_STAT),
    readBytes: vi.fn<Kaos['readBytes']>().mockResolvedValue(MP4_HEADER),
  });
}

async function waitForFile(path: string): Promise<void> {
  for (let i = 0; i < 100; i++) {
    if (existsSync(path)) return;
    await delay(10);
  }
  throw new Error(`Timed out waiting for ${path}`);
}

function mediaCapabilities(): ModelCapability {
  return {
    image_in: true,
    video_in: true,
    audio_in: false,
    thinking: false,
    tool_use: true,
    max_context_tokens: 1_000_000,
  };
}

function oauthAgentOptions(
  getAccessToken: (options?: { readonly force?: boolean }) => Promise<string>,
  capabilities?: readonly string[] | undefined,
): Pick<TestAgentOptions, 'initialConfig' | 'providerManagerOverrides'> {
  return {
    initialConfig: {
      defaultModel: 'kimi-code',
      providers: {
        'managed:kimi-code': {
          type: 'vertexai',
          baseUrl: 'https://api.example/v1',
          oauth: { storage: 'file', key: 'oauth/kimi-code' },
        },
      },
      models: {
        'kimi-code': {
          provider: 'managed:kimi-code',
          model: 'kimi-for-coding',
          maxContextSize: 1_000_000,
          capabilities: capabilities === undefined ? undefined : [...capabilities],
        },
      },
    },
    providerManagerOverrides: {
      resolveOAuthTokenProvider: vi.fn(() => ({ getAccessToken })),
    },
  };
}

function textResult(text: string): Awaited<ReturnType<GenerateFn>> {
  return {
    id: 'mock-oauth-retry',
    message: {
      role: 'assistant',
      content: [{ type: 'text', text }],
      toolCalls: [],
    },
    usage: {
      inputOther: 1,
      output: 1,
      inputCacheRead: 0,
      inputCacheCreation: 0,
    },
    finishReason: 'completed',
    rawFinishReason: 'stop',
  };
}

import * as __testAugmentVitest_7a552f14125f from "vitest";

import * as __testAugmentTarget_bf11b5895865 from "../../src/session/provider-manager.js";

const __testAugmentLoadTarget_bf11b5895865 = async () => {
  __testAugmentVitest_7a552f14125f.vi.doUnmock("../../src/session/provider-manager.js");
  __testAugmentVitest_7a552f14125f.vi.resetModules();
  return import("../../src/session/provider-manager.js");
};
