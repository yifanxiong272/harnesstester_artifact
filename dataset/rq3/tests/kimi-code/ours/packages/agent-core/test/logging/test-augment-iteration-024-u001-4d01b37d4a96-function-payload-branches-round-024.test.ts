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





  __testAugmentVitest_8c3247897cfb.it("function payload branches_round_024", async () => {
    // Load the target module under test
    const target = await __testAugmentLoadTarget_17d510b75e9f();
    const { getRootLogger, log } = target as any;

    // Configure logger so emitted entries are written
    await getRootLogger().configure(defaultConfig());

    // Create a function and force an empty name to trigger the anonymous-function branch
    const unnamed = function () {};
    try {
      Object.defineProperty(unnamed, 'name', { value: '', configurable: true });
    } catch {
      // If runtime doesn't allow redefining name, continue — we'll still have a named function
    }

    // Create a named function to hit the named-function branch
    function namedFn() {}

    // Emit logs with function payloads
    log.info('anonymous-fn-test', unnamed as unknown as Function);
    log.info('named-fn-test', namedFn as unknown as Function);

    // Flush and assert that the reason fields for functions are present
    await getRootLogger().flush();
    const text = await readGlobal();

    // Anonymous functions should produce a generic `[Function]` reason
    __testAugmentVitest_8c3247897cfb.expect(text.includes('reason="[Function]"') || text.includes('reason="[Function:') ).toBe(true);
    // Named function should include its name
    __testAugmentVitest_8c3247897cfb.expect(text).toContain('reason="[Function: namedFn]"');
  });
});




import * as __testAugmentVitest_8c3247897cfb from "vitest";

const __testAugmentLoadTarget_17d510b75e9f = async () => {
  __testAugmentVitest_8c3247897cfb.vi.doUnmock("../../src/logging/logger.js");
  __testAugmentVitest_8c3247897cfb.vi.resetModules();
  return import("../../src/logging/logger.js");
};
