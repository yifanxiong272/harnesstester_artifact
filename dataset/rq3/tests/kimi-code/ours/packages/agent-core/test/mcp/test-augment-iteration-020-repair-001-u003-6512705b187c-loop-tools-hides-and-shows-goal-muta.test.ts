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























  __testAugmentVitest_4b326f66c8b7.it("loop_tools_hides_and_shows_goal_mutation_tools_round_020", async () => {
    const mod = await __testAugmentLoadTarget_39fd743208f4();
    const { ToolManager } = mod;

    // Agent with an active goal -> mutation tools must be visible when registered
    const agentWithGoal: any = {
      config: { hasProvider: false },
      records: { logRecord: (_: any) => {} },
      getAdditionalDirs: () => [],
      skills: { registry: { getSkillRoots: () => [], listInvocableSkills: () => [] } },
      goal: { getGoal: () => ({ goal: { id: 'g1' } }) },
      kaos: {},
      rpc: undefined,
      emitEvent: () => {},
      modelProvider: undefined,
      background: undefined,
      cron: undefined,
      subagentHost: undefined,
      log: () => {},
      type: 'main',
    };

    const tmGoal = new ToolManager(agentWithGoal);
    // Register user tools that are the mutation tools
    tmGoal.registerUserTool({ name: 'SetGoalBudget', description: 'set', parameters: {} });
    tmGoal.registerUserTool({ name: 'UpdateGoal', description: 'update', parameters: {} });
    // Ensure they are active (registerUserTool adds them to enabled set)
    const loopNamesGoal = tmGoal.loopTools.map((t: any) => t.name);
    __testAugmentVitest_4b326f66c8b7.expect(loopNamesGoal).toContain('SetGoalBudget');
    __testAugmentVitest_4b326f66c8b7.expect(loopNamesGoal).toContain('UpdateGoal');

    // Agent without a goal -> the same tools should be filtered out
    const agentNoGoal: any = { ...agentWithGoal, goal: { getGoal: () => ({ goal: null }) } };
    const tmNoGoal = new ToolManager(agentNoGoal);
    tmNoGoal.registerUserTool({ name: 'SetGoalBudget', description: 'set', parameters: {} });
    tmNoGoal.registerUserTool({ name: 'UpdateGoal', description: 'update', parameters: {} });
    const loopNamesNoGoal = tmNoGoal.loopTools.map((t: any) => t.name);
    __testAugmentVitest_4b326f66c8b7.expect(loopNamesNoGoal).not.toContain('SetGoalBudget');
    __testAugmentVitest_4b326f66c8b7.expect(loopNamesNoGoal).not.toContain('UpdateGoal');
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
