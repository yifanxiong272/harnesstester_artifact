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
import * as RgLocator from '../../src/tools/support/rg-locator';
import { Readable } from 'node:stream';

// Download-branch tests mock `tar.extract` so the archive layout is
// controlled by the test, not the real CDN. `fetch` is replaced per-test
// on `globalThis` to drive the failure and success paths.
vi.mock('tar', () => ({ extract: vi.fn() }));

describe('findExistingRg', () => {
  let fakeShare: string;
  let savedPath: string | undefined;
  beforeEach(() => {
    fakeShare = join(tmpdir(), `kimi-rg-${String(Date.now())}-${String(Math.random()).slice(2)}`);
    mkdirSync(join(fakeShare, 'bin'), { recursive: true });
    savedPath = process.env['PATH'];
    // Empty PATH → rules out step 1 (system-path) for the default case.
    process.env['PATH'] = '';
  });
  afterEach(() => {
    rmSync(fakeShare, { recursive: true, force: true });
    if (savedPath === undefined) delete process.env['PATH'];
    else process.env['PATH'] = savedPath;
  });

  it('returns undefined when no rg anywhere', async () => {
    const result = await findExistingRg(fakeShare);
    expect(result).toBeUndefined();
  });

  it('resolves from share-dir when cached', async () => {
    const cached = join(fakeShare, 'bin', process.platform === 'win32' ? 'rg.exe' : 'rg');
    writeFileSync(cached, '#!/bin/sh\necho ripgrep 15.0.0\n');
    chmodSync(cached, 0o755);
    const result = await findExistingRg(fakeShare);
    expect(result).toEqual({ path: cached, source: 'share-bin-cached' });
  });

  it('prefers system PATH over share-dir when both are available', async () => {
    // Stage a fake rg on PATH.
    const pathDir = join(fakeShare, 'path');
    mkdirSync(pathDir, { recursive: true });
    const onPath = join(pathDir, process.platform === 'win32' ? 'rg.exe' : 'rg');
    writeFileSync(onPath, '#!/bin/sh\n');
    chmodSync(onPath, 0o755);
    process.env['PATH'] = pathDir;
    // Also stage a cached one to confirm the order.
    const cached = join(fakeShare, 'bin', process.platform === 'win32' ? 'rg.exe' : 'rg');
    writeFileSync(cached, '#!/bin/sh\n');
    chmodSync(cached, 0o755);
    const result = await findExistingRg(fakeShare);
    expect(result?.source).toBe('system-path');
    expect(result?.path).toBe(onPath);
  });
});

describe('detectTarget', () => {
  let savedArch: string;
  let savedPlatform: string;
  beforeEach(() => {
    savedArch = process.arch;
    savedPlatform = process.platform;
  });
  afterEach(() => {
    Object.defineProperty(process, 'arch', { value: savedArch });
    Object.defineProperty(process, 'platform', { value: savedPlatform });
  });

  function setPlatform(arch: string, platform: string): void {
    Object.defineProperty(process, 'arch', { value: arch });
    Object.defineProperty(process, 'platform', { value: platform });
  }

  it('darwin arm64 → aarch64-apple-darwin', () => {
    setPlatform('arm64', 'darwin');
    expect(detectTarget()).toBe('aarch64-apple-darwin');
  });
  it('darwin x64 → x86_64-apple-darwin', () => {
    setPlatform('x64', 'darwin');
    expect(detectTarget()).toBe('x86_64-apple-darwin');
  });
  it('linux x64 → x86_64-unknown-linux-musl', () => {
    setPlatform('x64', 'linux');
    expect(detectTarget()).toBe('x86_64-unknown-linux-musl');
  });
  it('linux arm64 → aarch64-unknown-linux-gnu', () => {
    setPlatform('arm64', 'linux');
    expect(detectTarget()).toBe('aarch64-unknown-linux-gnu');
  });
  it('win32 x64 → x86_64-pc-windows-msvc', () => {
    setPlatform('x64', 'win32');
    expect(detectTarget()).toBe('x86_64-pc-windows-msvc');
  });
  it('unsupported arch → undefined', () => {
    setPlatform('mips', 'linux');
    expect(detectTarget()).toBeUndefined();
  });
});

