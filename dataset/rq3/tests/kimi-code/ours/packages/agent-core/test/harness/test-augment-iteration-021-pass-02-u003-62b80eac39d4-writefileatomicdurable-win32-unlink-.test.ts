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
  __testAugmentVitest_d3f04bcd1def.it("writeFileAtomicDurable_win32_unlink_ENOENT_swallowed_round_021_pass_02", async () => {
    const vit = __testAugmentVitest_d3f04bcd1def;
    const originalPlatform = process.platform;
    const filePath = '/tmp/target.txt';
    try {
      Object.defineProperty(process, 'platform', { value: 'win32' });

      const openMock = vit.vi.fn(async (path: string, flag?: unknown) => {
        // tmp file write handle
        if (String(path).endsWith('.tmp')) {
          return { fd: 11, writeFile: vit.vi.fn(async (c: unknown) => {}), sync: vit.vi.fn(async () => {}), close: vit.vi.fn(async () => {}) };
        }
        // dir handle used by syncDir
        return { sync: vit.vi.fn(async () => {}), close: vit.vi.fn(async () => {}) };
      });

      const unlinkMock = vit.vi.fn(async (p: string) => {
        if (String(p) === filePath) {
          const e: any = new Error('not found');
          e.code = 'ENOENT';
          throw e;
        }
        return;
      });

      const renameMock = vit.vi.fn(async () => {});

      vit.vi.doMock('node:fs/promises', () => ({ open: openMock, unlink: unlinkMock, rename: renameMock }));

      const mod = await __testAugmentLoadTarget_12bd884c1a2e();
      const { writeFileAtomicDurable } = mod;

      // Should resolve despite the pre-unlink ENOENT being thrown and swallowed
      await vit.expect(writeFileAtomicDurable(filePath, 'hello')).resolves.toBeUndefined();

      vit.expect(unlinkMock).toHaveBeenCalled();
      vit.expect(renameMock).toHaveBeenCalled();
      // Since rename succeeded, cleanup unlink of tmp should not be required (renamed=true)
      // Ensure at least one unlink was invoked for the target path
      vit.expect(unlinkMock.mock.calls.some((c: any[]) => String(c[0]) === filePath)).toBe(true);
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
