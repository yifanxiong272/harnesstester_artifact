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







  __testAugmentVitest_4ca65999efb6.it("windows_full_download_and_install_round_015_pass_03", async () => {
    const savedArch = process.arch;
    const savedPlatform = process.platform;
    const savedFetch = globalThis.fetch;
    try {
      // Simulate a Windows host so the .zip branch is taken
      Object.defineProperty(process, 'arch', { value: 'x64' });
      Object.defineProperty(process, 'platform', { value: 'win32' });

      // Build a fixture zip containing the expected rg.exe entry
      const zipBuf = await buildFixtureZip([
        {
          name: 'ripgrep-15.0.0-x86_64-pc-windows-msvc/rg.exe',
          content: Buffer.from('MZfake-pe-bytes-success', 'utf8'),
        },
      ]);

      // Stub crypto to return the pinned SHA for the x86_64 Windows zip so verifyArchiveChecksum passes
      __testAugmentVitest_4ca65999efb6.vi.doMock('node:crypto', () => ({
        createHash: () => ({ update: () => ({ digest: () => '21a98bf42c4da97ca543c010e764cc6dec8b9b7538d05f8d21874016385e0860' }) }),
      }));

      // Provide fetch that yields the zip bytes (as a web ReadableStream)
      globalThis.fetch = __testAugmentVitest_4ca65999efb6.vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        statusText: 'OK',
        body: bodyFromBuffer(zipBuf),
      }) as unknown as typeof fetch;

      const { ensureRgPath } = await __testAugmentLoadTarget_dd1b8adb6952();

      const res = await ensureRgPath({ shareDir: fakeShare });

      __testAugmentVitest_4ca65999efb6.expect(res.source).toBe('share-bin-downloaded');
      __testAugmentVitest_4ca65999efb6.expect(existsSync(res.path)).toBe(true);
      __testAugmentVitest_4ca65999efb6.expect(readFileSync(res.path).toString()).toBe('MZfake-pe-bytes-success');
    } finally {
      Object.defineProperty(process, 'arch', { value: savedArch });
      Object.defineProperty(process, 'platform', { value: savedPlatform });
      if (savedFetch === undefined) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        delete (globalThis as any).fetch;
      } else {
        globalThis.fetch = savedFetch;
      }
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
