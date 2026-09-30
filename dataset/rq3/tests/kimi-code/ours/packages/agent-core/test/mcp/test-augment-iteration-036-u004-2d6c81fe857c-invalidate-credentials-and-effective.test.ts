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























  __testAugmentVitest_4b326f66c8b7.it("invalidate_credentials_and_effective_redirect_uri_round_036", async () => {
    // Provide the same helper exports the provider expects from ./store.
    __testAugmentVitest_4b326f66c8b7.vi.doMock('../../src/mcp/oauth/store', () => ({
      JsonFileStore: class {},
      canonicalMcpOAuthResource: (u: unknown) => (typeof u === 'string' ? u : String(u)),
      mcpOAuthStoreKey: (name: string, url: string) => `${name}@${url}`,
    }));

    const { McpOAuthClientProvider } = await __testAugmentLoadTarget_5e2c5aab3310();

    // Create an in-memory store implementation that records writes and removes.
    const map = new Map<string, unknown>();
    const removed: string[] = [];
    const store = {
      read: (k: string) => map.get(k),
      write: (k: string, v: unknown) => { map.set(k, v); },
      remove: (k: string) => { removed.push(k); map.delete(k); },
    } as const;

    const prov = new McpOAuthClientProvider({ serverName: 'srv', serverUrl: 'https://example', store });

    // Save client information that includes an explicit redirect URI so
    // effectiveRedirectUri uses the registered redirect rather than the passive one.
    prov.saveClientInformation({
      client_id: 'c',
      redirect_uris: ['https://my.redirect/cb'],
      token_endpoint_auth_method: 'none',
      grant_types: ['authorization_code'],
      response_types: ['code'],
    } as any);

    // With no explicit flow redirect set, the provider.redirectUrl should be
    // the registered redirect URI saved above.
    __testAugmentVitest_4b326f66c8b7.expect(String(prov.redirectUrl)).toBe('https://my.redirect/cb');

    // Save some credentials so invalidateCredentials has keys to remove.
    prov.saveTokens({ access_token: 'x' } as any);
    prov.saveClientInformation({ client_id: 'c2', redirect_uris: ['https://other'] } as any);
    prov.saveDiscoveryState({ authorizationServerUrl: 'https://auth.example', authorizationServerMetadata: { issuer: 'i' } } as any);

    // PKCE verifier is present; 'verifier' scope must clear it and return early.
    prov.saveCodeVerifier('pv');
    prov.invalidateCredentials('verifier');
    // After clearing verifier, codeVerifier() must throw.
    __testAugmentVitest_4b326f66c8b7.expect(() => prov.codeVerifier()).toThrow();

    // Re-add verifier and then exercise 'all' to remove all persisted keys and
    // clear verifier as well.
    prov.saveCodeVerifier('pv2');
    prov.invalidateCredentials('all');

    // The remove calls must include the three known suffixes for this provider.
    const tokenKey = `${prov.storeKey}-tokens.json`;
    const clientKey = `${prov.storeKey}-client.json`;
    const discoveryKey = `${prov.storeKey}-discovery.json`;
    __testAugmentVitest_4b326f66c8b7.expect(removed).toEqual(expect.arrayContaining([tokenKey, clientKey, discoveryKey]));

    // After 'all', code verifier must be cleared.
    __testAugmentVitest_4b326f66c8b7.expect(() => prov.codeVerifier()).toThrow();
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

const __testAugmentLoadTarget_5e2c5aab3310 = async () => {
  __testAugmentVitest_4b326f66c8b7.vi.doUnmock("../../src/mcp/oauth/provider.js");
  __testAugmentVitest_4b326f66c8b7.vi.resetModules();
  return import("../../src/mcp/oauth/provider.js");
};
