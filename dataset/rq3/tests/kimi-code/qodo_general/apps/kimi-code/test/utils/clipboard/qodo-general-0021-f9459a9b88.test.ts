import { mkdtempSync, rmSync, truncateSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

import { describe, expect, it, vi } from 'vitest';

import { ClipboardMediaError, readClipboardMedia } from '#/utils/clipboard/clipboard-image';
import type { ClipboardModule } from '#/utils/clipboard/clipboard-native';

function png(width: number, height: number): Uint8Array {
  const bytes = new Uint8Array(24);
  bytes.set([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a], 0);
  bytes.set([0x00, 0x00, 0x00, 0x0d], 8);
  bytes.set([0x49, 0x48, 0x44, 0x52], 12);
  bytes[16] = (width >>> 24) & 0xff;
  bytes[17] = (width >>> 16) & 0xff;
  bytes[18] = (width >>> 8) & 0xff;
  bytes[19] = width & 0xff;
  bytes[20] = (height >>> 24) & 0xff;
  bytes[21] = (height >>> 16) & 0xff;
  bytes[22] = (height >>> 8) & 0xff;
  bytes[23] = height & 0xff;
  return bytes;
}

function fakeClipboard(overrides: Partial<ClipboardModule>): ClipboardModule {
  return {
    hasImage: vi.fn(() => false),
    getImageBinary: vi.fn(async () => []),
    ...overrides,
  };
}

function noMacOsPaths(): { stdout: Buffer; ok: boolean } {
  return { stdout: Buffer.alloc(0), ok: false };
}

describe('readClipboardMedia', () => {
  it('reads a copied image file from its real path instead of the Finder preview icon', async () => {
    const dir = mkdtempSync(join(tmpdir(), 'kimi-code-clip-'));
    try {
      const imagePath = join(dir, 'photo.png');
      const imageBytes = png(12, 34);
      writeFileSync(imagePath, imageBytes);
      const getImageBinary = vi.fn(async () => Array.from(png(1, 1)));
      const clip = fakeClipboard({
        availableFormats: vi.fn(() => ['public.file-url', 'public.png']),
        hasImage: vi.fn(() => true),
        getImageBinary,
      });
      const runCommand = vi.fn(() => ({ stdout: Buffer.from(`${imagePath}\n`), ok: true }));

      const media = await readClipboardMedia({ platform: 'darwin', clipboard: clip, runCommand });

      expect(media).toEqual({
        kind: 'image',
        bytes: imageBytes,
        mimeType: 'image/png',
      });
      expect(getImageBinary).not.toHaveBeenCalled();
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it('prefers a video file URL over an available image preview', async () => {
    const dir = mkdtempSync(join(tmpdir(), 'kimi-code-clip-'));
    try {
      const videoPath = join(dir, 'sample.mov');
      writeFileSync(videoPath, new Uint8Array([0, 1, 2]));
      const getImageBinary = vi.fn(async () => [0x89, 0x50, 0x4e, 0x47]);
      const clip = fakeClipboard({
        availableFormats: vi.fn(() => ['public.file-url', 'public.png']),
        hasText: vi.fn(() => true),
        getText: vi.fn(async () => pathToFileURL(videoPath).toString()),
        hasImage: vi.fn(() => true),
        getImageBinary,
      });

      const media = await readClipboardMedia({
        platform: 'darwin',
        clipboard: clip,
        runCommand: noMacOsPaths,
      });

      expect(media?.kind).toBe('video');
      expect(media).toMatchObject({
        mimeType: 'video/quicktime',
        filename: 'sample.mov',
        sourcePath: videoPath,
      });
      expect(getImageBinary).not.toHaveBeenCalled();
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it('falls back to native image bytes when no video file is present', async () => {
    const clip = fakeClipboard({
      availableFormats: vi.fn(() => ['public.png']),
      hasText: vi.fn(() => false),
      hasImage: vi.fn(() => true),
      getImageBinary: vi.fn(async () => [0x89, 0x50, 0x4e, 0x47]),
    });

    const media = await readClipboardMedia({
      platform: 'darwin',
      clipboard: clip,
      runCommand: noMacOsPaths,
    });

    expect(media).toEqual({
      kind: 'image',
      bytes: new Uint8Array([0x89, 0x50, 0x4e, 0x47]),
      mimeType: 'image/png',
    });
  });

  it('does not consume file-like clipboard image previews when no real file path is readable', async () => {
    const getImageBinary = vi.fn(async () => Array.from(png(1, 1)));
    const clip = fakeClipboard({
      availableFormats: vi.fn(() => ['public.file-url', 'public.png']),
      hasImage: vi.fn(() => true),
      getImageBinary,
    });

    const media = await readClipboardMedia({
      platform: 'darwin',
      clipboard: clip,
      runCommand: noMacOsPaths,
    });

    expect(media).toBeNull();
    expect(getImageBinary).not.toHaveBeenCalled();
  });

  it('rejects pasted videos larger than 100 MB', async () => {
    const dir = mkdtempSync(join(tmpdir(), 'kimi-code-clip-'));
    try {
      const videoPath = resolve(dir, 'too-big.mp4');
      writeFileSync(videoPath, new Uint8Array([0]));
      truncateSync(videoPath, 101 * 1024 * 1024);
      const clip = fakeClipboard({
        availableFormats: vi.fn(() => ['public.file-url']),
        hasText: vi.fn(() => true),
        getText: vi.fn(async () => pathToFileURL(videoPath).toString()),
      });

      await expect(
        readClipboardMedia({
          platform: 'darwin',
          clipboard: clip,
          runCommand: noMacOsPaths,
        }),
      ).rejects.toThrow(ClipboardMediaError);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it('falls back to PowerShell on WSL and reads a temporary PNG file', async () => {
    vi.resetModules();
  
    // Make randomUUID deterministic so the temp path is predictable.
    vi.doMock('node:crypto', () => ({ randomUUID: () => 'fixed-uuid' }));
  
    // Prepare the temp file that the code will try to read after PowerShell reports success.
    const tmpFile = join(tmpdir(), `kimi-wsl-clip-fixed-uuid.png`);
    const pngBytes = png(8, 8);
    try {
      writeFileSync(tmpFile, pngBytes);
  
      // Provide a runCommand implementation that forces the PowerShell path.
      let runCommandImpl = (command: string, args: string[], opts?: any) => {
        // Simulate wl-paste and xclip failure so the WSL PowerShell fallback is used.
        if (command === 'wl-paste' || command === 'xclip') {
          return { stdout: Buffer.alloc(0), ok: false };
        }
        // wslpath -w should succeed and return a Windows-style path (content is not parsed further).
        if (command === 'wslpath') {
          return { stdout: Buffer.from('C:\\\\temp\\\\kimi-wsl-clip-fixed-uuid.png\n'), ok: true };
        }
        // powershell should report 'ok' to indicate it saved the image.
        if (command === 'powershell.exe') {
          return { stdout: Buffer.from('ok\n'), ok: true };
        }
        return { stdout: Buffer.alloc(0), ok: false };
      };
  
      vi.doMock('#/utils/clipboard/clipboard-common', () => {
        return {
          DEFAULT_LIST_TIMEOUT_MS: 100,
          DEFAULT_POWERSHELL_TIMEOUT_MS: 100,
          SUPPORTED_IMAGE_MIME_TYPES: ['image/png', 'image/jpeg'],
          baseMimeType: (t: string) => t.split(';')[0].trim(),
          isFileLikeNativeFormat: () => false,
          isSupportedImageMimeType: (t: string) => t.startsWith('image/'),
          // Indicate we are in WSL so the PowerShell fallback is used.
          isWaylandSession: () => false,
          isWSL: () => true,
          parseTargetList: (buf: Buffer) => buf.toString('utf-8').split(/\s+/).filter(Boolean),
          runCommand: (command: string, args: string[], opts?: any) => runCommandImpl(command, args, opts),
          safeAvailableFormats: () => [],
        };
      });
  
      const mod = await import('#/utils/clipboard/clipboard-image');
  
      const media = await mod.readClipboardMedia({ platform: 'linux', env: {}, clipboard: null });
  
      expect(media).not.toBeNull();
      expect(media?.kind).toBe('image');
      expect(media?.mimeType).toBe('image/png');
      expect(media && (media as any).bytes).toEqual(pngBytes);
    } finally {
      // Ensure we clean up the temp file created for the test.
      try {
        rmSync(tmpFile, { force: true });
      } catch {
        // ignore cleanup errors
      }
    }
  });

});
