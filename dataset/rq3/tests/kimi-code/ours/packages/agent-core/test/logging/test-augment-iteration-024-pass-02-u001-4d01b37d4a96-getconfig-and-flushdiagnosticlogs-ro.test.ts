import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'pathe';

import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import {
  __resetRootLoggerForTest,
  getRootLogger,
  log,
  redact,
  resolveGlobalLogPath,
} from '#/logging/logger';

let homeDir: string;

beforeEach(async () => {
  await __resetRootLoggerForTest();
  homeDir = await mkdtemp(join(tmpdir(), 'logger-test-'));
});

afterEach(async () => {
  await __resetRootLoggerForTest();
  await rm(homeDir, { recursive: true, force: true });
});

function defaultConfig(level: 'info' | 'debug' | 'warn' | 'error' | 'off' = 'info') {
  return {
    level,
    globalLogPath: resolveGlobalLogPath(homeDir),
    globalMaxBytes: 1_000_000,
    globalFiles: 3,
    sessionMaxBytes: 500_000,
    sessionFiles: 2,
  } as const;
}

async function readGlobal(): Promise<string> {
  return readGlobalAt(homeDir);
}

async function readGlobalAt(dir: string): Promise<string> {
  try {
    return await readFile(resolveGlobalLogPath(dir), 'utf-8');
  } catch {
    return '';
  }
}






describe('session routing', () => {







  __testAugmentVitest_8c3247897cfb.it("getConfig and flushDiagnosticLogs_round_024_pass_02", async () => {
    const target = await __testAugmentLoadTarget_17d510b75e9f();
    const { getRootLogger, flushDiagnosticLogs } = target as any;

    // Before configure, getConfig should be undefined
    __testAugmentVitest_8c3247897cfb.expect(getRootLogger().getConfig()).toBeUndefined();

    // Configure and verify getConfig returns the same config object
    const cfg = defaultConfig();
    await getRootLogger().configure(cfg);
    __testAugmentVitest_8c3247897cfb.expect(getRootLogger().getConfig()).toEqual(cfg);

    // flushDiagnosticLogs forwards to root.flush(); when sinks exist it will resolve to boolean
    const ok = await flushDiagnosticLogs();
    __testAugmentVitest_8c3247897cfb.expect(ok).toBe(true);
  });
});


import * as __testAugmentVitest_8c3247897cfb from "vitest";

const __testAugmentLoadTarget_17d510b75e9f = async () => {
  __testAugmentVitest_8c3247897cfb.vi.doUnmock("../../src/logging/logger.js");
  __testAugmentVitest_8c3247897cfb.vi.resetModules();
  return import("../../src/logging/logger.js");
};
