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







  __testAugmentVitest_8c3247897cfb.it("handle flush waits for closing_round_024_pass_02", async () => {
    const closers: Array<() => void> = [];
    __testAugmentVitest_8c3247897cfb.vi.doMock('../../src/logging/sinks', () => {
      return {
        RotatingFileSink: class {
          constructor() {
            this._close = new Promise((res) => {
              closers.push(res);
            });
          }
          enqueue() {}
          flush() {
            return Promise.resolve(true);
          }
          flushSync() {}
          close() {
            return this._close;
          }
        },
      };
    });

    const target = await __testAugmentLoadTarget_17d510b75e9f();
    const { getRootLogger } = target as any;

    await getRootLogger().configure(defaultConfig());

    const sessionDir = await mkdtemp(join(tmpdir(), 'logger-hflush-'));
    try {
      const handle = getRootLogger().attachSession({ sessionId: 's_flush', sessionDir });

      // Start closing the handle (initiates detachSession and sets entry.state='closing').
      const closePromise = handle.close();

      // Now resolve the sink-close so any awaits complete.
      for (const r of closers) r();

      // makeHandle.flush should await the entry.closePromise path (line ~241)
      await handle.flush();

      // Ensure the close promise settled as well
      await closePromise;
    } finally {
      await rm(sessionDir, { recursive: true, force: true });
    }
  });
});


import * as __testAugmentVitest_8c3247897cfb from "vitest";

const __testAugmentLoadTarget_17d510b75e9f = async () => {
  __testAugmentVitest_8c3247897cfb.vi.doUnmock("../../src/logging/logger.js");
  __testAugmentVitest_8c3247897cfb.vi.resetModules();
  return import("../../src/logging/logger.js");
};
