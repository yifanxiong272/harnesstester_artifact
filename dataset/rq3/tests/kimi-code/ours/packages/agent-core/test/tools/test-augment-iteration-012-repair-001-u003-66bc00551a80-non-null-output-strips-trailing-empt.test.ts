import { Readable, type Writable } from 'node:stream';

import type { KaosProcess, StatResult } from '@moonshot-ai/kaos';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { type GrepInput, GrepInputSchema, GrepTool } from '../../src/tools/builtin/file/grep';
import { SENSITIVE_DOT_VARIANT_SUFFIXES } from '../../src/tools/policies/sensitive';
import { ensureRgPath } from '../../src/tools/support/rg-locator';
import type { WorkspaceConfig } from '../../src/tools/support/workspace';
import { createFakeKaos, toolContentString } from './fixtures/fake-kaos';
import { executeTool } from './fixtures/execute-tool';

vi.mock('../../src/tools/support/rg-locator', () => ({
  ensureRgPath: vi.fn(async () => ({ path: '/mock/rg', source: 'system-path' })),
  rgUnavailableMessage: (cause: unknown) =>
    `rg unavailable: ${cause instanceof Error ? cause.message : String(cause)}`,
}));

const signal = new AbortController().signal;
const workspace: WorkspaceConfig = { workspaceDir: '/workspace', additionalDirs: ['/extra'] };
// `--max-columns` is applied only outside `content` output mode, so it is kept
// as a separate segment: non-content modes use `DEFAULT_RG_ARGS`, while
// `content` mode uses `CONTENT_RG_ARGS` without the column cap.
const MAX_COLUMNS_RG_ARGS = ['--max-columns', '500'] as const;
const COMMON_RG_ARGS = [
  '--null',
  '--glob',
  '!.git',
  '--glob',
  '!.svn',
  '--glob',
  '!.hg',
  '--glob',
  '!.bzr',
  '--glob',
  '!.jj',
  '--glob',
  '!.sl',
] as const;
const DEFAULT_RG_ARGS = ['--hidden', ...MAX_COLUMNS_RG_ARGS, ...COMMON_RG_ARGS] as const;
const CONTENT_RG_ARGS = ['--hidden', ...COMMON_RG_ARGS] as const;
const SENSITIVE_KEY_BASENAMES = ['id_rsa', 'id_ed25519', 'id_ecdsa'] as const;
const SENSITIVE_KEY_RG_ARGS = SENSITIVE_KEY_BASENAMES.flatMap((basename) => [
  '--glob',
  `!**/${basename}`,
  '--glob',
  `!**/${basename}[-_]*`,
  ...SENSITIVE_DOT_VARIANT_SUFFIXES.flatMap((suffix) => [
    '--glob',
    `!**/${basename}${suffix}`,
  ]),
]);
const SENSITIVE_RG_ARGS = [
  '--glob',
  '!**/.env',
  ...SENSITIVE_KEY_RG_ARGS,
  '--glob',
  '!**/.aws/credentials',
  '--glob',
  '!**/.aws/credentials/**',
  '--glob',
  '!**/.gcp/credentials',
  '--glob',
  '!**/.gcp/credentials/**',
] as const;

function processWithOutput(stdout: string, stderr = '', exitCode = 0): KaosProcess {
  const stdoutStream = Readable.from([stdout]);
  const stderrStream = Readable.from([stderr]);
  return {
    stdin: { end: vi.fn(), write: vi.fn() } as unknown as Writable,
    stdout: stdoutStream,
    stderr: stderrStream,
    pid: 123,
    exitCode,
    wait: vi.fn().mockResolvedValue(exitCode),
    kill: vi.fn(async () => {}),
    dispose: vi.fn(async () => {
      stdoutStream.destroy();
      stderrStream.destroy();
    }),
  };
}

function statResult(mtime: number): StatResult {
  return {
    stMode: 0o100000,
    stIno: 1,
    stDev: 1,
    stNlink: 1,
    stUid: 0,
    stGid: 0,
    stSize: 0,
    stAtime: mtime,
    stMtime: mtime,
    stCtime: mtime,
  };
}

function processThatExitsOnKill(stdout: string, stderr = '', exitCode = 143): KaosProcess {
  let currentExitCode: number | null = null;
  let resolveWait: (code: number) => void;
  const waitPromise = new Promise<number>((resolve) => {
    resolveWait = resolve;
  });
  const stdoutStream = Readable.from(stdout === '' ? [] : [stdout]);
  const stderrStream = Readable.from(stderr === '' ? [] : [stderr]);

  return {
    stdin: { end: vi.fn(), write: vi.fn() } as unknown as Writable,
    stdout: stdoutStream,
    stderr: stderrStream,
    pid: 123,
    get exitCode() {
      return currentExitCode;
    },
    wait: vi.fn(() => waitPromise),
    kill: vi.fn(async () => {
      currentExitCode = exitCode;
      resolveWait(exitCode);
    }),
    dispose: vi.fn(async () => {
      stdoutStream.destroy();
      stderrStream.destroy();
    }),
  };
}

function context(args: GrepInput, abortSignal = signal) {
  return { turnId: '0', toolCallId: 'call_grep', args, signal: abortSignal };
}

function nullRecord(filePath: string, payload = ''): string {
  return `${filePath}\0${payload}`;
}

afterEach(() => {
  vi.useRealTimers();
});

describe('GrepTool', () => {















































































  __testAugmentVitest_77360762ae29.it("non_null_output_strips_trailing_empty_and_cr_round_012", async () => {
    // Non-null (legacy) ripgrep output with CR line endings and a trailing empty line
    const raw = 'C:/some/path/file.txt:1:hello\r\nC:/some/path/other.txt:2:bye\r\n\n';
    const exec = __testAugmentVitest_77360762ae29.vi.fn().mockResolvedValue(processWithOutput(raw));
    const tool = new GrepTool(createFakeKaos({ exec, pathClass: () => 'win32' }), {
      workspaceDir: 'C:/some/path',
      additionalDirs: [],
    });

    const result = await executeTool(tool, context({ pattern: 'x', output_mode: 'content', '-n': true }));
    const out = toolContentString(result).split('\n').filter((l) => l.trim() !== '');

    // splitRgLines should remove the trailing empty line and strip '\r' characters
    __testAugmentVitest_77360762ae29.expect(out).toContain('file.txt:1:hello');
    __testAugmentVitest_77360762ae29.expect(out).toContain('other.txt:2:bye');
  });
});

import * as __testAugmentVitest_77360762ae29 from "vitest";

const __testAugmentLoadTarget_98bfc6a518f9 = async () => {
  __testAugmentVitest_77360762ae29.vi.doUnmock("../../src/tools/builtin/file/grep.js");
  __testAugmentVitest_77360762ae29.vi.resetModules();
  return import("../../src/tools/builtin/file/grep.js");
};
