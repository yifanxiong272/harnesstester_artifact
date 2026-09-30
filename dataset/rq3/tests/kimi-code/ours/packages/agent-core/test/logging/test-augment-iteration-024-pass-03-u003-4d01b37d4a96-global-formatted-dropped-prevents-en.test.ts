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







  __testAugmentVitest_8c3247897cfb.it("global formatted dropped prevents enqueue_round_024_pass_03", async () => {
    const globalEnqueues: string[] = [];

    // Mock formatter to drop a specific global message
    __testAugmentVitest_8c3247897cfb.vi.doMock('../../src/logging/formatter', () => {
      return {
        extractError: (e: any) => ({ name: e.name, message: e.message, stack: e.stack }),
        formatEntry: (entry: any, _opts?: any) => {
          if (entry.msg === 'drop-me-global') return { dropped: true, text: '' };
          return { dropped: false, text: `${entry.msg}-GLOBAL` };
        },
        redactCtx: (ctx: any) => ctx,
      } as any;
    });

    __testAugmentVitest_8c3247897cfb.vi.doMock('../../src/logging/sinks', () => {
      return {
        RotatingFileSink: class {
          constructor(_opts: any) {}
          enqueue(text: string) {
            globalEnqueues.push(text);
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
    const { getRootLogger, log } = target as any;

    await getRootLogger().configure(defaultConfig());

    // Emit a dropped and a kept global entry
    log.info('drop-me-global');
    log.info('keep-me-global');

    await getRootLogger().flush();

    __testAugmentVitest_8c3247897cfb.expect(globalEnqueues.some((t) => t.includes('keep-me-global'))).toBe(true);
    __testAugmentVitest_8c3247897cfb.expect(globalEnqueues.some((t) => t.includes('drop-me-global'))).toBe(false);
  });
});


import * as __testAugmentVitest_8c3247897cfb from "vitest";

const __testAugmentLoadTarget_17d510b75e9f = async () => {
  __testAugmentVitest_8c3247897cfb.vi.doUnmock("../../src/logging/logger.js");
  __testAugmentVitest_8c3247897cfb.vi.resetModules();
  return import("../../src/logging/logger.js");
};
