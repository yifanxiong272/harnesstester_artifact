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
  __testAugmentVitest_d3f04bcd1def.it("atomicWrite_win32_preunlink_nonENOENT_throws_and_cleanup_round_021_pass_03", async () => {
    const vit = __testAugmentVitest_d3f04bcd1def;
    const originalPlatform = process.platform;
    const filePath = '/win/target-fail.txt';
    try {
      Object.defineProperty(process, 'platform', { value: 'win32' });

      // Make fsync succeed so we reach the pre-unlink
      const fsyncMock = vit.vi.fn((fd: number, cb: (err: NodeJS.ErrnoException | null) => void) => cb(null));
      vit.vi.doMock('node:fs', () => ({ fsync: fsyncMock }));

      const writeFileMock = vit.vi.fn(async () => {});
      const closeMock = vit.vi.fn(async () => {});
      const openMock = vit.vi.fn(async (path: string) => {
        if (String(path).includes('.tmp')) {
          return { fd: 444, writeFile: writeFileMock, sync: vit.vi.fn(async () => {}), close: closeMock };
        }
        return { sync: vit.vi.fn(async () => {}), close: closeMock };
      });

      const unlinkMock = vit.vi.fn(async (p: string) => {
        if (String(p) === filePath) {
          const e: any = new Error('access denied');
          e.code = 'EACCES';
          throw e;
        }
        // tmp cleanup unlink resolves
        return;
      });

      const renameMock = vit.vi.fn(async () => { /* not reached */ });

      vit.vi.doMock('node:fs/promises', () => ({ open: openMock, unlink: unlinkMock, rename: renameMock }));

      const mod = await __testAugmentLoadTarget_12bd884c1a2e();
      const { atomicWrite } = mod;

      await vit.expect(atomicWrite(filePath, 'data')).rejects.toThrow('access denied');

      // unlink called for the original file and for tmp cleanup
      vit.expect(unlinkMock.mock.calls.length).toBeGreaterThanOrEqual(1);
      const calls = unlinkMock.mock.calls.map((c) => String(c[0]));
      vit.expect(calls.some((p) => p === filePath)).toBe(true);
      vit.expect(calls.some((p) => p.includes('.tmp.'))).toBe(true);

      // rename must not have been invoked
      vit.expect(renameMock).not.toHaveBeenCalled();
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
