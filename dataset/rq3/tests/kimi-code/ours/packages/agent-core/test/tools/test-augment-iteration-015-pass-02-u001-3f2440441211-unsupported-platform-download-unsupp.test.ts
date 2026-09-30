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







  __testAugmentVitest_4ca65999efb6.it("unsupported-platform-download_round_015_pass_02", async () => {
    // Reuse suite fixtures (fakeShare) declared in the parent describe.
    const savedArch = process.arch;
    const savedPlatform = process.platform;
    try {
      // Force detectTarget() → undefined to exercise the unsupported-platform throw
      Object.defineProperty(process, 'arch', { value: 'mips' });
      Object.defineProperty(process, 'platform', { value: 'linux' });

      // Load the target under the manipulated process values
      const { ensureRgPath } = await __testAugmentLoadTarget_dd1b8adb6952();

      await __testAugmentVitest_4ca65999efb6.expect(
        ensureRgPath({ shareDir: fakeShare }),
      ).rejects.toThrow(/Unsupported platform\/arch for ripgrep download: linux\/mips/);
    } finally {
      // Restore process globals so other tests are unaffected.
      Object.defineProperty(process, 'arch', { value: savedArch });
      Object.defineProperty(process, 'platform', { value: savedPlatform });
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
