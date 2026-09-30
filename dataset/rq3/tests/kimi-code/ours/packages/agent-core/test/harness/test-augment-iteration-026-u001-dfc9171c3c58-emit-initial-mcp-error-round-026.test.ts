import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, normalize } from 'pathe';

import type { Kaos } from '@moonshot-ai/kaos';
import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  FLAG_DEFINITIONS,
  MASTER_ENV,
  createRPC,
  ErrorCodes,
  KimiCore,
  KimiError,
  type ApprovalResponse,
  type CoreAPI,
  type SDKAPI,
} from '../../src';
import {
  __resetRootLoggerForTest,
  getRootLogger,
  resolveGlobalLogPath,
} from '../../src/logging/logger';
import { resolveLoggingConfig } from '../../src/logging/resolve-config';
import type { OAuthTokenProviderResolver } from '../../src/session/provider-manager';
import { testKaos } from '../fixtures/test-kaos';

function requiredFlagEnv(id: string): string {
  const def = FLAG_DEFINITIONS.find((item) => item.id === id);
  if (def === undefined) throw new Error(`Missing flag definition: ${id}`);
  return def.env;
}

function clearExperimentalEnv(): void {
  vi.stubEnv(MASTER_ENV, '0');
  for (const def of FLAG_DEFINITIONS) {
    vi.stubEnv(def.env, '');
  }
}

function experimentalFeatureEnabled(core: KimiCore, id: string): boolean | undefined {
  return core.getExperimentalFeatures().find((feature) => feature.id === id)?.enabled;
}

function setCoreKaos(core: KimiCore, kaos: Promise<Kaos>): void {
  (core as unknown as { kaos?: Promise<Kaos> }).kaos = kaos;
}

function rejectedKaos(error: Error): Promise<Kaos> {
  const promise = Promise.reject(error) as Promise<Kaos>;
  promise.catch(() => undefined);
  return promise;
}

// Builds a Kaos that behaves like the ACP reverse-RPC bridge during
// `session/new`: reading a `local.toml` rejects with a non-ENOENT error because
// the client does not know the session yet (issue #988). Everything else
// delegates to the underlying kaos, so once the system-file read is routed
// through a working (local) kaos, session bootstrap can still proceed.
function createLocalTomlFailingKaos(base: Kaos): Kaos {
  return new Proxy(base, {
    get(target, prop, receiver) {
      if (prop === 'readText') {
        return (
          path: string,
          options?: { encoding?: BufferEncoding; errors?: 'strict' | 'replace' | 'ignore' },
        ) => {
          if (String(path).endsWith('local.toml')) {
            return Promise.reject(
              new Error(`acp: readTextFile failed for ${path}: unknown session (issue #988)`),
            );
          }
          return target.readText(path, options);
        };
      }
      if (prop === 'withCwd') {
        return (cwd: string) => createLocalTomlFailingKaos(target.withCwd(cwd));
      }
      const value = Reflect.get(target, prop, receiver);
      return typeof value === 'function' ? (value as (...args: unknown[]) => unknown).bind(target) : value;
    },
  });
}

describe('KimiCore runtime config', () => {
  let tmp: string;

  afterEach(async () => {
    if (tmp !== undefined) {
      await rm(tmp, { recursive: true, force: true });
    }
    await __resetRootLoggerForTest();
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });





  // Regression for https://github.com/MoonshotAI/kimi-code/issues/988: during
  // ACP `session/new` the tool kaos is the reverse-RPC bridge and the client
  // does not know the session yet, so reading `.kimi-code/local.toml` through
  // it rejects. The workspace local config is a local system file and must be
  // read through the persistence (local) kaos instead.
















  __testAugmentVitest_0dc358e75096.it("emit_initial_mcp_error_round_026", async () => {
    const vi = __testAugmentVitest_0dc358e75096.vi;
    // Provide minimal MCP that fails connectAll to force emitInitialMcpLoadError path
    vi.doMock('../../src/mcp', () => {
      class McpOAuthService {
        constructor() {}
      }
      class McpConnectionManager {
        constructor(opts: any) {
          this.opts = opts;
        }
        onStatusChange(cb: any) {
          // noop
        }
        async connectAll(_servers: any) {
          throw new Error('connect failed (simulated)');
        }
        list() {
          return [];
        }
        async shutdown() {}
      }
      return { McpConnectionManager, McpOAuthService };
    });
    // Minimal skill registry used by Session ctor
    vi.doMock('../../src/skill', () => {
      class SessionSkillRegistry {
        constructor(_opts: any) {}
        async loadRoots(_roots?: any) {}
        listSkills() { return []; }
      }
      function registerBuiltinSkills() {}
      function resolveSkillRoots() { return Promise.resolve([]); }
      return { SessionSkillRegistry, registerBuiltinSkills, resolveSkillRoots, summarizeSkill: (s: any) => s };
    });
    // Minimal HookEngine used by Session ctor
    vi.doMock('../../src/session/hooks', () => {
      class HookEngine {
        constructor(_hooks: any, _opts: any) {}
        async trigger() {}
      }
      return { HookEngine };
    });

    const { Session } = await __testAugmentLoadTarget_4594e9943ada();
    // Simple deterministic kaos
    const kaos = { getcwd: () => '/cwd', withCwd() { return this; } } as unknown as any;
    const emitEvent = __testAugmentVitest_0dc358e75096.vi.fn();
    const rpc = { emitEvent } as any;

    // Construct session with an MCP config so loadMcpServers runs and connectAll rejects
    const session = new Session({
      kaos,
      homedir: '/tmp/ses_emit_mcp',
      rpc,
      id: 'ses_emit_mcp',
      mcpConfig: { servers: { s1: {} } },
    });

    // Allow the ctor-fired async load to run
    await new Promise((r) => setImmediate(r));

    __testAugmentVitest_0dc358e75096.expect(emitEvent).toHaveBeenCalled();
    const payload = emitEvent.mock.calls[0][0] as Record<string, unknown>;
    __testAugmentVitest_0dc358e75096.expect(payload.type).toBe('error');
    // The emitted error uses makeErrorPayload so it should contain an error code and agentId
    __testAugmentVitest_0dc358e75096.expect(payload['agentId']).toBe('main');
  });
});

async function readMainWire(sessionDir: string): Promise<readonly Record<string, unknown>[]> {
  const wire = await readFile(join(sessionDir, 'agents', 'main', 'wire.jsonl'), 'utf-8');
  return wire
    .trim()
    .split('\n')
    .filter((line) => line.length > 0)
    .map((line) => JSON.parse(line) as Record<string, unknown>);
}

function baseModelConfig(): string {
  return `default_model = "default-mock"

[providers.test]
type = "kimi"
api_key = "test-key"

[models."default-mock"]
provider = "test"
model = "default-mock"
max_context_size = 100000
`;
}

import * as __testAugmentVitest_0dc358e75096 from "vitest";

const __testAugmentLoadTarget_4594e9943ada = async () => {
  __testAugmentVitest_0dc358e75096.vi.doUnmock("../../src/session/index.js");
  __testAugmentVitest_0dc358e75096.vi.resetModules();
  return import("../../src/session/index.js");
};
