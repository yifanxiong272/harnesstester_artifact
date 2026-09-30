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























  __testAugmentVitest_4b326f66c8b7.it("register_mcp_server_same_server_collision_round_020", async () => {
    const events: any[] = [];
    const agent: any = {
      config: { hasProvider: false },
      records: { logRecord: (_: any) => {} },
      emitEvent: (e: any) => events.push(e),
      getAdditionalDirs: () => [],
      skills: { registry: { getSkillRoots: () => [], listInvocableSkills: () => [] } },
      goal: { getGoal: () => ({ goal: null }) },
      kaos: {},
      rpc: undefined,
      modelProvider: undefined,
      background: undefined,
      cron: undefined,
      subagentHost: undefined,
      log: () => {},
      type: 'main',
    };

    const mod = await __testAugmentLoadTarget_39fd743208f4();
    const { ToolManager } = mod;
    const tm = new ToolManager(agent);

    // Two tools with the same name in a single registerMcpServer call -> same_server collision
    const fakeClient = {
      callTool: async () => ({ output: 'ok' }),
    };
    const tools = [
      { name: 'echo', description: 'first', parameters: {} },
      { name: 'echo', description: 'duplicate', parameters: {} },
    ];

    const result = tm.registerMcpServer('serverA', fakeClient, tools);
    // Expect one registered qualified name (only one winning entry) and one collision
    __testAugmentVitest_4b326f66c8b7.expect(result.registered.length).toBeGreaterThanOrEqual(1);
    __testAugmentVitest_4b326f66c8b7.expect(result.collisions.length).toBe(1);
    __testAugmentVitest_4b326f66c8b7.expect(result.collisions[0].collidesWith.kind).toBe('same_server');

    // The registered qualified name should be present in the ToolManager data() as an MCP tool
    const data = tm.data();
    const qualified = result.registered[0];
    const found = data.find((d: any) => d.name === qualified && d.source === 'mcp');
    __testAugmentVitest_4b326f66c8b7.expect(found).toBeTruthy();
    // By default, MCP tools are not active unless patterns enable them
    __testAugmentVitest_4b326f66c8b7.expect(found?.active).toBe(false);
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

const __testAugmentLoadTarget_39fd743208f4 = async () => {
  __testAugmentVitest_4b326f66c8b7.vi.doUnmock("../../src/agent/tool/index.js");
  __testAugmentVitest_4b326f66c8b7.vi.resetModules();
  return import("../../src/agent/tool/index.js");
};
