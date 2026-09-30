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







  __testAugmentVitest_4c703264d156.it("buildLocalSpawnOptions_flags_round_005", async () => {
    // Access target export via injected binding (no module mocking required).
    const { buildLocalSpawnOptions } = __testAugmentTarget_a25b379575c7;

    // When `isWindows` is true, detached must be false and windowsHide true.
    const winOpts = buildLocalSpawnOptions(true, '/some/cwd', { KEY: 'V' });
    __testAugmentVitest_4c703264d156.expect(winOpts.cwd).toBe('/some/cwd');
    __testAugmentVitest_4c703264d156.expect(winOpts.env).toEqual({ KEY: 'V' });
    __testAugmentVitest_4c703264d156.expect(Array.isArray(winOpts.stdio)).toBe(true);
    __testAugmentVitest_4c703264d156.expect(winOpts.windowsHide).toBe(true);
    __testAugmentVitest_4c703264d156.expect(winOpts.detached).toBe(false);

    // When `isWindows` is false, detached must be true.
    const posixOpts = buildLocalSpawnOptions(false, '/other/cwd', undefined);
    __testAugmentVitest_4c703264d156.expect(posixOpts.cwd).toBe('/other/cwd');
    __testAugmentVitest_4c703264d156.expect(posixOpts.windowsHide).toBe(true);
    __testAugmentVitest_4c703264d156.expect(posixOpts.detached).toBe(true);
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

import * as __testAugmentTarget_a25b379575c7 from "../src/local.js";

const __testAugmentLoadTarget_a25b379575c7 = async () => {
  __testAugmentVitest_4c703264d156.vi.doUnmock("../src/local.js");
  __testAugmentVitest_4c703264d156.vi.resetModules();
  return import("../src/local.js");
};
