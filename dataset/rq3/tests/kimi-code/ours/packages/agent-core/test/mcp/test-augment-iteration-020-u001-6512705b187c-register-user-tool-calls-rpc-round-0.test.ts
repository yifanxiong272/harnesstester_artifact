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























  __testAugmentVitest_4b326f66c8b7.it("register_user_tool_calls_rpc_round_020", async () => {
    // Minimal agent stub capturing records and rpc calls
    const records: any[] = [];
    const rpc = { toolCall: __testAugmentVitest_4b326f66c8b7.vi.fn(async (_payload: any) => ({ output: 'rpc-ok' })) };
    const events: any[] = [];
    const agent: any = {
      config: { hasProvider: false },
      records: { logRecord: (r: any) => records.push(r) },
      rpc,
      emitEvent: (e: any) => events.push(e),
      getAdditionalDirs: () => [],
      skills: { registry: { getSkillRoots: () => [], listInvocableSkills: () => [] } },
      goal: { getGoal: () => ({ goal: null }) },
      modelProvider: undefined,
      kaos: {},
      background: undefined,
      cron: undefined,
      subagentHost: undefined,
      log: () => {},
      type: 'main',
    };

    const mod = await __testAugmentLoadTarget_39fd743208f4();
    const { ToolManager } = mod;

    const tm = new ToolManager(agent);

    // Register a user tool and assert a register log entry
    tm.registerUserTool({ name: 'myTool', description: 'desc', parameters: { foo: 'bar' } });
    // The record must contain the register event
    __testAugmentVitest_4b326f66c8b7.expect(records.some((r) => r.type === 'tools.register_user_tool' && r.name === 'myTool')).toBe(true);

    // The tool should appear in data() as a user tool and be active by default
    const data = tm.data();
    const found = data.find((d: any) => d.name === 'myTool' && d.source === 'user');
    __testAugmentVitest_4b326f66c8b7.expect(found).toBeTruthy();
    __testAugmentVitest_4b326f66c8b7.expect(found?.active).toBe(true);

    // Use loopTools to get the executable tool and exercise resolveExecution -> execute
    const loop = tm.loopTools;
    const execTool: any = loop.find((t: any) => t.name === 'myTool');
    __testAugmentVitest_4b326f66c8b7.expect(execTool).toBeTruthy();

    const resolved = execTool.resolveExecution({ some: 'args' });
    __testAugmentVitest_4b326f66c8b7.expect(resolved.approvalRule).toBe('myTool');

    const result = await resolved.execute({ turnId: '7', toolCallId: 'tc-1', signal: (new AbortController()).signal });
    // rpc.toolCall should have been invoked with the numeric turnId and the provided toolCallId and args
    __testAugmentVitest_4b326f66c8b7.expect(rpc.toolCall).toHaveBeenCalled();
    const callArg = rpc.toolCall.mock.calls[0][0];
    __testAugmentVitest_4b326f66c8b7.expect(callArg.turnId).toBe(7);
    __testAugmentVitest_4b326f66c8b7.expect(callArg.toolCallId).toBe('tc-1');

    __testAugmentVitest_4b326f66c8b7.expect(result).toEqual({ output: 'rpc-ok' });
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
