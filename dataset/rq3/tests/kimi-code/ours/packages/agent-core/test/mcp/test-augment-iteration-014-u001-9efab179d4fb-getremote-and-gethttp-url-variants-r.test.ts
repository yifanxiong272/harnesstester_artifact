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























  __testAugmentVitest_4b326f66c8b7.it("getRemote_and_getHttp_url_variants_round_014", async () => {
    const { McpConnectionManager } = __testAugmentTarget_99e67a41bfd7;
    const cm = new McpConnectionManager();
    try {
      // Unknown server -> undefined
      __testAugmentVitest_4b326f66c8b7.expect(cm.getRemoteServerUrl('missing')).toBeUndefined();

      // Non-remote (stdio) -> undefined
      await cm.connect('local', { transport: 'stdio', command: process.execPath, args: [], enabled: false });
      __testAugmentVitest_4b326f66c8b7.expect(cm.getRemoteServerUrl('local')).toBeUndefined();

      // Remote HTTP config should return its URL even when disabled (no network)
      const url = 'http://127.0.0.1/dummy';
      await cm.connect('remoteNamed', { transport: 'http', url, enabled: false });
      __testAugmentVitest_4b326f66c8b7.expect(cm.getRemoteServerUrl('remoteNamed')).toBe(url);
      // Deprecated getter delegates to same implementation
      __testAugmentVitest_4b326f66c8b7.expect(cm.getHttpServerUrl('remoteNamed')).toBe(url);
    } finally {
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
