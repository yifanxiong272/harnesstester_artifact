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







  __testAugmentVitest_8c3247897cfb.it("session formatted dropped prevents enqueue_round_024_pass_03", async () => {
    // Capture enqueue calls from our mocked sinks
    const sessionEnqueues: string[] = [];

    // Mock formatter to force dropped=true for a specific message
    __testAugmentVitest_8c3247897cfb.vi.doMock('../../src/logging/formatter', () => {
      return {
        extractError: (e: any) => ({ name: e.name, message: e.message, stack: e.stack }),
        formatEntry: (entry: any, opts?: any) => {
          if (entry.msg === 'drop-me-session') return { dropped: true, text: '' };
          return { dropped: false, text: `${entry.msg} formatted` };
        },
        redactCtx: (ctx: any) => ctx,
      } as any;
    });

    // Mock sinks so we can observe enqueue calls for the session sink
    __testAugmentVitest_8c3247897cfb.vi.doMock('../../src/logging/sinks', () => {
      return {
        RotatingFileSink: class {
          constructor(_opts: any) {}
          enqueue(text: string) {
            sessionEnqueues.push(text);
          }
          async flush() {
            return true;
          }
          flushSync() {}
          close() {
            return Promise.resolve();
          }
        },
      };
    });

    const target = await __testAugmentLoadTarget_17d510b75e9f();
    const { getRootLogger } = target as any;

    await getRootLogger().configure(defaultConfig());

    const sessionDir = await mkdtemp(join(tmpdir(), 'logger-session-drop-a-'));
    try {
      const handle = getRootLogger().attachSession({ sessionId: 's_drop_a', sessionDir });
      // This message should be marked dropped by our formatter for session entries
      handle.logger.info('drop-me-session');
      // This other message should be enqueued
      handle.logger.info('keep-me-session');

      await handle.flush();
      await getRootLogger().flush();

      // The dropped entry should not have produced an enqueue; only the kept one should
      __testAugmentVitest_8c3247897cfb.expect(sessionEnqueues.some((t) => t.includes('keep-me-session'))).toBe(true);
      __testAugmentVitest_8c3247897cfb.expect(sessionEnqueues.some((t) => t.includes('drop-me-session'))).toBe(false);

      await handle.close();
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
