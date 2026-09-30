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







  __testAugmentVitest_8c3247897cfb.it("session formatted not dropped enqueues text_round_024_pass_03", async () => {
    const sessionEnqueues: string[] = [];

    __testAugmentVitest_8c3247897cfb.vi.doMock('../../src/logging/formatter', () => {
      return {
        extractError: (e: any) => ({ name: e.name, message: e.message, stack: e.stack }),
        // For any entry return dropped=false and a predictable text payload
        formatEntry: (entry: any, _opts?: any) => ({ dropped: false, text: `FMT:${entry.msg}` }),
        redactCtx: (ctx: any) => ctx,
      } as any;
    });

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

    const sessionDir = await mkdtemp(join(tmpdir(), 'logger-session-ok-'));
    try {
      const handle = getRootLogger().attachSession({ sessionId: 's_ok', sessionDir });
      handle.logger.info('hello-session');

      await handle.flush();
      await getRootLogger().flush();

      // The RotatingFileSink receives the formatted text plus the logger adds a trailing newline
      __testAugmentVitest_8c3247897cfb.expect(sessionEnqueues.length).toBeGreaterThanOrEqual(1);
      __testAugmentVitest_8c3247897cfb.expect(sessionEnqueues.some((t) => t.startsWith('FMT:hello-session'))).toBe(true);

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
