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
  __testAugmentVitest_d3f04bcd1def.it("atomicWrite_syncFd_error_rejects_and_cleanup_tmp_round_021_pass_03", async () => {
    const vit = __testAugmentVitest_d3f04bcd1def;

    // Make node:fs.fsync invoke callback with an error
    const fsyncError = new Error('fsync-bang');
    const fsyncMock = vit.vi.fn((fd: number, cb: (err: NodeJS.ErrnoException | null) => void) => cb(fsyncError as any));
    vit.vi.doMock('node:fs', () => ({ fsync: fsyncMock }));

    // Provide a tmp file handle and mocks for rename/unlink
    const writeFileMock = vit.vi.fn(async () => {});
    const closeMock = vit.vi.fn(async () => {});
    const openMock = vit.vi.fn(async () => ({ fd: 77, writeFile: writeFileMock, close: closeMock }));
    const renameMock = vit.vi.fn(async () => { /* not reached */ });
    const unlinkMock = vit.vi.fn(async () => {});
    vit.vi.doMock('node:fs/promises', () => ({ open: openMock, rename: renameMock, unlink: unlinkMock }));

    const mod = await __testAugmentLoadTarget_12bd884c1a2e();
    const { atomicWrite } = mod;

    await vit.expect(atomicWrite('/another/target.txt', 'x')).rejects.toThrow('fsync-bang');

    // fsync was invoked and cleanup unlink attempted for the tmp file
    vit.expect(fsyncMock).toHaveBeenCalled();
    vit.expect(unlinkMock.mock.calls.length).toBeGreaterThanOrEqual(1);
    const calls = unlinkMock.mock.calls.map((c) => String(c[0]));
    vit.expect(calls.some((p) => p.includes('.tmp.'))).toBe(true);
    vit.expect(renameMock).not.toHaveBeenCalled();
  });
});

import * as __testAugmentVitest_d3f04bcd1def from "vitest";

const __testAugmentLoadTarget_12bd884c1a2e = async () => {
  __testAugmentVitest_d3f04bcd1def.vi.doUnmock("../../src/utils/fs.js");
  __testAugmentVitest_d3f04bcd1def.vi.resetModules();
  return import("../../src/utils/fs.js");
};
