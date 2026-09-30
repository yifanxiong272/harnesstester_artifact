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























  __testAugmentVitest_4b326f66c8b7.it("mcp_tool_execute_calls_client_and_converts_round_020_pass_02", async () => {
    // Mock the mcp output converter so we can assert the wrapped result deterministically
    __testAugmentVitest_4b326f66c8b7.vi.doMock("../../src/mcp/output", () => ({
      mcpResultToExecutableOutput: (result: any, qualified: string) => ({ converted: true, qualified, inner: result }),
    }));

    const mod = await __testAugmentLoadTarget_39fd743208f4();
    const { ToolManager } = mod;

    const agent: any = {
      config: { hasProvider: false },
      records: { logRecord: (_: any) => {} },
      emitEvent: () => {},
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

    const client = {
      callTool: __testAugmentVitest_4b326f66c8b7.vi.fn(async (toolName: string, args: any, signal?: any) => {
        return { toolName, args, called: true, signalPresent: !!signal };
      }),
    } as any;

    const tm = new ToolManager(agent);
    const tools = [{ name: 'echo', description: 'Echo', parameters: {} }];

    const result = tm.registerMcpServer('srv', client, tools);
    __testAugmentVitest_4b326f66c8b7.expect(result.registered.length).toBeGreaterThanOrEqual(1);

    const qualified = result.registered[0];
    // Find the entry in the tm.mcpTools map and execute its tool
    const entry = (tm as any).mcpTools.get(qualified) as any;
    __testAugmentVitest_4b326f66c8b7.expect(entry).toBeTruthy();

    const exec = entry.tool.resolveExecution({});
    const out = await exec.execute({ turnId: '1', toolCallId: 'tc', signal: (new AbortController()).signal });

    // Our mocked converter should have wrapped the client's return value
    __testAugmentVitest_4b326f66c8b7.expect(out).toEqual({ converted: true, qualified, inner: { toolName: 'echo', args: {}, called: true, signalPresent: true } });

    // client.callTool must have been invoked with the original tool.name (not the qualified)
    __testAugmentVitest_4b326f66c8b7.expect(client.callTool).toHaveBeenCalled();
    const callArgs = client.callTool.mock.calls[0];
    __testAugmentVitest_4b326f66c8b7.expect(callArgs[0]).toBe('echo');
    __testAugmentVitest_4b326f66c8b7.expect(callArgs[1]).toEqual({});
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
