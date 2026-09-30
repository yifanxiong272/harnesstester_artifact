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







  __testAugmentVitest_4c703264d156.it("exec_rejects_on_null_stdio_round_005", async () => {
    // Mock node:child_process.spawn to return a ChildProcess-like object with null stdio
    __testAugmentVitest_4c703264d156.vi.doMock('node:child_process', () => {
      return {
        spawn: () => {
          const child: any = {
            stdin: null,
            stdout: null,
            stderr: null,
            pid: undefined,
            once(event: string, cb: any) {
              // waitForSpawn attaches 'spawn' and 'error'; immediately emit 'spawn'
              if (event === 'spawn') {
                setImmediate(cb);
              }
              return this;
            },
            on() { return this; },
            off() { return this; },
            kill() { /* noop */ },
          };
          return child;
        },
      };
    });

    // Load the target after registering mocks
    const mod = await __testAugmentLoadTarget_a25b379575c7();
    const { LocalKaos } = mod as any;

    const kaos = await LocalKaos.create();

    // Expect exec to reject because LocalProcess constructor requires pipes
    await __testAugmentVitest_4c703264d156.expect(kaos.exec('dummy-cmd')).rejects.toThrow(
      /stdin\/?stdout\/?stderr|Process must be created with stdin\/stdout\/stderr pipes\./,
    );
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
