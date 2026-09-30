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







  __testAugmentVitest_4c703264d156.it("execWithEnv_invocation_env_used_when_no_layers_round_005", async () => {
    // This test mocks node:child_process so no real external 'node' binary is required.
    let captured: { command?: unknown; args?: unknown; options?: any } | null = null;

    __testAugmentVitest_4c703264d156.vi.doMock('node:child_process', () => {
      // Use synchronous require inside the factory to create stream objects.
      const { PassThrough } = require('node:stream');

      return {
        spawn: (command: unknown, args: unknown[], options: any) => {
          captured = { command, args, options };
          const stdin = new PassThrough();
          const stdout = new PassThrough();
          const stderr = new PassThrough();

          const child: any = {
            stdin,
            stdout,
            stderr,
            pid: 55555,
            // Allow waitForSpawn to attach 'spawn' and 'error' listeners via once/on
            once(ev: string, cb: any) {
              if (ev === 'spawn') {
                // Emulate successful spawn asynchronously.
                setImmediate(cb);
              }
              return this;
            },
            on() { return this; },
            off() { return this; },
            // Provide a best-effort kill implementation used by LocalProcess.kill fallback.
            kill() { return true; },
          };
          return child;
        },
      };
    });

    // Load the target module after registering the mock.
    const mod = await __testAugmentLoadTarget_a25b379575c7();
    const { LocalKaos } = mod as any;

    const kaos = await LocalKaos.create();

    const SENT = 'KAOS_INVOKE_ENV_TEST';
    const invocationEnv = { [SENT]: 'INVOKED' } as Record<string, string>;

    // Call execWithEnv with a mocked spawn; because spawn is mocked the
    // command string is irrelevant and no real process is launched.
    const proc = await kaos.execWithEnv(['irrelevant-cmd', '--no-op'], invocationEnv);

    // At this point waitForSpawn resolved (mock emitted 'spawn') and execWithEnv returned.
    __testAugmentVitest_4c703264d156.expect(captured).not.toBeNull();
    __testAugmentVitest_4c703264d156.expect(captured!.options).toBeDefined();
    __testAugmentVitest_4c703264d156.expect(captured!.options.env).toBeDefined();
    __testAugmentVitest_4c703264d156.expect(captured!.options.env[SENT]).toBe('INVOKED');

    // Clean up the fake process resources. Do not await proc.wait() because
    // there is no real 'exit' event for the mocked child; dispose() is safe.
    proc.dispose();
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
