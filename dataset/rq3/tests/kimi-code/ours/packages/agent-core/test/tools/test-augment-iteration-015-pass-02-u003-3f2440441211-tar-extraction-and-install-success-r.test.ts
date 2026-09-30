/**
 * Covers: rg-locator (ripgrep hybrid binary resolution).
 *
 * Pure-lookup pins (no real CDN download):
 *   - `findExistingRg` returns undefined when PATH + share-bin are both empty
 *   - Resolves from `<shareDir>/bin/rg` when that binary exists
 *   - Prefers system PATH over share-dir cache when both are available
 *   - `rgUnavailableMessage` surfaces the underlying cause + install hints
 */

import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync, chmodSync } from 'node:fs';
import type * as FsPromises from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'pathe';

import { extract as extractTar } from 'tar';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ZipFile } from 'yazl';

import {
  detectTarget,
  ensureRgPath,
  extractRgFromZip,
  findExistingRg,
  rgUnavailableMessage,
  verifyArchiveChecksum,
} from '../../src/tools/support/rg-locator';

// Download-branch tests mock `tar.extract` so the archive layout is
// controlled by the test, not the real CDN. `fetch` is replaced per-test
// on `globalThis` to drive the failure and success paths.
vi.mock('tar', () => ({ extract: vi.fn() }));





describe('ensureRgPath download branch', () => {
  let fakeShare: string;
  let savedPath: string | undefined;
  let savedFetch: typeof globalThis.fetch | undefined;
  beforeEach(() => {
    fakeShare = join(
      tmpdir(),
      `kimi-rg-dl-${String(Date.now())}-${String(Math.random()).slice(2)}`,
    );
    mkdirSync(join(fakeShare, 'bin'), { recursive: true });
    savedPath = process.env['PATH'];
    process.env['PATH'] = ''; // force the locator past `whichRg`
    savedFetch = globalThis.fetch;
  });
  afterEach(() => {
    rmSync(fakeShare, { recursive: true, force: true });
    if (savedPath === undefined) delete process.env['PATH'];
    else process.env['PATH'] = savedPath;
    if (savedFetch === undefined) {
      // oxlint-disable-next-line @typescript-eslint/no-explicit-any
      delete (globalThis as unknown as { fetch?: typeof fetch }).fetch;
    } else {
      globalThis.fetch = savedFetch;
    }
    vi.restoreAllMocks();
  });







  __testAugmentVitest_4ca65999efb6.it("tar_extraction_and_install_success_round_015_pass_02", async () => {
    // Force Linux x64 so the tar.gz branch is chosen
    const savedArch = process.arch;
    const savedPlatform = process.platform;
    Object.defineProperty(process, 'arch', { value: 'x64' });
    Object.defineProperty(process, 'platform', { value: 'linux' });

    // Make verifyArchiveChecksum succeed by stubbing crypto to emit the expected pinned digest.
    __testAugmentVitest_4ca65999efb6.vi.doMock('node:crypto', () => ({
      createHash: () => ({
        update: () => ({ digest: () => '253ad0fd5fef0d64cba56c70dccdacc1916d4ed70ad057cc525fcdb0c3bbd2a7' }),
      }),
    }));

    // Mock tar.extract to materialize the exact extracted file path the implementation expects.
    __testAugmentVitest_4ca65999efb6.vi.doMock('tar', () => ({
      extract: __testAugmentVitest_4ca65999efb6.vi.fn(async (opts: any) => {
        // The code calls extractTar with cwd = extractDir. Recreate the expected
        // extracted path: <cwd>/ripgrep-<RG_VERSION>-<target>/<rgBinaryName>
        const extractDir = opts.cwd as string;
        const arch = 'x86_64-unknown-linux-musl';
        const rgName = process.platform === 'win32' ? 'rg.exe' : 'rg';
        const extractedDir = join(extractDir, `ripgrep-15.0.0-${arch}`);
        // Ensure directory exists and write a fake binary file
        mkdirSync(extractedDir, { recursive: true });
        writeFileSync(join(extractedDir, rgName), Buffer.from('fake-binary'));
      }),
    }));

    // Minimal fetch response to allow the download-to-disk pipeline to run (content arbitrary)
    globalThis.fetch = __testAugmentVitest_4ca65999efb6.vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      body: bodyFromBuffer(Buffer.from('fake-tar-bytes')),
    }) as unknown as typeof fetch;

    try {
      const { ensureRgPath } = await __testAugmentLoadTarget_dd1b8adb6952();

      const result = await ensureRgPath({ shareDir: fakeShare });

      // The installer should report the final destination and 'share-bin-downloaded'
      __testAugmentVitest_4ca65999efb6.expect(result.source).toBe('share-bin-downloaded');
      __testAugmentVitest_4ca65999efb6.expect(result.path).toBe(join(fakeShare, 'bin', process.platform === 'win32' ? 'rg.exe' : 'rg'));

      // And the installed binary must exist at the destination
      __testAugmentVitest_4ca65999efb6.expect(existsSync(result.path)).toBe(true);
      __testAugmentVitest_4ca65999efb6.expect(readFileSync(result.path).toString()).toBe('fake-binary');
    } finally {
      Object.defineProperty(process, 'arch', { value: savedArch });
      Object.defineProperty(process, 'platform', { value: savedPlatform });
      __testAugmentVitest_4ca65999efb6.vi.doUnmock('tar');
      __testAugmentVitest_4ca65999efb6.vi.doUnmock('node:crypto');
    }
  });
});

// ── Windows zip download branch ─────────────────────────────────────────
//
// Counterpart to the Linux `ensureRgPath download branch` tests but
// drives the `target.includes('windows')` path: the CDN delivers a `.zip`,
// yauzl walks the entries, and `rg.exe` lands at `<shareDir>/bin/rg.exe`.
// `detectTarget()` reads `process.platform` + `process.arch`, so we
// override both per-test via Object.defineProperty (the same trick used
// by the `detectTarget` suite above).
//
// Fixture zips are built in-memory with `yazl` so tests stay hermetic
// (no committed binary fixtures on the repo). The archive uses the
// layout the CDN actually ships (`ripgrep-{ver}-{target}/rg.exe`).

function buildFixtureZip(entries: Array<{ name: string; content: Buffer }>): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const zip = new ZipFile();
    for (const { name, content } of entries) {
      zip.addBuffer(content, name);
    }
    zip.end();
    const chunks: Buffer[] = [];
    zip.outputStream.on('data', (c: Buffer) => chunks.push(c));
    zip.outputStream.on('end', () => {
      resolve(Buffer.concat(chunks));
    });
    zip.outputStream.on('error', reject);
  });
}

function bodyFromBuffer(buf: Buffer): ReadableStream<Uint8Array> {
  return new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new Uint8Array(buf));
      controller.close();
    },
  });
}


import * as __testAugmentVitest_4ca65999efb6 from "vitest";

const __testAugmentLoadTarget_dd1b8adb6952 = async () => {
  __testAugmentVitest_4ca65999efb6.vi.doUnmock("../../src/tools/support/rg-locator.js");
  __testAugmentVitest_4ca65999efb6.vi.resetModules();
  return import("../../src/tools/support/rg-locator.js");
};
