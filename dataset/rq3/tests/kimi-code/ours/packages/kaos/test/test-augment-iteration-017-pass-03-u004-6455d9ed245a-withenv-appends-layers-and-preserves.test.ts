import { EventEmitter } from 'node:events';

import { KaosFileExistsError, KaosValueError } from '#/errors';
import {
  KaosConnectionError,
  KaosFileNotFoundError,
  KaosPermissionError,
  KaosSSHError,
  SSHKaos,
} from '#/ssh';
import type { StatResult } from '#/types';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, test } from 'vitest';

// Environment variable configuration for SSH connection
const SSH_SMOKE = process.env['KAOS_SSH_SMOKE'] === '1';
const SSH_HOST = process.env['KAOS_SSH_HOST'] ?? '127.0.0.1';
const SSH_PORT = Number(process.env['KAOS_SSH_PORT'] ?? '22');
const SSH_USERNAME = process.env['KAOS_SSH_USERNAME'];
const SSH_PASSWORD = process.env['KAOS_SSH_PASSWORD'];
const SSH_KEY_PATHS = process.env['KAOS_SSH_KEY_PATHS']?.split(',').filter(Boolean);
const SSH_KEY_CONTENTS = process.env['KAOS_SSH_KEY_CONTENTS']?.split('|||').filter(Boolean);

// S_IFMT mask and file type constants
const S_IFMT = 0o170000;
const S_IFDIR = 0o040000;
const S_IFREG = 0o100000;

async function streamToBuffer(stream: NodeJS.ReadableStream): Promise<Buffer> {
  const chunks: Buffer[] = [];
  for await (const chunk of stream) {
    chunks.push(Buffer.from(chunk as Buffer));
  }
  return Buffer.concat(chunks);
}

// Explicit opt-in smoke: set KAOS_SSH_SMOKE=1 plus SSH credentials.

// These tests don't need a live SSH connection — they exercise the
// argument-validation guards that run before any network I/O. We invoke the
// methods through the prototype so no real instance is constructed.

// chdir should refuse to treat a regular file (or anything that isn't a
// directory) as the new working directory. Without this guard, `sftp.realpath`
// happily returns file paths and later relative reads/writes/execs would
// resolve against a file — silently wrong. We exercise this by constructing
// a fake SFTP that returns a file stat so the test needs no live SSH.

// These tests pin the SFTPError → KaosError mapping contract. They use a
// fake SFTPWrapper that invokes callbacks with errors carrying the standard
// SFTP status codes (NO_SUCH_FILE=2, PERMISSION_DENIED=3), so they run in
// CI without needing a live SSH connection.
//
// The mapping lives in the promisified SFTP helpers in ssh.ts, so every
// SSHKaos method that touches SFTP automatically throws a KaosSSHError
// subclass (KaosFileNotFoundError / KaosPermissionError / …) instead of
// the raw ssh2 error.

// These tests exercise the pure command-building logic behind execWithEnv
// without needing a live SSH connection. The actual end-to-end delivery of
// env vars is validated by the smoke tests above when KAOS_SSH_SMOKE=1.

