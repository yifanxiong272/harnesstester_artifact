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























  __testAugmentVitest_4b326f66c8b7.it("shouldMarkNeedsAuth_error_shapes_and_config_flags_round_014_pass_02", async () => {
    const { McpConnectionManager } = __testAugmentTarget_99e67a41bfd7;

    const oauthService = { hasTokens: () => true, getProvider: () => ({}) };
    const cm = new McpConnectionManager({ oauthService });
    const proto = McpConnectionManager.prototype as any;

    // Helper to build an InternalEntry-like object
    const makeEntry = (cfg: any) => ({ name: 'n', config: cfg, attemptId: 0, status: 'pending' });

    // UnauthorizedError by name -> true
    const e1 = new Error('no');
    (e1 as any).name = 'UnauthorizedError';
    __testAugmentVitest_4b326f66c8b7.expect((proto.shouldMarkNeedsAuth as any).call(cm, makeEntry({ transport: 'http', url: 'u' }), e1)).toBe(true);

    // Numeric code 401 -> true
    const e2 = new Error('denied');
    (e2 as any).code = 401;
    __testAugmentVitest_4b326f66c8b7.expect((proto.shouldMarkNeedsAuth as any).call(cm, makeEntry({ transport: 'http', url: 'u' }), e2)).toBe(true);

    // String code '401' -> true
    const e3 = new Error('denied');
    (e3 as any).code = '401';
    __testAugmentVitest_4b326f66c8b7.expect((proto.shouldMarkNeedsAuth as any).call(cm, makeEntry({ transport: 'http', url: 'u' }), e3)).toBe(true);

    // Message sniff 'unauthorized' -> true
    const e4 = new Error('this is unauthorized by policy');
    __testAugmentVitest_4b326f66c8b7.expect((proto.shouldMarkNeedsAuth as any).call(cm, makeEntry({ transport: 'http', url: 'u' }), e4)).toBe(true);

    // No oauthService -> false
    const cmNo = new McpConnectionManager();
    __testAugmentVitest_4b326f66c8b7.expect((proto.shouldMarkNeedsAuth as any).call(cmNo, makeEntry({ transport: 'http', url: 'u' }), e1)).toBe(false);

    // Non-remote config -> false
    __testAugmentVitest_4b326f66c8b7.expect((proto.shouldMarkNeedsAuth as any).call(cm, makeEntry({ transport: 'stdio', command: process.execPath, args: [] }), e1)).toBe(false);

    // bearerTokenEnvVar present -> false
    __testAugmentVitest_4b326f66c8b7.expect((proto.shouldMarkNeedsAuth as any).call(cm, makeEntry({ transport: 'http', url: 'u', bearerTokenEnvVar: 'X' }), e1)).toBe(false);

    // headers present -> false
    __testAugmentVitest_4b326f66c8b7.expect((proto.shouldMarkNeedsAuth as any).call(cm, makeEntry({ transport: 'http', url: 'u', headers: { 'X': 'y' } }), e1)).toBe(false);

    await cm.shutdown();
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

import * as __testAugmentTarget_99e67a41bfd7 from "../../src/mcp/connection-manager.js";

const __testAugmentLoadTarget_99e67a41bfd7 = async () => {
  __testAugmentVitest_4b326f66c8b7.vi.doUnmock("../../src/mcp/connection-manager.js");
  __testAugmentVitest_4b326f66c8b7.vi.resetModules();
  return import("../../src/mcp/connection-manager.js");
};
