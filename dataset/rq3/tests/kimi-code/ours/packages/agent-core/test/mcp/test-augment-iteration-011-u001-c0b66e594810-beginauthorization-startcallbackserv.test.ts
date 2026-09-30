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























  __testAugmentVitest_4b326f66c8b7.it("beginAuthorization startCallbackServer failure_round_011", async () => {
    const vi = __testAugmentVitest_4b326f66c8b7.vi;
    const expect = __testAugmentVitest_4b326f66c8b7.expect;

    // Mock the auth module (not reached in this error path but provided for completeness).
    const authMock = async () => 'REDIRECT';
    __testAugmentVitest_4b326f66c8b7.vi.doMock('@modelcontextprotocol/sdk/client/auth.js', () => ({ auth: authMock }));

    // Provide a minimal store mock with deterministic store key computation.
    __testAugmentVitest_4b326f66c8b7.vi.doMock('../../src/mcp/oauth/store', () => ({
      JsonFileStore: class JsonFileStore {},
      mcpCredentialsDir: (d) => d,
      mcpOAuthStoreKey: (name, url) => `${name}-${String(url)}`,
    }));

    // Provider mock: track resetFlow calls but otherwise inert.
    let providerResetCount = 0;
    __testAugmentVitest_4b326f66c8b7.vi.doMock('../../src/mcp/oauth/provider', () => ({
      McpOAuthClientProvider: class McpOAuthClientProvider {
        constructor(opts) {
          this.storeKey = `${opts.serverName}-${String(opts.serverUrl)}`;
        }
        resetFlow() { providerResetCount++; }
        setRedirectUrl() {}
        takeAuthorizationUrl() { return undefined; }
        tokens() { return undefined; }
      },
    }));

    // startCallbackServer fails synchronously with an Error to exercise wrapAuthError.
    __testAugmentVitest_4b326f66c8b7.vi.doMock('../../src/mcp/oauth/callback-server', () => ({
      startCallbackServer: async () => { throw new Error('no socket'); },
    }));

    // Load the target module after registering mocks.
    const { McpOAuthService } = await __testAugmentLoadTarget_3dfd4638f794();

    const svc = new McpOAuthService();

    try {
      await svc.beginAuthorization('srv', 'http://example.invalid');
      throw new Error('expected beginAuthorization to throw');
    } catch (err) {
      // Wrapped error must surface the prefix used in the implementation and carry the original as `cause`.
      __testAugmentVitest_4b326f66c8b7.expect((err).message).toContain('failed to start OAuth callback listener');
      // The cause must be the original Error we threw from startCallbackServer.
      __testAugmentVitest_4b326f66c8b7.expect((err).cause).toBeInstanceOf(Error);
      __testAugmentVitest_4b326f66c8b7.expect((err).cause.message).toBe('no socket');
      // provider.resetFlow was invoked at least once during startup.
      __testAugmentVitest_4b326f66c8b7.expect(providerResetCount).toBeGreaterThanOrEqual(1);
    }
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
