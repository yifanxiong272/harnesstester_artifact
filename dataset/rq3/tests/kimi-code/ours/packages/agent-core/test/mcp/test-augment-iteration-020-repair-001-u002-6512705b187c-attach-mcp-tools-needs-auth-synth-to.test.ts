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























  __testAugmentVitest_4b326f66c8b7.it("attach_mcp_tools_needs_auth_synth_tool_round_020", async () => {
    // Mock createMcpAuthTool so registerNeedsAuthMcpServer creates a predictable tool
    __testAugmentVitest_4b326f66c8b7.vi.doMock("../../src/mcp/auth-tool", () => ({
      createMcpAuthTool: (opts: any) => ({
        name: `mcp__${opts.serverName}__auth`,
        description: 'auth tool',
        parameters: {},
        resolveExecution: (_: any) => ({ approvalRule: 'auth', execute: async () => ({ output: 'ok' }) }),
      }),
    }));

    const events: any[] = [];
    // mcp stub that lists one needs-auth entry and provides oauthService and URL
    const mcpStub: any = {
      list: () => [{ name: 'ghost', status: 'needs-auth' }],
      oauthService: { /* presence matters */ },
      getRemoteServerUrl: (_: string) => 'https://example.invalid/mcp',
      reconnect: async (_: string) => {},
      onStatusChange: (__cb: any) => {
        // return an unsubscribe
        return () => {};
      },
    };

    const agent: any = {
      config: { hasProvider: false },
      records: { logRecord: (_: any) => {} },
      getAdditionalDirs: () => [],
      skills: { registry: { getSkillRoots: () => [], listInvocableSkills: () => [] } },
      goal: { getGoal: () => ({ goal: null }) },
      kaos: {},
      rpc: undefined,
      emitEvent: (e: any) => events.push(e),
      modelProvider: undefined,
      background: undefined,
      cron: undefined,
      subagentHost: undefined,
      log: () => {},
      type: 'main',
      mcp: mcpStub,
    };

    const mod = await __testAugmentLoadTarget_39fd743208f4();
    const { ToolManager } = mod;

    // Construction should call attachMcpTools and register the synthetic auth tool
    const tm = new ToolManager(agent);

    // The agent must have received a tool.list.updated with reason 'mcp.connected'
    __testAugmentVitest_4b326f66c8b7.expect(events.some((e) => e.type === 'tool.list.updated' && e.reason === 'mcp.connected')).toBe(true);

    // The synthetic tool should appear in data() as an mcp tool
    const data = tm.data();
    const synth = data.find((d: any) => d.name === 'mcp__ghost__auth' && d.source === 'mcp');
    __testAugmentVitest_4b326f66c8b7.expect(synth).toBeTruthy();
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
