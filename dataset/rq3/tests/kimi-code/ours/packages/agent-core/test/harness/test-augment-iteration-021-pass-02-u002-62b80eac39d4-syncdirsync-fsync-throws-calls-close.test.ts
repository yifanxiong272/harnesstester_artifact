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
  __testAugmentVitest_d3f04bcd1def.it("syncDirSync_fsync_throws_calls_close_round_021_pass_02", async () => {
    const vit = __testAugmentVitest_d3f04bcd1def;
    const originalPlatform = process.platform;
    try {
      // Ensure non-win32 so the function executes the fsync path
      Object.defineProperty(process, 'platform', { value: 'linux' });

      const fd = 999;
      const openSyncMock = vit.vi.fn(() => fd);
      const fsyncSyncMock = vit.vi.fn(() => { throw new Error('fsync failed'); });
      const closeSyncMock = vit.vi.fn(() => {});

      vit.vi.doMock('node:fs', () => ({ openSync: openSyncMock, fsyncSync: fsyncSyncMock, closeSync: closeSyncMock }));

      const mod = await __testAugmentLoadTarget_12bd884c1a2e();
      const { syncDirSync } = mod;

      // fsyncSync throws; syncDirSync should propagate and still call closeSync
      vit.expect(() => syncDirSync('/some/dir')).toThrow('fsync failed');
      vit.expect(openSyncMock).toHaveBeenCalledWith('/some/dir', 'r');
      vit.expect(fsyncSyncMock).toHaveBeenCalledWith(fd);
      vit.expect(closeSyncMock).toHaveBeenCalledWith(fd);
    } finally {
      try { Object.defineProperty(process, 'platform', { value: originalPlatform }); } catch { /* ignore */ }
    }
  });
});

import * as __testAugmentVitest_d3f04bcd1def from "vitest";

const __testAugmentLoadTarget_12bd884c1a2e = async () => {
  __testAugmentVitest_d3f04bcd1def.vi.doUnmock("../../src/utils/fs.js");
  __testAugmentVitest_d3f04bcd1def.vi.resetModules();
  return import("../../src/utils/fs.js");
};
