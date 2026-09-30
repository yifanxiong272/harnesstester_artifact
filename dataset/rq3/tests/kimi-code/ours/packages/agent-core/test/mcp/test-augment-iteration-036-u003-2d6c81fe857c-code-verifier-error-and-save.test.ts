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























  __testAugmentVitest_4b326f66c8b7.it("code_verifier_error_and_save_round_036", async () => {
    __testAugmentVitest_4b326f66c8b7.vi.doMock('../../src/mcp/oauth/store', () => ({
      JsonFileStore: class {},
      canonicalMcpOAuthResource: (u: unknown) => (typeof u === 'string' ? u : String(u)),
      mcpOAuthStoreKey: (name: string, url: string) => `${name}@${url}`,
    }));

    const { McpOAuthClientProvider } = await __testAugmentLoadTarget_5e2c5aab3310();
    const store = { read: (_k: string) => undefined, write: (_k: string, _v: unknown) => undefined, remove: (_k: string) => undefined } as const;
    const prov = new McpOAuthClientProvider({ serverName: 'srv', serverUrl: 'https://example', store });

    // When no verifier has been saved, codeVerifier() must throw the expected error.
    __testAugmentVitest_4b326f66c8b7.expect(() => prov.codeVerifier()).toThrowError(
      'McpOAuthClientProvider: PKCE code verifier not initialized',
    );

    // After saving a code verifier, codeVerifier() must return the saved value.
    prov.saveCodeVerifier('secret-verifier');
    __testAugmentVitest_4b326f66c8b7.expect(prov.codeVerifier()).toBe('secret-verifier');
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
