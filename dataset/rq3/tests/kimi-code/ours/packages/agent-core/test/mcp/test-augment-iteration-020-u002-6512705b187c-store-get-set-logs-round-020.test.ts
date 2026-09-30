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























  __testAugmentVitest_4b326f66c8b7.it("store_get_set_logs_round_020", async () => {
    const logs: any[] = [];
    const agent: any = {
      config: { hasProvider: false },
      records: { logRecord: (r: any) => logs.push(r) },
      getAdditionalDirs: () => [],
      skills: { registry: { getSkillRoots: () => [], listInvocableSkills: () => [] } },
      goal: { getGoal: () => ({ goal: null }) },
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

    const mod = await __testAugmentLoadTarget_39fd743208f4();
    const { ToolManager } = mod;
    const tm = new ToolManager(agent);

    // toolStore adapter: set and then get
    const store = tm.toolStore;
    store.set('someKey' as any, 123);
    __testAugmentVitest_4b326f66c8b7.expect(store.get('someKey' as any)).toBe(123);

    // There must be a logRecord for the update
    const update = logs.find((l) => l.type === 'tools.update_store' && l.key === 'someKey');
    __testAugmentVitest_4b326f66c8b7.expect(update).toBeTruthy();
    __testAugmentVitest_4b326f66c8b7.expect(update.value).toBe(123);
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
