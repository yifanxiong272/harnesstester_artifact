import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join } from 'pathe';
import { setTimeout as sleep } from 'node:timers/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { testKaos } from '../fixtures/test-kaos';
import type { ProviderConfig } from '@moonshot-ai/kosong';
import { describe, expect, it } from 'vitest';

import { randomUUID } from 'node:crypto';
import { createServer as createHttpServer, type Server as HttpServer } from 'node:http';
import type { AddressInfo as HttpAddress } from 'node:net';

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import type {
  OAuthClientInformationFull,
  OAuthTokens,
} from '@modelcontextprotocol/sdk/shared/auth.js';
import { z } from 'zod';

import { KimiError } from '../../src/errors';
import { ProviderManager } from '../../src/session/provider-manager';
import { McpConnectionManager, type McpServerEntry } from '../../src/mcp/connection-manager';
import { JsonFileStore, McpOAuthService } from '../../src/mcp/oauth';
import type { AgentEvent, SDKSessionRPC } from '../../src/rpc';
import { Session } from '../../src/session';
import { SessionAPIImpl } from '../../src/session/rpc';
import { createScriptedGenerate } from '../agent/harness';


const here = import.meta.dirname;
const stdioFixture = join(here, 'fixtures', 'mock-stdio-server.mjs');
const slowStdioFixture = join(here, 'fixtures', 'slow-stdio-server.mjs');
const crashAfterConnectFixture = join(here, 'fixtures', 'crash-after-connect-stdio-server.mjs');
const stderrThenExitFixture = join(here, 'fixtures', 'stderr-then-exit-stdio-server.mjs');
const MOCK_PROVIDER: ProviderConfig = {
  type: 'kimi',
  apiKey: 'test-key',
  model: 'mock-model',
};
type SessionRpcEvent = AgentEvent & { readonly agentId: string };

function stdioConfig(args: string[] = [stdioFixture]) {
  return {
    transport: 'stdio' as const,
    command: process.execPath,
    args,
  };
}

function sessionRpc(options: {
  readonly events?: SessionRpcEvent[] | undefined;
  readonly onEvent?: ((event: SessionRpcEvent) => void) | undefined;
} = {}): SDKSessionRPC {
  return {
    emitEvent: async (event: SessionRpcEvent) => {
      options.events?.push(event);
      options.onEvent?.(event);
    },
    requestApproval: async () => ({ decision: 'rejected' }),
    requestQuestion: async () => null,
    toolCall: async () => ({ output: '' }),
  } as unknown as SDKSessionRPC;
}

describe('McpConnectionManager', () => {























  __testAugmentVitest_4b326f66c8b7.it("create_video_uploader_auth_and_noauth_round_020", async () => {
    const calls: any[] = [];
    // Agent stub that avoids builtin initialization
    const agent: any = {
      config: { hasProvider: false, modelAlias: 'alias' },
      records: { logRecord: (_: any) => {} },
      getAdditionalDirs: () => [],
      skills: { registry: { getSkillRoots: () => [], listInvocableSkills: () => [] } },
      goal: { getGoal: () => ({ goal: null }) },
      kaos: {},
      rpc: undefined,
      emitEvent: (_: any) => {},
      modelProvider: undefined,
      background: undefined,
      cron: undefined,
      subagentHost: undefined,
      log: () => {},
      type: 'main',
    };

    const mod = await __testAugmentLoadTarget_39fd743208f4();
    const { ToolManager } = mod;
    const tm = new ToolManager(agent);

    // Provider with an uploadVideo implementation (no auth wrapping)
    const providerNoAuth = {
      uploadVideo: __testAugmentVitest_4b326f66c8b7.vi.fn(async (input: unknown, opts?: any) => {
        calls.push({ kind: 'noauth', input, opts });
        return { url: 'u1' };
      }),
    } as any;

    const uploader1 = (tm as any).createVideoUploader(providerNoAuth as any);
    __testAugmentVitest_4b326f66c8b7.expect(typeof uploader1).toBe('function');
    const res1 = await uploader1({ foo: 'bar' });
    __testAugmentVitest_4b326f66c8b7.expect(res1).toEqual({ url: 'u1' });
    __testAugmentVitest_4b326f66c8b7.expect(calls.some((c) => c.kind === 'noauth')).toBe(true);

    // Provider with uploadVideo and agent.modelProvider.resolveAuth present
    const providerWithAuth = {
      uploadVideo: __testAugmentVitest_4b326f66c8b7.vi.fn(async (input: unknown, opts?: any) => {
        calls.push({ kind: 'withauth', input, opts });
        return { url: 'u2', auth: opts?.auth };
      }),
    } as any;

    // Provide a modelProvider.resolveAuth that yields an auth object to the callback
    agent.modelProvider = {
      resolveAuth: (modelAlias: string, _opts: any) => {
        return (cb: (auth: any) => any) => cb({ token: `tok-for-${modelAlias}` });
      },
    };

    const uploader2 = (tm as any).createVideoUploader(providerWithAuth as any);
    __testAugmentVitest_4b326f66c8b7.expect(typeof uploader2).toBe('function');
    const res2 = await uploader2({ x: 1 });
    __testAugmentVitest_4b326f66c8b7.expect(res2).toEqual({ url: 'u2', auth: { token: 'tok-for-alias' } });
    // Ensure uploadVideo was called with auth in opts
    __testAugmentVitest_4b326f66c8b7.expect(calls.some((c) => c.kind === 'withauth' && c.opts && c.opts.auth && c.opts.auth.token === 'tok-for-alias')).toBe(true);
  });
});


function testProviderManager(): ProviderManager {
  return new ProviderManager({
    config: {
      providers: {
        test: {
          type: MOCK_PROVIDER.type,
          apiKey: MOCK_PROVIDER.apiKey,
        },
      },
      models: {
        [MOCK_PROVIDER.model]: {
          provider: 'test',
          model: MOCK_PROVIDER.model,
          maxContextSize: 1_000_000,
        },
      },
    },
  });
}

import * as __testAugmentVitest_4b326f66c8b7 from "vitest";

const __testAugmentLoadTarget_39fd743208f4 = async () => {
  __testAugmentVitest_4b326f66c8b7.vi.doUnmock("../../src/agent/tool/index.js");
  __testAugmentVitest_4b326f66c8b7.vi.resetModules();
  return import("../../src/agent/tool/index.js");
};
