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





  __testAugmentVitest_8c3247897cfb.it("flushSync writes global and session_round_024", async () => {
    const target = await __testAugmentLoadTarget_17d510b75e9f();
    const { getRootLogger, log } = target as any;

    await getRootLogger().configure(defaultConfig());

    // Create a session and write entries to both session and global sinks
    const sessionDir = await mkdtemp(join(tmpdir(), 'logger-session-sync-'));
    const handle = getRootLogger().attachSession({ sessionId: 's_sync', sessionDir });

    handle.logger.info('sync-session-entry');
    log.info('sync-global-entry');

    // Call the synchronous flush path
    getRootLogger().flushSync();

    // Read files synchronously via promise-based API after flushSync
    const globalText = await readGlobal();
    const sessionText = await readFile(join(sessionDir, 'logs', 'kimi-code.log'), 'utf-8');

    __testAugmentVitest_8c3247897cfb.expect(globalText).toContain('sync-global-entry');
    __testAugmentVitest_8c3247897cfb.expect(sessionText).toContain('sync-session-entry');

    await handle.close();
  });
});




import * as __testAugmentVitest_8c3247897cfb from "vitest";

const __testAugmentLoadTarget_17d510b75e9f = async () => {
  __testAugmentVitest_8c3247897cfb.vi.doUnmock("../../src/logging/logger.js");
  __testAugmentVitest_8c3247897cfb.vi.resetModules();
  return import("../../src/logging/logger.js");
};
