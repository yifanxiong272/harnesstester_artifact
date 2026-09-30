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























  __testAugmentVitest_4b326f66c8b7.it("beginAuthorization complete success and idempotent complete_round_011_pass_02", async () => {
    const vi = __testAugmentVitest_4b326f66c8b7.vi;

    // auth must return REDIRECT for the initial call and AUTHORIZED for the exchange.
    let calls = 0;
    vi.doMock('@modelcontextprotocol/sdk/client/auth.js', () => ({
      auth: async () => {
        calls++;
        return calls === 1 ? 'REDIRECT' : 'AUTHORIZED';
      },
    }));

    vi.doMock('../../src/mcp/oauth/store', () => ({
      JsonFileStore: class JsonFileStore {},
      mcpCredentialsDir: (d: string) => d,
      mcpOAuthStoreKey: (name: string, url: unknown) => `${name}-${String(url)}`,
    }));

    // Provider mock exposes expectedState and tracks resetFlow calls.
    let resetCount = 0;
    vi.doMock('../../src/mcp/oauth/provider', () => ({
      McpOAuthClientProvider: class McpOAuthClientProvider {
        constructor(opts: any) { this.storeKey = `${opts.serverName}-${String(opts.serverUrl)}`; this._expected = 's-123'; }
        resetFlow() { resetCount++; }
        setRedirectUrl() {}
        takeAuthorizationUrl() { return new URL('https://auth.example/authorize'); }
        expectedState() { return this._expected; }
        tokens() { return undefined; }
      },
    }));

    // Callback server yields a code/state that matches expectedState and exposes close.
    let closed = false;
    vi.doMock('../../src/mcp/oauth/callback-server', () => ({
      startCallbackServer: async () => ({
        redirectUri: 'http://127.0.0.1/cb',
        close: async () => { closed = true; },
        waitForCode: async () => ({ code: 'the-code', state: 's-123' }),
      }),
    }));

    const { McpOAuthService } = await __testAugmentLoadTarget_3dfd4638f794();
    const svc = new McpOAuthService();

    const begun = await svc.beginAuthorization('svc', 'http://u');
    // Complete should resolve (no throw) when final auth returns AUTHORIZED.
    await begun.complete();

    __testAugmentVitest_4b326f66c8b7.expect(closed).toBe(true);
    __testAugmentVitest_4b326f66c8b7.expect(resetCount).toBeGreaterThanOrEqual(1);

    // Second call to complete() must throw the 'already completed or cancelled' error.
    await __testAugmentVitest_4b326f66c8b7.expect(begun.complete()).rejects.toThrow('OAuth flow already completed or cancelled');
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
