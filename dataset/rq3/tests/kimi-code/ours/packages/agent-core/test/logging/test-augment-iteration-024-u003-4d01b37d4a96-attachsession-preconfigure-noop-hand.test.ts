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





  __testAugmentVitest_8c3247897cfb.it("attachSession pre-configure noop handle_round_024", async () => {
    const target = await __testAugmentLoadTarget_17d510b75e9f();
    const { getRootLogger } = target as any;

    // Ensure we are in pre-configure state (seed beforeEach resets root)
    // Attach a session before calling configure -> should return a noop handle
    const sessionDir = await mkdtemp(join(tmpdir(), 'logger-session-noop-'));
    const handle = getRootLogger().attachSession({ sessionId: 'pre_cfg', sessionDir });

    // Use the noop logger — should not throw and should not create any session file
    handle.logger.info('should-not-write');
    await handle.flush();
    await handle.close();

    // Attempt to read the session log file; expect it to not exist / be empty
    let sessionExists = true;
    try {
      const content = await readFile(join(sessionDir, 'logs', 'kimi-code.log'), 'utf-8');
      // If file exists, ensure it does not contain our message
      if (content.includes('should-not-write')) sessionExists = false;
    } catch {
      // readFile throws if file doesn't exist — expected
      sessionExists = false;
    }

    __testAugmentVitest_8c3247897cfb.expect(sessionExists).toBe(false);
  });
});




import * as __testAugmentVitest_8c3247897cfb from "vitest";

const __testAugmentLoadTarget_17d510b75e9f = async () => {
  __testAugmentVitest_8c3247897cfb.vi.doUnmock("../../src/logging/logger.js");
  __testAugmentVitest_8c3247897cfb.vi.resetModules();
  return import("../../src/logging/logger.js");
};
