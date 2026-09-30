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







  __testAugmentVitest_4c703264d156.it("kill_epperm_fallback_calls_child_kill_round_005", async () => {
    // This test exercises the EPERM fallback inside LocalProcess.kill on POSIX-like systems.
    if (process.platform === 'win32') {
      // Not applicable on Windows (different kill path). Make a trivial assertion.
      __testAugmentVitest_4c703264d156.expect(true).toBe(true);
      return;
    }

    // Mock spawn to return a real-looking ChildProcess with non-null stdio
    __testAugmentVitest_4c703264d156.vi.doMock('node:child_process', async () => {
      const { PassThrough } = await import('node:stream');
      return {
        spawn: () => {
          const stdin = new PassThrough();
          const stdout = new PassThrough();
          const stderr = new PassThrough();
          const child: any = {
            stdin,
            stdout,
            stderr,
            pid: 424242, // positive pid -> path that calls process.kill(-pid,...)
            _killed: false,
            once(event: string, cb: any) {
              if (event === 'spawn') setImmediate(cb);
              return this;
            },
            on() { return this; },
            off() { return this; },
            kill(signal?: any) {
              this._killed = true;
              return true;
            },
          };
          return child;
        },
      };
    });

    const mod = await __testAugmentLoadTarget_a25b379575c7();
    const { LocalKaos } = mod as any;

    const kaos = await LocalKaos.create();
    const proc = await kaos.exec('node', '-e', "process.stdout.write('ok')");

    // Replace process.kill temporarily so the negative-pid group kill throws EPERM
    const realKill = process.kill;
    try {
      (process as any).kill = (_pid: number, _sig?: any) => {
        const err: any = new Error('EPERM');
        err.code = 'EPERM';
        throw err;
      };

      // Calling kill() should catch EPERM and fall back to child.kill()
      await __testAugmentVitest_4c703264d156.expect(proc.kill('SIGTERM')).resolves.toBeUndefined();

      // Ensure our mocked child's .kill was invoked (it recorded _killed)
      __testAugmentVitest_4c703264d156.expect((proc as any)._child._killed).toBe(true);
    } finally {
      (process as any).kill = realKill;
    }
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
