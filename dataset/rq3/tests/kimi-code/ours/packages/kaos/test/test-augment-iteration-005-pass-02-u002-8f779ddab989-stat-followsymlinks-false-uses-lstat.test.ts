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







  __testAugmentVitest_4c703264d156.it("stat_followSymlinks_false_uses_lstat_round_005_pass_02", async () => {
    const mod = await __testAugmentLoadTarget_a25b379575c7();
    const { LocalKaos } = mod as any;
    const kaos = await LocalKaos.create();

    const fs = await import('node:fs/promises');
    const { mkdtemp } = fs;
    const { tmpdir } = await import('node:os');
    const { join } = await import('pathe');

    const tmp = await mkdtemp(join(tmpdir(), 'kaos-stat-'));
    await kaos.chdir(tmp);

    const target = join(tmp, 't.txt');
    await kaos.writeText(target, 'hello');
    const link = join(tmp, 'link-to-t');
    await fs.symlink(target, link);

    const statFollow = await kaos.stat(link, { followSymlinks: true });
    const statNoFollow = await kaos.stat(link, { followSymlinks: false });

    // Compare to platform lstat/stat to ensure followSymlinks flag selected the right call
    const realStat = await fs.stat(link);
    const realLstat = await fs.lstat(link);

    __testAugmentVitest_4c703264d156.expect(statFollow.stIno).toBe(realStat.ino);
    __testAugmentVitest_4c703264d156.expect(statNoFollow.stIno).toBe(realLstat.ino);
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
