import { mkdtemp, realpath, rm } from 'node:fs/promises';
import { homedir, tmpdir } from 'node:os';
import { join } from 'node:path';

import { KaosFileExistsError } from '#/errors';
import { LocalKaos } from '#/local';
import { afterEach, beforeEach, describe, expect, it, test } from 'vitest';

function nodeArgs(code: string): string[] {
  return ['node', '-e', code];
}

describe('LocalKaos', () => {
  let kaos: LocalKaos;
  let tempDir: string;

  beforeEach(async () => {
    kaos = await LocalKaos.create();
    tempDir = await realpath(await mkdtemp(join(tmpdir(), 'kaos-test-')));
    await kaos.chdir(tempDir);
  });

  afterEach(async () => {
    await rm(tempDir, { recursive: true, force: true });
  });

















  // ── Symlink cycle safety ────────────────────────────────────────────
  //
  // These tests use real filesystem symlinks. Note: macOS/Linux apply
  // SYMLOOP_MAX (~40 components) at the kernel level, so an unfixed
  // walker doesn't hang forever — it yields a bounded-but-large number
  // of cyclic paths (observed ~16 for a self-loop) before ELOOP. The
  // assertions here are therefore tight (single-digit expected counts)
  // so they distinguish "OS-ELOOP bailout" (buggy) from "app-level
  // cycle detection" (fixed). HARD_STOP is a final safety belt in case
  // a future kernel allows deeper symlink chains — tests shouldn't hang.







  __testAugmentVitest_4c703264d156.it("waitForSpawn_error_rejects_exec_round_005_pass_03", async () => {
    // Mock child_process.spawn to immediately emit an 'error' (simulate spawn failure)
    __testAugmentVitest_4c703264d156.vi.doMock('node:child_process', () => {
      const { PassThrough } = require('node:stream');
      return {
        spawn: () => {
          const stdin = new PassThrough();
          const stdout = new PassThrough();
          const stderr = new PassThrough();
          const child: any = {
            stdin,
            stdout,
            stderr,
            pid: undefined,
            // When waitForSpawn registers once('error', cb), call cb async to reject
            once(event: string, cb: any) {
              if (event === 'error') {
                setImmediate(() => cb(new Error('spawn simulated failure')));
              }
              // no-op for 'spawn'
              return this;
            },
            on() { return this; },
            off() { return this; },
          };
          return child;
        },
      };
    });

    const mod = await __testAugmentLoadTarget_a25b379575c7();
    const { LocalKaos } = mod as any;
    const kaos = await LocalKaos.create();

    // exec should reject because waitForSpawn's 'error' path is taken
    await __testAugmentVitest_4c703264d156.expect(kaos.exec('irrelevant')).rejects.toThrow(/spawn simulated failure/);
  });
});



async function streamToBuffer(stream: NodeJS.ReadableStream): Promise<Buffer> {
  const chunks: Buffer[] = [];
  for await (const chunk of stream) {
    chunks.push(Buffer.from(chunk as Buffer));
  }
  return Buffer.concat(chunks);
}

import * as __testAugmentVitest_4c703264d156 from "vitest";

const __testAugmentLoadTarget_a25b379575c7 = async () => {
  __testAugmentVitest_4c703264d156.vi.doUnmock("../src/local.js");
  __testAugmentVitest_4c703264d156.vi.resetModules();
  return import("../src/local.js");
};