// These tests drive the SSHKaos read/stat/glob/iterdir happy paths via
// fake SFTP wrappers, so they run in CI without a live SSH server. Without
// them the smoke block is the only route to those code paths, which means
// CI only sees the error branches.
describe('SSHKaos mock success paths', () => {
  interface TreeNode {
    type: 'dir' | 'file';
    children?: Record<string, TreeNode>;
    content?: Buffer;
    // Permission bits only — forces buildStMode to derive the type bits
    // from the is* helpers (the "mode without type bits" branch) when true.
    stripTypeBits?: boolean;
  }

  function makeStats(node: TreeNode): unknown {
    const isDir = node.type === 'dir';
    // Either include type bits (0o040000/0o100000) or strip them to force
    // the buildStMode helper to derive them via isDirectory()/isFile().
    const baseMode = isDir ? 0o040755 : 0o100644;
    const mode = node.stripTypeBits === true ? baseMode & 0o7777 : baseMode;
    return {
      mode,
      size: node.content ? node.content.length : 0,
      uid: 1000,
      gid: 1000,
      atime: 100,
      mtime: 200,
      isDirectory: () => isDir,
      isFile: () => !isDir,
      isSymbolicLink: () => false,
      isSocket: () => false,
      isCharacterDevice: () => false,
      isBlockDevice: () => false,
      isFIFO: () => false,
    };
  }

  function lookup(root: TreeNode, path: string): TreeNode | undefined {
    if (path === '/') return root;
    const parts = path.split('/').filter(Boolean);
    let current: TreeNode | undefined = root;
    for (const part of parts) {
      if (!current?.children?.[part]) return undefined;
      current = current.children[part];
    }
    return current;
  }

  // Fake SFTP that exposes a tree and implements the handful of callbacks
  // SSHKaos actually calls. Anything not needed is left unimplemented.
  function makeTreeSftp(root: TreeNode): unknown {
    return {
      realpath(path: string, cb: (err: Error | null, abs: string) => void): void {
        cb(null, path);
      },
      stat(path: string, cb: (err: Error | null, stats?: unknown) => void): void {
        const node = lookup(root, path);
        if (!node) {
          const err = new Error(`no such file: ${path}`);
          (err as unknown as { code: number }).code = 2;
          cb(err);
          return;
        }
        cb(null, makeStats(node));
      },
      lstat(path: string, cb: (err: Error | null, stats?: unknown) => void): void {
        const node = lookup(root, path);
        if (!node) {
          const err = new Error(`no such file: ${path}`);
          (err as unknown as { code: number }).code = 2;
          cb(err);
          return;
        }
        cb(null, makeStats(node));
      },
      readdir(path: string, cb: (err: Error | null, list?: unknown[]) => void): void {
        const node = lookup(root, path);
        if (!node || node.type !== 'dir' || !node.children) {
          const err = new Error(`not a directory: ${path}`);
          (err as unknown as { code: number }).code = 2;
          cb(err);
          return;
        }
        cb(
          null,
          Object.entries(node.children).map(([filename, child]) => ({
            filename,
            attrs: makeStats(child),
          })),
        );
      },
      readFile(path: string, cb: (err: Error | null, data?: Buffer) => void): void {
        const node = lookup(root, path);
        if (!node || node.type !== 'file') {
          const err = new Error(`no such file: ${path}`);
          (err as unknown as { code: number }).code = 2;
          cb(err);
          return;
        }
        cb(null, node.content ?? Buffer.alloc(0));
      },
    };
  }

  function makeFakeKaos(sftp: unknown, cwd = '/'): SSHKaos {
    const instance = Object.create(SSHKaos.prototype) as SSHKaos;
    const internal = instance as unknown as { _sftp: unknown; _cwd: string; _home: string };
    internal._sftp = sftp;
    internal._cwd = cwd;
    internal._home = '/home/tester';
    return instance;
  }

  // ── path helpers ────────────────────────────────────────────────────


  // ── stat + buildStMode variants ─────────────────────────────────────




  // ── iterdir ────────────────────────────────────────────────────────


  // ── glob ────────────────────────────────────────────────────────────






  // ── readLines empty-file early return ─────────────────────────────



  // ── . / .. filter coverage ────────────────────────────────────────





  // ── glob error handling in the ** branch ──────────────────────────


  // ── readBytes ──────────────────────────────────────────────────────


  // ── execWithEnv body ───────────────────────────────────────────────

  __testAugmentVitest_eb364c837923.it("withenv_appends_layers_and_preserves_original_round_017_pass_03", () => {
    const { SSHKaos } = __testAugmentTarget_a2e5cf093d4b;
    const { expect } = __testAugmentVitest_eb364c837923;

    const instance = Object.create(SSHKaos.prototype) as InstanceType<typeof SSHKaos>;
    (instance as any)._client = {};
    (instance as any)._sftp = {};
    (instance as any)._home = '/home/test';
    (instance as any)._cwd = '/cwd';
    (instance as any)._envLayers = [{ A: '1' }];

    const child = instance.withEnv({ B: '2' });
    const grand = child.withEnv({ C: '3' });

    // Original must be unchanged
    __testAugmentVitest_eb364c837923.expect((instance as any)._envLayers).toEqual([{ A: '1' }]);
    // Child should have two layers (original + new)
    __testAugmentVitest_eb364c837923.expect((child as any)._envLayers).toEqual([{ A: '1' }, { B: '2' }]);
    // Grandchild should have three layers
    __testAugmentVitest_eb364c837923.expect((grand as any)._envLayers).toEqual([{ A: '1' }, { B: '2' }, { C: '3' }]);
  });
});

// These tests pin the non-race mkdir error branches in SSHKaos — the
// "path already exists but is a file" and "parents=true with a final
// directory already present under existOk=false" cases. All driven via
// fake SFTP wrappers so no live server is required.


import * as __testAugmentVitest_eb364c837923 from "vitest";

import * as __testAugmentTarget_a2e5cf093d4b from "../src/ssh.js";

const __testAugmentLoadTarget_a2e5cf093d4b = async () => {
  __testAugmentVitest_eb364c837923.vi.doUnmock("../src/ssh.js");
  __testAugmentVitest_eb364c837923.vi.resetModules();
  return import("../src/ssh.js");
};
