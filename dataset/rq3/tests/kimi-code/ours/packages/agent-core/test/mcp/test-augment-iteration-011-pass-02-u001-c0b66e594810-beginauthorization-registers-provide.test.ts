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























  __testAugmentVitest_4b326f66c8b7.it("beginAuthorization registers provider when clientLabel provided_round_011_pass_02", async () => {
    const vi = __testAugmentVitest_4b326f66c8b7.vi;

    // auth returns REDIRECT so beginAuthorization proceeds down the redirect path.
    vi.doMock('@modelcontextprotocol/sdk/client/auth.js', () => ({ auth: async () => 'REDIRECT' }));

    // Deterministic store helpers.
    vi.doMock('../../src/mcp/oauth/store', () => ({
      JsonFileStore: class JsonFileStore {},
      mcpCredentialsDir: (d: string) => d,
      mcpOAuthStoreKey: (name: string, url: unknown) => `${name}-${String(url)}`,
    }));

    // Provider mock records the clientLabel passed to the constructor and exposes the expected API.
    let constructed: any = null;
    vi.doMock('../../src/mcp/oauth/provider', () => ({
      McpOAuthClientProvider: class McpOAuthClientProvider {
        constructor(opts: any) {
          this.storeKey = `${opts.serverName}-${String(opts.serverUrl)}`;
          this.clientLabel = opts.clientLabel;
          constructed = this;
        }
        resetFlow() {}
        setRedirectUrl() {}
        takeAuthorizationUrl() { return new URL('https://auth.example/authorize'); }
        tokens() { return undefined; }
      },
    }));

    // Callback server returns a simple object whose close we can observe.
    let closed = false;
    vi.doMock('../../src/mcp/oauth/callback-server', () => ({
      startCallbackServer: async () => ({
        redirectUri: 'http://127.0.0.1/cb',
        close: async () => { closed = true; },
      }),
    }));

    const { McpOAuthService } = await __testAugmentLoadTarget_3dfd4638f794();
    const svc = new McpOAuthService();

    // Provide a clientLabel override: code should construct a new provider and store it.
    const res = await svc.beginAuthorization('srv', 'http://example.invalid', { clientLabel: 'my-client' });

    __testAugmentVitest_4b326f66c8b7.expect(constructed).not.toBeNull();
    __testAugmentVitest_4b326f66c8b7.expect(constructed.clientLabel).toBe('my-client');

    // getProvider should return the same instance that was stored when clientLabel was provided.
    const p = svc.getProvider('srv', 'http://example.invalid');
    __testAugmentVitest_4b326f66c8b7.expect(p).toBe(constructed);

    // Cancel to exercise the cancel cleanup path.
    await res.cancel();
    __testAugmentVitest_4b326f66c8b7.expect(closed).toBe(true);
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
