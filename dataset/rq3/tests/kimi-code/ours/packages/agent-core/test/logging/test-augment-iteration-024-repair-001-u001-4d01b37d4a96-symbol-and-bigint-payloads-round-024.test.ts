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




describe('payload shapes', () => {





  __testAugmentVitest_8c3247897cfb.it("symbol and bigint payloads_round_024", async () => {
    const target = await __testAugmentLoadTarget_17d510b75e9f();
    const { getRootLogger, log } = target as any;

    await getRootLogger().configure(defaultConfig());

    log.warn('sym-test', Symbol('z'));
    log.warn('big-test', BigInt(123));

    await getRootLogger().flush();
    const text = await readGlobal();

    // Be permissive about how symbols may be formatted (with or without quotes)
    const symPresentNearby = /sym-test[\s\S]{0,200}Symbol\(z\)/.test(text);
    const symReasonForms = /reason\s*=\s*"?Symbol\(z\)"?/.test(text) || /reason\s*=\s*Symbol\(z\)/.test(text);
    __testAugmentVitest_8c3247897cfb.expect(symPresentNearby || symReasonForms).toBe(true);

    // BigInt may be stringified with or without quotes depending on formatter
    const bigNearby = /big-test[\s\S]{0,200}123/.test(text);
    const bigReasonForms = /reason\s*=\s*"?123"?/.test(text) || /reason\s*=\s*123/.test(text);
    __testAugmentVitest_8c3247897cfb.expect(bigNearby || bigReasonForms).toBe(true);
  });
});




import * as __testAugmentVitest_8c3247897cfb from "vitest";

const __testAugmentLoadTarget_17d510b75e9f = async () => {
  __testAugmentVitest_8c3247897cfb.vi.doUnmock("../../src/logging/logger.js");
  __testAugmentVitest_8c3247897cfb.vi.resetModules();
  return import("../../src/logging/logger.js");
};