describe('rgUnavailableMessage', () => {
  it('surfaces the underlying cause and install hints', () => {
    const msg = rgUnavailableMessage(new Error('fetch failed'));
    expect(msg).toContain('fetch failed');
    expect(msg).toContain('brew install ripgrep');
    expect(msg).toContain('https://github.com/BurntSushi/ripgrep');
  });

  it('handles non-Error causes (string, unknown)', () => {
    const a = rgUnavailableMessage('boom');
    expect(a).toContain('boom');
    const b = rgUnavailableMessage(42);
    expect(b).toContain('unknown error');
  });
});

describe('verifyArchiveChecksum', () => {
  let fakeDir: string;
  beforeEach(() => {
    fakeDir = join(tmpdir(), `kimi-rg-sha-${String(Date.now())}-${String(Math.random()).slice(2)}`);
    mkdirSync(fakeDir, { recursive: true });
  });
  afterEach(() => {
    rmSync(fakeDir, { recursive: true, force: true });
  });

  it('accepts a file whose SHA-256 matches the expected digest', async () => {
    const archivePath = join(fakeDir, 'archive.tar.gz');
    const payload = Buffer.from('trusted archive bytes', 'utf8');
    writeFileSync(archivePath, payload);
    const expectedSha256 = createHash('sha256').update(payload).digest('hex');

    await expect(
      verifyArchiveChecksum(archivePath, 'archive.tar.gz', expectedSha256),
    ).resolves.toBeUndefined();
  });

  it('rejects a file whose SHA-256 differs from the expected digest', async () => {
    const archivePath = join(fakeDir, 'archive.tar.gz');
    writeFileSync(archivePath, 'tampered archive bytes');

    await expect(
      verifyArchiveChecksum(archivePath, 'archive.tar.gz', '0'.repeat(64)),
    ).rejects.toThrow(/checksum mismatch/);
  });
});

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

  it('surfaces a network error when fetch rejects', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('network unreachable')) as typeof fetch;
    await expect(ensureRgPath({ shareDir: fakeShare })).rejects.toThrow(/network unreachable/);
  });

  it('does not start bootstrap work when the caller is already aborted', async () => {
    const controller = new AbortController();
    controller.abort();
    const fetchMock = vi.fn();
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(
      ensureRgPath({ shareDir: fakeShare, signal: controller.signal }),
    ).rejects.toHaveProperty('name', 'AbortError');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('does not start bootstrap work when aborted after lookup misses', async () => {
    const controller = new AbortController();
    const fetchMock = vi.fn(() => new Promise<Response>(() => {}));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    let rejectFirstStat: ((error: Error) => void) | undefined;
    let statCalls = 0;
    const statMock = vi.fn(() => {
      statCalls += 1;
      if (statCalls === 1) {
        return new Promise<never>((_resolve, reject) => {
          rejectFirstStat = reject;
        });
      }
      return Promise.reject(Object.assign(new Error('ENOENT'), { code: 'ENOENT' }));
    });

    vi.resetModules();
    vi.doMock('node:fs/promises', async () => {
      const actual = await vi.importActual<typeof FsPromises>('node:fs/promises');
      return { ...actual, stat: statMock };
    });

    try {
      const { ensureRgPath: isolatedEnsureRgPath } =
        await import('../../src/tools/support/rg-locator');
      const resultPromise = isolatedEnsureRgPath({
        shareDir: fakeShare,
        signal: controller.signal,
      });

      await vi.waitFor(() => {
        expect(statMock).toHaveBeenCalledTimes(1);
      });
      controller.abort();
      rejectFirstStat?.(Object.assign(new Error('ENOENT'), { code: 'ENOENT' }));

      await expect(resultPromise).rejects.toHaveProperty('name', 'AbortError');
      await new Promise((resolve) => {
        setTimeout(resolve, 20);
      });

      expect(statMock).toHaveBeenCalledTimes(1);
      expect(fetchMock).not.toHaveBeenCalled();
    } finally {
      vi.doUnmock('node:fs/promises');
      vi.resetModules();
    }
  });

  it('aborts the current caller wait while shared bootstrap work continues', async () => {
    const controller = new AbortController();
    let resolveFetch: (response: {
      ok: false;
      status: number;
      statusText: string;
      body: null;
    }) => void = () => {};
    const fetchResponse = new Promise<{
      ok: false;
      status: number;
      statusText: string;
      body: null;
    }>((resolve) => {
      resolveFetch = resolve;
    });
    globalThis.fetch = vi.fn(() => fetchResponse) as unknown as typeof fetch;

    const resultPromise = ensureRgPath({ shareDir: fakeShare, signal: controller.signal });
    await vi.waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    });

    controller.abort();
    await expect(resultPromise).rejects.toHaveProperty('name', 'AbortError');

    resolveFetch({ ok: false, status: 499, statusText: 'Client Closed', body: null });
    await expect(ensureRgPath({ shareDir: fakeShare })).rejects.toThrow(/HTTP 499 Client Closed/);
  });

  it('surfaces HTTP failure (non-2xx response) with status + statusText', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      body: null,
    }) as unknown as typeof fetch;
    await expect(ensureRgPath({ shareDir: fakeShare })).rejects.toThrow(/HTTP 404 Not Found/);
  });

  it('fetches ripgrep over HTTPS', async () => {
    const body = bodyFromBuffer(Buffer.from('not a real archive', 'utf8'));
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      body,
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(ensureRgPath({ shareDir: fakeShare })).rejects.toThrow();

    const [url] = fetchMock.mock.calls[0] as [string];
    expect(new URL(url).protocol).toBe('https:');
  });

  it('rejects archives that do not match the pinned SHA-256 before extraction', async () => {
    const tarMock = vi.mocked(extractTar);
    tarMock.mockClear();
    const body = bodyFromBuffer(Buffer.from('tampered archive', 'utf8'));
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      body,
    }) as unknown as typeof fetch;

    await expect(ensureRgPath({ shareDir: fakeShare })).rejects.toThrow(/checksum/i);

    expect(tarMock).not.toHaveBeenCalled();
    expect(existsSync(join(fakeShare, 'bin', process.platform === 'win32' ? 'rg.exe' : 'rg'))).toBe(
      false,
    );
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

