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







  __testAugmentVitest_4c703264d156.it("scanTextFile_valid_multibyte_sequences_round_005_pass_02", async () => {
    const mod = await __testAugmentLoadTarget_a25b379575c7();
    const { LocalKaos } = mod as any;
    const kaos = await LocalKaos.create();

    const { mkdtemp } = await import('node:fs/promises');
    const { tmpdir } = await import('node:os');
    const { join } = await import('pathe');
    const tmp = await mkdtemp(join(tmpdir(), 'kaos-scan-valid-'));
    await kaos.chdir(tmp);

    // Construct a buffer with a variety of valid UTF-8 start bytes so the
    // validator exercises branches for 2/3/4-byte sequences and the special
    // lower/upper bound adjustments.
    const parts: Buffer[] = [];
    // ASCII line (counts as a line)
    parts.push(Buffer.from('ascii\n', 'utf-8'));
    // 2-byte: U+00A2 (¢) -> 0xc2 0xa2
    parts.push(Buffer.from([0xc2, 0xa2]));
    parts.push(Buffer.from('\n'));
    // 3-byte special: 0xe0 0xa0 0x80 (lowest 3-byte)
    parts.push(Buffer.from([0xe0, 0xa0, 0x80]));
    parts.push(Buffer.from('\n'));
    // 3-byte ED-range end: 0xed 0x9f 0xbf (highest allowed under ED branch)
    parts.push(Buffer.from([0xed, 0x9f, 0xbf]));
    parts.push(Buffer.from('\n'));
    // 4-byte: 0xf0 0x90 0x80 0x80
    parts.push(Buffer.from([0xf0, 0x90, 0x80, 0x80]));
    parts.push(Buffer.from('\n'));
    // 4-byte F4 upper: 0xf4 0x8f 0xbf 0xbf
    parts.push(Buffer.from([0xf4, 0x8f, 0xbf, 0xbf]));
    parts.push(Buffer.from('\n'));

    const buf = Buffer.concat(parts);
    const path = join(tmp, 'multi-utf8.txt');
    await kaos.writeBytes(path, buf);

    // Should not throw; should report some lines and no NUL
    const result = await kaos.scanTextFile(path);
    __testAugmentVitest_4c703264d156.expect(result.hasNul).toBe(false);
    __testAugmentVitest_4c703264d156.expect(result.totalLines).toBeGreaterThanOrEqual(5);
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
