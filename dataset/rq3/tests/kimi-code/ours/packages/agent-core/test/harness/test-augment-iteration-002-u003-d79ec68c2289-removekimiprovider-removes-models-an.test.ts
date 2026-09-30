import { mkdtemp, mkdir, readdir, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'pathe';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  createRPC,
  KimiCore,
  type CoreAPI,
  type SDKAPI,
  type TelemetryClient,
} from '../../src';
import {
  __resetRootLoggerForTest,
  getRootLogger,
} from '../../src/logging/logger';
import { resolveLoggingConfig } from '../../src/logging/resolve-config';
import {
  recordingContextTelemetry,
  type TelemetryContextRecord,
} from '../fixtures/telemetry';

const CONFIG = `
default_model = "kimi-code/kimi-for-coding"

[providers."managed:kimi-code"]
type = "kimi"
api_key = "test-key"
base_url = "https://api.example/v1"

[models."kimi-code/kimi-for-coding"]
provider = "managed:kimi-code"
model = "kimi-for-coding"
max_context_size = 1000000
`;

describe('HarnessAPI session model aliases', () => {
  let tmp: string;
  let homeDir: string;
  let workDir: string;
  let configPath: string;

  beforeEach(async () => {
    tmp = await mkdtemp(join(tmpdir(), 'kimi-model-alias-'));
    homeDir = join(tmp, 'home');
    workDir = join(tmp, 'work');
    configPath = join(tmp, 'config.toml');
    await mkdir(workDir, { recursive: true });
    await writeFile(configPath, CONFIG);
  });

  afterEach(async () => {
    await __resetRootLoggerForTest();
    await rm(tmp, { recursive: true, force: true });
  });















  async function findWireFile(root: string): Promise<string> {
    const suffix = join('agents', 'main', 'wire.jsonl');
    const entries = await readdir(root, { recursive: true });
    const match = entries.find((entry) => entry.endsWith(suffix));
    if (match === undefined) {
      throw new Error('wire.jsonl not found under session home');
    }
    return join(root, match);
  }

  async function createTestRpc(
    options: {
      readonly appVersion?: string;
      readonly telemetry?: TelemetryClient;
    } = {},
  ) {
    const [coreRpc, sdkRpc] = createRPC<CoreAPI, SDKAPI>();
    void new KimiCore(coreRpc, {
      homeDir,
      configPath,
      appVersion: options.appVersion,
      telemetry: options.telemetry,
    });
    return sdkRpc({
      emitEvent: vi.fn(),
      requestApproval: vi.fn(async () => ({ decision: 'rejected' as const })),
      requestQuestion: vi.fn(async () => null),
      toolCall: vi.fn(async () => ({ output: '' })),
    });
  }
  __testAugmentVitest_d3f04bcd1def.it("removeKimiProvider_removes_models_and_defaults_round_002", async () => {
    // Prepare a config that defines a provider, defaultProvider, defaultModel and a model referencing that provider.
    const TOML = `
  default_provider = "managed:kimi-code"

  default_model = "kimi-code/kimi-for-coding"

  [providers."managed:kimi-code"]
  type = "kimi"
  api_key = "test-key"
  base_url = "https://api.example/v1"

  [models."kimi-code/kimi-for-coding"]
  provider = "managed:kimi-code"
  model = "kimi-for-coding"
  max_context_size = 1000000
  `;
    await writeFile(configPath, TOML, 'utf-8');

    const rpc = await createTestRpc();
    const updated = await rpc.removeKimiProvider({ providerId: 'managed:kimi-code' });

    // After removal the defaultModel and defaultProvider should be cleared and models that referenced provider removed
    __testAugmentVitest_d3f04bcd1def.expect(updated.defaultModel).toBeUndefined();
    __testAugmentVitest_d3f04bcd1def.expect(updated.defaultProvider).toBeUndefined();
    __testAugmentVitest_d3f04bcd1def.expect(updated.models ?? {}).not.toHaveProperty('kimi-code/kimi-for-coding');
  });
});

import * as __testAugmentVitest_d3f04bcd1def from "vitest";

const __testAugmentLoadTarget_1178a576217e = async () => {
  __testAugmentVitest_d3f04bcd1def.vi.doUnmock("../../src/rpc/core-impl.js");
  __testAugmentVitest_d3f04bcd1def.vi.resetModules();
  return import("../../src/rpc/core-impl.js");
};
