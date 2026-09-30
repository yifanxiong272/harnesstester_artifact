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























  __testAugmentVitest_4b326f66c8b7.it("unexpected_close_flips_connected_to_failed_round_014", async () => {
    const { McpConnectionManager } = __testAugmentTarget_99e67a41bfd7;
    const cm = new McpConnectionManager();

    // Intercept createClient/connectAndDiscoverTools to produce a client that
    // registers an onUnexpectedClose handler we can invoke deterministically.
    const proto = McpConnectionManager.prototype as any;
    const createClientSpy = __testAugmentVitest_4b326f66c8b7.vi.spyOn(proto, 'createClient');
    const discoverSpy = __testAugmentVitest_4b326f66c8b7.vi.spyOn(proto, 'connectAndDiscoverTools');

    try {
      let unexpectedCb: ((reason: any) => void) | undefined;
      const fakeClient = {
        connect: async () => undefined,
        close: async () => undefined,
        onUnexpectedClose: (cb: (reason: any) => void) => {
          unexpectedCb = cb;
        },
      };
      createClientSpy.mockImplementation(() => fakeClient);

      // Provide a single tool so the entry becomes connected before we trigger the close
      const tool = { name: 't1', description: '', parameters: {} };
      discoverSpy.mockResolvedValue([tool]);

      await cm.connect('willclose', { transport: 'http', url: 'http://x', startupTimeoutMs: 1000 });
      __testAugmentVitest_4b326f66c8b7.expect(cm.get('willclose')?.status).toBe('connected');

      // Now simulate unexpected close from the runtime with an error + stderr
      __testAugmentVitest_4b326f66c8b7.expect(typeof unexpectedCb).toBe('function');
      unexpectedCb?.({ error: new Error('fatal-exit'), stderr: 'some diagnostic\n' });

      // Allow asynchronous event loop tasks to run
      for (let i = 0; i < 50; i++) {
        if (cm.get('willclose')?.status === 'failed') break;
        await new Promise((r) => setTimeout(r, 10));
      }

      const entry = cm.get('willclose');
      __testAugmentVitest_4b326f66c8b7.expect(entry?.status).toBe('failed');
      __testAugmentVitest_4b326f66c8b7.expect(entry?.toolCount).toBe(0);
      __testAugmentVitest_4b326f66c8b7.expect(entry?.error).toContain('fatal-exit');
      __testAugmentVitest_4b326f66c8b7.expect(entry?.error).toContain('some diagnostic');
    } finally {
      __testAugmentVitest_4b326f66c8b7.vi.restoreAllMocks();
      await cm.shutdown();
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

import * as __testAugmentTarget_99e67a41bfd7 from "../../src/mcp/connection-manager.js";

const __testAugmentLoadTarget_99e67a41bfd7 = async () => {
  __testAugmentVitest_4b326f66c8b7.vi.doUnmock("../../src/mcp/connection-manager.js");
  __testAugmentVitest_4b326f66c8b7.vi.resetModules();
  return import("../../src/mcp/connection-manager.js");
};
