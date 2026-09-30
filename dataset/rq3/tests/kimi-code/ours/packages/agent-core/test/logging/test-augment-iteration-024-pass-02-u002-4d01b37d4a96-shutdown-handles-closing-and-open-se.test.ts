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







  __testAugmentVitest_8c3247897cfb.it("shutdown handles closing and open sessions_round_024_pass_02", async () => {
    // We'll mock the RotatingFileSink so close() returns promises we can resolve deterministically.
    const closers: Array<() => void> = [];
    __testAugmentVitest_8c3247897cfb.vi.doMock('../../src/logging/sinks', () => {
      return {
        RotatingFileSink: class {
          constructor(options: any) {
            // create a close promise resolved only when test code calls the captured resolver
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
    const { getRootLogger, __resetRootLoggerForTest } = target as any;

    await getRootLogger().configure(defaultConfig());

    // Create two session directories
    const dirA = await mkdtemp(join(tmpdir(), 'logger-shutdown-a-'));
    const dirB = await mkdtemp(join(tmpdir(), 'logger-shutdown-b-'));

    try {
      // Attach first session and start closing it (do not await the close)
      const first = getRootLogger().attachSession({ sessionId: 's_shutdown_a', sessionDir: dirA });
      const closingPromise = first.close(); // initiates detachSession and sets state='closing'

      // Attach second session and leave it open so __shutdownForTest will move it to closing
      const second = getRootLogger().attachSession({ sessionId: 's_shutdown_b', sessionDir: dirB });

      // Resolve any pending sink-close promises so shutdown does not hang — closers are created
      // during RotatingFileSink construction and will be resolved here.
      for (const r of closers) r();

      // Call the exported reset helper which invokes internal shutdown; this must complete
      await __resetRootLoggerForTest();

      // After reset the root should be unconfigured (fresh root will be produced on next getRootLogger())
      __testAugmentVitest_8c3247897cfb.expect(getRootLogger().isConfigured()).toBe(false);

      // Ensure the previously-initiated close promise also settles
      await closingPromise;
    } finally {
      await rm(dirA, { recursive: true, force: true });
      await rm(dirB, { recursive: true, force: true });
    }
  });
});


import * as __testAugmentVitest_8c3247897cfb from "vitest";

const __testAugmentLoadTarget_17d510b75e9f = async () => {
  __testAugmentVitest_8c3247897cfb.vi.doUnmock("../../src/logging/logger.js");
  __testAugmentVitest_8c3247897cfb.vi.resetModules();
  return import("../../src/logging/logger.js");
};
