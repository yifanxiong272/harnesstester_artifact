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























  __testAugmentVitest_4b326f66c8b7.it("withTimeout_onTimeout_triggers_closeRuntimeClient_round_014_pass_02", async () => {
    const { McpConnectionManager } = __testAugmentTarget_99e67a41bfd7;
    const cm = new McpConnectionManager();
    const proto = McpConnectionManager.prototype as any;

    const createSpy = __testAugmentVitest_4b326f66c8b7.vi.spyOn(proto, 'createClient');
    const discoverSpy = __testAugmentVitest_4b326f66c8b7.vi.spyOn(proto, 'connectAndDiscoverTools');
    const closeRuntimeSpy = __testAugmentVitest_4b326f66c8b7.vi.spyOn(proto, 'closeRuntimeClient');

    try {
      // createClient returns a startup client object
      const startupClient = { close: async () => undefined };
      createSpy.mockImplementation(() => startupClient);

      // connectAndDiscoverTools returns a never-resolving promise to trigger timeout
      discoverSpy.mockImplementation(() => new Promise(() => {}));

      // Connect with a very small startupTimeoutMs so withTimeout fires quickly
      const connectPromise = cm.connect('tmo', { transport: 'http', url: 'http://x', startupTimeoutMs: 20 });

      // Wait briefly to allow the timeout to occur
      await new Promise((r) => setTimeout(r, 100));

      // closeRuntimeClient should have been invoked from the onTimeout callback
      __testAugmentVitest_4b326f66c8b7.expect(closeRuntimeSpy).toHaveBeenCalled();
      __testAugmentVitest_4b326f66c8b7.expect(closeRuntimeSpy.mock.calls.some((c: any) => c[0] === startupClient)).toBe(true);

      // Clean up any outstanding promise (connect will eventually reject/resolve internally)
      await Promise.race([connectPromise.catch(() => {}), new Promise((r) => setTimeout(r, 50))]);
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
