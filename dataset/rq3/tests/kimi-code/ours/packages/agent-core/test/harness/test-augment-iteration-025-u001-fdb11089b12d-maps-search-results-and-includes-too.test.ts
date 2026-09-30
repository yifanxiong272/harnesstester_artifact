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
















  __testAugmentVitest_0dc358e75096.it("maps_search_results_and_includes_toolCallId_header_round_025", async () => {
    // Arrange: create a token provider that returns an access token and a fetchImpl
    // that validates headers and returns a 200 response with mixed result shapes.
    const tokenProvider = { getAccessToken: async () => 'tok-123' };
    const captured: { url?: string; init?: RequestInit } = {};
    const fetchImpl = __testAugmentVitest_0dc358e75096.vi.fn(async (url: string, init?: RequestInit) => {
      captured.url = url;
      captured.init = init;
      return {
        status: 200,
        async json() {
          return {
            search_results: [
              // Missing title/url/snippet -> should default to empty strings
              { site_name: 's1' },
              // Has date and content -> those should be included
              { title: 'T2', url: 'https://x/', snippet: 'snip', date: '2021-01-01', content: 'full' },
            ],
          };
        },
        async text() {
          return JSON.stringify({});
        },
      } as unknown as Response;
    });

    const { MoonshotWebSearchProvider } = await __testAugmentLoadTarget_473af1d52f56();
    const provider = new MoonshotWebSearchProvider({
      baseUrl: 'https://search.local/v1',
      tokenProvider,
      fetchImpl: fetchImpl as unknown as typeof fetch,
      defaultHeaders: { 'User-Agent': 'test-agent' },
    });

    // Act
    const results = await provider.search('query text', { limit: 2, includeContent: true, toolCallId: 'call-xyz' });

    // Assert: mapping behavior
    __testAugmentVitest_0dc358e75096.expect(results).toHaveLength(2);
    __testAugmentVitest_0dc358e75096.expect(results[0].title).toBe('');
    __testAugmentVitest_0dc358e75096.expect(results[0].url).toBe('');
    __testAugmentVitest_0dc358e75096.expect(results[0].snippet).toBe('');
    // second row preserves strings
    __testAugmentVitest_0dc358e75096.expect(results[1].title).toBe('T2');
    __testAugmentVitest_0dc358e75096.expect(results[1].url).toBe('https://x/');
    __testAugmentVitest_0dc358e75096.expect(results[1].snippet).toBe('snip');
    __testAugmentVitest_0dc358e75096.expect(results[1].date).toBe('2021-01-01');
    __testAugmentVitest_0dc358e75096.expect(results[1].content).toBe('full');

    // Assert: fetch called with correct URL and headers including toolCallId and Authorization
    __testAugmentVitest_0dc358e75096.expect(captured.url).toBe('https://search.local/v1');
    __testAugmentVitest_0dc358e75096.expect(captured.init).toBeDefined();
    const headers = captured.init!.headers as Record<string, string>;
    __testAugmentVitest_0dc358e75096.expect(headers['Authorization']).toBe('Bearer tok-123');
    __testAugmentVitest_0dc358e75096.expect(headers['X-Msh-Tool-Call-Id']).toBe('call-xyz');
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

const __testAugmentLoadTarget_473af1d52f56 = async () => {
  __testAugmentVitest_0dc358e75096.vi.doUnmock("../../src/tools/providers/moonshot-web-search.js");
  __testAugmentVitest_0dc358e75096.vi.resetModules();
  return import("../../src/tools/providers/moonshot-web-search.js");
};