describe('ensureRgPath Windows download branch', () => {
  let fakeShare: string;
  let savedPath: string | undefined;
  let savedFetch: typeof globalThis.fetch | undefined;
  let savedArch: string;
  let savedPlatform: string;
  beforeEach(() => {
    fakeShare = join(
      tmpdir(),
      `kimi-rg-win-${String(Date.now())}-${String(Math.random()).slice(2)}`,
    );
    mkdirSync(join(fakeShare, 'bin'), { recursive: true });
    savedPath = process.env['PATH'];
    process.env['PATH'] = ''; // force past whichRg
    savedFetch = globalThis.fetch;
    savedArch = process.arch;
    savedPlatform = process.platform;
    // Simulate a Windows host end-to-end — `rgBinaryName()`, `whichRg()`
    // (PATH sep), and `detectTarget()` all key off these two values.
    Object.defineProperty(process, 'arch', { value: 'x64' });
    Object.defineProperty(process, 'platform', { value: 'win32' });
  });
  afterEach(() => {
    rmSync(fakeShare, { recursive: true, force: true });
    if (savedPath === undefined) delete process.env['PATH'];
    else process.env['PATH'] = savedPath;
    if (savedFetch === undefined) {
      delete (globalThis as unknown as { fetch?: typeof fetch }).fetch;
    } else {
      globalThis.fetch = savedFetch;
    }
    Object.defineProperty(process, 'arch', { value: savedArch });
    Object.defineProperty(process, 'platform', { value: savedPlatform });
    vi.restoreAllMocks();
  });

  it('fetches the .zip URL (not .tar.gz) on Windows target', async () => {
    const zipBuf = await buildFixtureZip([
      {
        name: 'ripgrep-15.0.0-x86_64-pc-windows-msvc/rg.exe',
        content: Buffer.from('MZfake-pe-bytes', 'utf8'),
      },
    ]);
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      body: bodyFromBuffer(zipBuf),
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(ensureRgPath({ shareDir: fakeShare })).rejects.toThrow(/checksum mismatch/);

    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toMatch(/ripgrep-15\.0\.0-x86_64-pc-windows-msvc\.zip$/);
  });

  it('extracts rg.exe into <shareDir>/bin/rg.exe', async () => {
    const payload = Buffer.from('MZfake-pe-bytes-extracted', 'utf8');
    const zipBuf = await buildFixtureZip([
      {
        name: 'ripgrep-15.0.0-x86_64-pc-windows-msvc/rg.exe',
        content: payload,
      },
    ]);

    const archivePath = join(fakeShare, 'fixture.zip');
    const installed = join(fakeShare, 'bin', 'rg.exe');
    writeFileSync(archivePath, zipBuf);

    await extractRgFromZip(archivePath, installed);

    expect(existsSync(installed)).toBe(true);
    expect(readFileSync(installed)).toEqual(payload);
  });

  it('throws with "CDN content may have changed" when the zip omits rg.exe', async () => {
    // Archive is well-formed but holds the wrong entry — mirrors the
    // Counterpart to the Linux third-download test's sentinel.
    const zipBuf = await buildFixtureZip([{ name: 'README.md', content: Buffer.from('readme') }]);
    const archivePath = join(fakeShare, 'fixture.zip');
    const installed = join(fakeShare, 'bin', 'rg.exe');
    writeFileSync(archivePath, zipBuf);

    await expect(extractRgFromZip(archivePath, installed)).rejects.toThrow(
      /CDN content may have changed/,
    );
  });

  it('surfaces HTTP failure on Windows with status + statusText', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      statusText: 'Bad Gateway',
      body: null,
    }) as unknown as typeof fetch;
    await expect(ensureRgPath({ shareDir: fakeShare })).rejects.toThrow(/HTTP 502 Bad Gateway/);
  });
});

  it('downloads, extracts (tar.gz) and installs rg into <shareDir>/bin on non-Windows platforms', async () => {
    // Fresh module load so our module-level mocks take effect.
    vi.resetModules();
  
    const savedPath = process.env['PATH'];
    process.env['PATH'] = ''; // force download branch
  
    // Temporaries for process tuning
    const savedArch = process.arch;
    const savedPlatform = process.platform;
    Object.defineProperty(process, 'arch', { value: 'x64' });
    Object.defineProperty(process, 'platform', { value: 'linux' });
  
    // Create a fake share dir
    const fakeShare = join(
      tmpdir(),
      `kimi-rg-install-${String(Date.now())}-${String(Math.random()).slice(2)}`,
    );
    mkdirSync(join(fakeShare, 'bin'), { recursive: true });
  
    // The pinned SHA for the linux x86_64 tar.gz (copied from source's RG_ARCHIVE_SHA256)
    const expectedSha =
      '253ad0fd5fef0d64cba56c70dccdacc1916d4ed70ad057cc525fcdb0c3bbd2a7';
  
    // Mock node:crypto.createHash so verifyArchiveChecksum believes the digest matches
    vi.doMock('node:crypto', () => {
      return {
        createHash: (_alg: string) => ({
          update: (_data: unknown) => ({
            digest: (_enc?: string) => expectedSha,
          }),
        }),
      };
    });
  
    // Mock tar.extract to materialize the expected extracted binary path the real code checks for.
    vi.doMock('tar', () => {
      return {
        extract: async (opts: any) => {
          const cwd: string = opts.cwd;
          const targetDir = join(
            cwd,
            `ripgrep-15.0.0-x86_64-unknown-linux-musl`,
          );
          mkdirSync(targetDir, { recursive: true });
          const extractedBin = join(targetDir, process.platform === 'win32' ? 'rg.exe' : 'rg');
          // Write the file the install step will copy into the staged dir.
          writeFileSync(extractedBin, 'extracted-rg-binary-content', 'utf8');
        },
      };
    });
  
    // Import the module under test after setting up mocks.
    const { ensureRgPath } = await import('../../src/tools/support/rg-locator');
  
    // Mock fetch to return some body stream (contents are irrelevant because crypto was mocked).
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      body: bodyFromBuffer(Buffer.from('fake-tar-bytes', 'utf8')),
    }) as unknown as typeof fetch;
  
    try {
      const res = await ensureRgPath({ shareDir: fakeShare });
      expect(res.source).toBe('share-bin-downloaded');
      const dest = join(fakeShare, 'bin', process.platform === 'win32' ? 'rg.exe' : 'rg');
      expect(res.path).toBe(dest);
      // Destination binary should exist and contain the content staged by our tar.extract mock.
      expect(existsSync(dest)).toBe(true);
      expect(readFileSync(dest, 'utf8')).toBe('extracted-rg-binary-content');
    } finally {
      // cleanup mocks and environment
      vi.doUnmock('node:crypto');
      vi.doUnmock('tar');
      vi.resetModules();
      if (savedPath === undefined) delete process.env['PATH'];
      else process.env['PATH'] = savedPath;
      Object.defineProperty(process, 'arch', { value: savedArch });
      Object.defineProperty(process, 'platform', { value: savedPlatform });
      // Remove fake share dir
      rmSync(fakeShare, { recursive: true, force: true });
      // Restore global fetch
      // (Top-level afterEach in the suite will also revert if necessary)
      delete (globalThis as unknown as { fetch?: typeof fetch }).fetch;
    }
  });


  it('ensureRgPath rejects when platform/arch are unsupported', async () => {
    const fakeShare = join(
      tmpdir(),
      `kimi-rg-unsupported-${String(Date.now())}-${String(Math.random()).slice(2)}`,
    );
    mkdirSync(join(fakeShare, 'bin'), { recursive: true });
    const savedPath = process.env['PATH'];
    process.env['PATH'] = ''; // force download branch
  
    const savedArch = process.arch;
    const savedPlatform = process.platform;
    // Pick values that detectTarget() will not recognise
    Object.defineProperty(process, 'arch', { value: 'mips' });
    Object.defineProperty(process, 'platform', { value: 'sunos' });
  
    try {
      await expect(ensureRgPath({ shareDir: fakeShare })).rejects.toThrow(
        /Unsupported platform\/arch/,
      );
    } finally {
      // restore
      if (savedPath === undefined) delete process.env['PATH'];
      else process.env['PATH'] = savedPath;
      Object.defineProperty(process, 'arch', { value: savedArch });
      Object.defineProperty(process, 'platform', { value: savedPlatform });
      rmSync(fakeShare, { recursive: true, force: true });
    }
  });


  it('extractRgFromZip rejects when the read stream errors during pipeline', async () => {
    vi.resetModules();
    vi.doMock('yauzl', () => ({
      fromBuffer: (_buf: Buffer, _opts: unknown, cb: (err: Error | null, zipfile?: any) => void) => {
        const handlers: Record<string, Function[]> = {};
        const binName = process.platform === 'win32' ? 'rg.exe' : 'rg';
        const zipfile = {
          on(event: string, fn: Function) {
            handlers[event] = handlers[event] || [];
            handlers[event].push(fn);
          },
          readEntry() {
            const entry = { fileName: `ripgrep-${String(Date.now())}/${binName}` };
            (handlers['entry'] || []).forEach((h) => h(entry));
            (handlers['end'] || []).forEach((h) => h());
          },
          openReadStream(_entry: any, cb2: (err: Error | null, stream?: NodeJS.ReadableStream) => void) {
            // Return a Node Readable that emits an error as soon as it's consumed.
            const { Readable } = require('node:stream');
            const stream = new Readable({
              read() {
                // emit an error to force pipeline rejection
                this.emit('error', new Error('stream pipeline failure'));
              },
            });
            // Defer to mimic async open
            setImmediate(() => cb2(null, stream));
          },
          close() {
            /* noop */
          },
        };
        setImmediate(() => cb(null, zipfile));
      },
    }));
    try {
      const { extractRgFromZip } = await import('../../src/tools/support/rg-locator');
      const fakeDir = join(tmpdir(), `kimi-rg-zip-pipeerr-${String(Date.now())}`);
      mkdirSync(fakeDir, { recursive: true });
      const archivePath = join(fakeDir, 'fixture.zip');
      writeFileSync(archivePath, Buffer.from('zip-like-bytes'));
      const destination = join(fakeDir, process.platform === 'win32' ? 'rg.exe' : 'rg');
      await expect(extractRgFromZip(archivePath, destination)).rejects.toThrow(/stream pipeline failure/);
      rmSync(fakeDir, { recursive: true, force: true });
    } finally {
      vi.doUnmock('yauzl');
      vi.resetModules();
    }
  });


  it('extractRgFromZip rejects when openReadStream returns an error', async () => {
    vi.resetModules();
    // Build a fake `yauzl` implementation that calls back a zipfile object
    // whose openReadStream reports an error for the matching entry.
    vi.doMock('yauzl', () => ({
      fromBuffer: (_buf: Buffer, _opts: unknown, cb: (err: Error | null, zipfile?: any) => void) => {
        const handlers: Record<string, Function[]> = {};
        const binName = process.platform === 'win32' ? 'rg.exe' : 'rg';
        const zipfile = {
          on(event: string, fn: Function) {
            handlers[event] = handlers[event] || [];
            handlers[event].push(fn);
          },
          readEntry() {
            // Simulate a single entry matching the binary; trigger 'entry' once
            const entry = { fileName: `someprefix/${binName}` };
            (handlers['entry'] || []).forEach((h) => h(entry));
            // Then trigger 'end' to simulate no more entries
            (handlers['end'] || []).forEach((h) => h());
          },
          openReadStream(_entry: any, cb2: (err: Error | null, stream?: NodeJS.ReadableStream) => void) {
            // Simulate failing to open the entry stream
            cb2(new Error('openReadStream failed'), undefined);
          },
          close() {
            /* noop */
          },
        };
        // Defer callback to mimic async behavior
        setImmediate(() => cb(null, zipfile));
      },
    }));
    try {
      const { extractRgFromZip } = await import('../../src/tools/support/rg-locator');
      const fakeDir = join(tmpdir(), `kimi-rg-zip-streamerr-${String(Date.now())}`);
      mkdirSync(fakeDir, { recursive: true });
      const archivePath = join(fakeDir, 'fixture.zip');
      writeFileSync(archivePath, Buffer.from('zip-like-bytes'));
      const destination = join(fakeDir, process.platform === 'win32' ? 'rg.exe' : 'rg');
      await expect(extractRgFromZip(archivePath, destination)).rejects.toThrow(/Failed to read .* from archive: openReadStream failed/);
      rmSync(fakeDir, { recursive: true, force: true });
    } finally {
      vi.doUnmock('yauzl');
      vi.resetModules();
    }
  });


  it('extractRgFromZip rejects when yauzl fails to open archive', async () => {
    // Isolate module so we can mock `yauzl.fromBuffer` to simulate an open error.
    vi.resetModules();
    vi.doMock('yauzl', () => ({
      fromBuffer: (_buf: Buffer, _opts: unknown, cb: (err: Error | null, zipfile?: unknown) => void) =>
        cb(new Error('failed to open zip'), undefined),
    }));
    try {
      const { extractRgFromZip } = await import('../../src/tools/support/rg-locator');
      const fakeDir = join(tmpdir(), `kimi-rg-zip-open-${String(Date.now())}`);
      mkdirSync(fakeDir, { recursive: true });
      const archivePath = join(fakeDir, 'broken.zip');
      writeFileSync(archivePath, Buffer.from('not a zip'));
      const destination = join(fakeDir, 'rg.exe');
      await expect(extractRgFromZip(archivePath, destination)).rejects.toThrow(/Failed to open ripgrep archive/);
      rmSync(fakeDir, { recursive: true, force: true });
    } finally {
      vi.doUnmock('yauzl');
      vi.resetModules();
    }
  });

