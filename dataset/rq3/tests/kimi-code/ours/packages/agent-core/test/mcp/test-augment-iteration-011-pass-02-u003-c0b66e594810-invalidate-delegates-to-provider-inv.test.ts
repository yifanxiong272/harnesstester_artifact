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























  __testAugmentVitest_4b326f66c8b7.it("invalidate delegates to provider.invalidateCredentials_round_011_pass_02", async () => {
    const vi = __testAugmentVitest_4b326f66c8b7.vi;

    vi.doMock('../../src/mcp/oauth/store', () => ({
      JsonFileStore: class JsonFileStore {},
      mcpCredentialsDir: (d: string) => d,
      mcpOAuthStoreKey: (name: string, url: unknown) => `${name}-${String(url)}`,
    }));

    // Provider mock records the last invalidation scope it received.
    let lastScope: string | undefined = undefined;
    vi.doMock('../../src/mcp/oauth/provider', () => ({
      McpOAuthClientProvider: class McpOAuthClientProvider {
        constructor(opts: any) { this.storeKey = `${opts.serverName}-${String(opts.serverUrl)}`; }
        resetFlow() {}
        invalidateCredentials(scope: string) { lastScope = scope; }
        tokens() { return undefined; }
      },
    }));

    // Minimal auth/callback-server mocks so target loads cleanly (not used here).
    vi.doMock('@modelcontextprotocol/sdk/client/auth.js', () => ({ auth: async () => 'REDIRECT' }));
    vi.doMock('../../src/mcp/oauth/callback-server', () => ({ startCallbackServer: async () => ({ redirectUri: 'http://x', close: async () => {} }) }));

    const { McpOAuthService } = await __testAugmentLoadTarget_3dfd4638f794();
    const svc = new McpOAuthService();

    // Ensure provider exists and then call invalidate.
    svc.getProvider('t', 'http://u');
    svc.invalidate('t', 'http://u', 'tokens');
    __testAugmentVitest_4b326f66c8b7.expect(lastScope).toBe('tokens');

    svc.invalidate('t', 'http://u', 'all');
    __testAugmentVitest_4b326f66c8b7.expect(lastScope).toBe('all');
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

const __testAugmentLoadTarget_3dfd4638f794 = async () => {
  __testAugmentVitest_4b326f66c8b7.vi.doUnmock("../../src/mcp/oauth/service.js");
  __testAugmentVitest_4b326f66c8b7.vi.resetModules();
  return import("../../src/mcp/oauth/service.js");
};
