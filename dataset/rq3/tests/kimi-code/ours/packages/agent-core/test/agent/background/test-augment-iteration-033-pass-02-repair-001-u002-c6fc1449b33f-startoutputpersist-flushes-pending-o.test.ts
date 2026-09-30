/**
 * Covers: BackgroundManager.
 */

import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { PassThrough, Readable } from 'node:stream';
import type { Writable } from 'node:stream';
import { join } from 'pathe';

import type { KaosProcess } from '@moonshot-ai/kaos';
import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  BackgroundTaskPersistence,
  ProcessBackgroundTask,
  type BackgroundManager,
} from '../../../src/agent/background';
import {
  agentTask,
  createBackgroundManager,
  registerProcess,
  waitForOutput,
  waitForTerminal,
} from './helpers';
import { isUserCancellation, userCancellationReason } from '../../../src/utils/abort';

function immediateProcess(exitCode: number, stdoutText = ''): KaosProcess {
  return {
    stdin: { write: vi.fn(), end: vi.fn() } as unknown as Writable,
    stdout: Readable.from(stdoutText ? [stdoutText] : []),
    stderr: Readable.from([]),
    pid: 10000 + exitCode,
    exitCode,
    wait: vi.fn().mockResolvedValue(exitCode) as KaosProcess['wait'],
    kill: vi.fn().mockResolvedValue(undefined) as KaosProcess['kill'],
    dispose: vi.fn().mockResolvedValue(undefined) as KaosProcess['dispose'],
  };
}

function rejectedProcess(error: Error): KaosProcess {
  return {
    stdin: { write: vi.fn(), end: vi.fn() } as unknown as Writable,
    stdout: Readable.from([]),
    stderr: Readable.from([]),
    pid: 99999,
    exitCode: null,
    wait: vi.fn().mockRejectedValue(error) as KaosProcess['wait'],
    kill: vi.fn().mockResolvedValue(undefined) as KaosProcess['kill'],
    dispose: vi.fn().mockResolvedValue(undefined) as KaosProcess['dispose'],
  };
}

function processWithStdoutError(message = 'stdout read failed'): KaosProcess {
  const stdout = new PassThrough();
  return {
    stdin: { write: vi.fn(), end: vi.fn() } as unknown as Writable,
    stdout,
    stderr: Readable.from([]),
    pid: 99998,
    exitCode: 0,
    wait: vi.fn(async () => {
      stdout.destroy(new Error(message));
      return 0;
    }) as KaosProcess['wait'],
    kill: vi.fn().mockResolvedValue(undefined) as KaosProcess['kill'],
    dispose: vi.fn().mockResolvedValue(undefined) as KaosProcess['dispose'],
  };
}

function processWithStdoutErrorBeforeWait(message = 'stdout read failed'): {
  proc: KaosProcess;
  failStdout: () => void;
  resolveWait: (exitCode: number) => void;
} {
  const stdout = new PassThrough();
  let currentExitCode: number | null = null;
  let resolveWait: (n: number) => void = () => {};
  const waitPromise = new Promise<number>((resolve) => {
    resolveWait = resolve;
  });
  return {
    proc: {
      stdin: { write: vi.fn(), end: vi.fn() } as unknown as Writable,
      stdout,
      stderr: Readable.from([]),
      pid: 99997,
      get exitCode(): number | null {
        return currentExitCode;
      },
      wait: vi.fn(() => waitPromise) as KaosProcess['wait'],
      kill: vi.fn().mockResolvedValue(undefined) as KaosProcess['kill'],
      dispose: vi.fn().mockResolvedValue(undefined) as KaosProcess['dispose'],
    },
    failStdout: () => {
      stdout.destroy(new Error(message));
    },
    resolveWait: (exitCode) => {
      currentExitCode = exitCode;
      resolveWait(exitCode);
    },
  };
}

function pendingProcess(exitOnKill = 143): {
  proc: KaosProcess;
  killSpy: ReturnType<typeof vi.fn>;
} {
  let resolveWait: (n: number) => void = () => {};
  const waitPromise = new Promise<number>((resolve) => {
    resolveWait = resolve;
  });
  let currentExitCode: number | null = null;
  const killSpy = vi.fn(async () => {
    if (currentExitCode !== null) return;
    currentExitCode = exitOnKill;
    resolveWait(exitOnKill);
  });
  const proc: KaosProcess = {
    stdin: { write: vi.fn(), end: vi.fn() } as unknown as Writable,
    stdout: Readable.from([]),
    stderr: Readable.from([]),
    pid: 54321,
    get exitCode(): number | null {
      return currentExitCode;
    },
    wait: () => waitPromise,
    kill: killSpy as unknown as KaosProcess['kill'],
    dispose: vi.fn().mockResolvedValue(undefined) as KaosProcess['dispose'],
  };
  return { proc, killSpy };
}

function manuallyResolvedProcess(): {
  proc: KaosProcess;
  killSpy: ReturnType<typeof vi.fn>;
  resolve: (exitCode: number) => void;
} {
  let resolveWait: (n: number) => void = () => {};
  const waitPromise = new Promise<number>((resolve) => {
    resolveWait = resolve;
  });
  let currentExitCode: number | null = null;
  const killSpy = vi.fn().mockResolvedValue(undefined);
  const proc: KaosProcess = {
    stdin: { write: vi.fn(), end: vi.fn() } as unknown as Writable,
    stdout: Readable.from([]),
    stderr: Readable.from([]),
    pid: 54324,
    get exitCode(): number | null {
      return currentExitCode;
    },
    wait: () => waitPromise,
    kill: killSpy as unknown as KaosProcess['kill'],
    dispose: vi.fn().mockResolvedValue(undefined) as KaosProcess['dispose'],
  };
  return {
    proc,
    killSpy,
    resolve: (exitCode) => {
      if (currentExitCode !== null) return;
      currentExitCode = exitCode;
      resolveWait(exitCode);
    },
  };
}

function processWithVisibleExitCodeBeforeWait(exitCode = 143): {
  proc: KaosProcess;
  markExited: () => void;
} {
  let currentExitCode: number | null = null;
  const proc: KaosProcess = {
    stdin: { write: vi.fn(), end: vi.fn() } as unknown as Writable,
    stdout: Readable.from([]),
    stderr: Readable.from([]),
    pid: 54322,
    get exitCode(): number | null {
      return currentExitCode;
    },
    wait: () => new Promise<number>(() => {}),
    kill: vi.fn().mockResolvedValue(undefined) as KaosProcess['kill'],
    dispose: vi.fn().mockResolvedValue(undefined) as KaosProcess['dispose'],
  };
  return {
    proc,
    markExited: () => {
      currentExitCode = exitCode;
    },
  };
}

describe('BackgroundManager', () => {
  afterEach(() => {
    vi.useRealTimers();
  });
































  __testAugmentVitest_eb020db9e026.it("startOutputPersist_flushes_pending_output_round_033_pass_02", async () => {
    const { expect, vi } = __testAugmentVitest_eb020db9e026;

    // persistence that captures appendTaskOutput calls
    const appendTaskOutput = vi.fn().mockResolvedValue(undefined);
    const persistence = {
      appendTaskOutput,
      writeTask: vi.fn().mockResolvedValue(undefined),
      taskOutputExists: vi.fn().mockResolvedValue(false),
      taskOutputSizeBytes: vi.fn().mockResolvedValue(0),
      readTaskOutputBytes: vi.fn().mockResolvedValue(''),
      taskOutputFile: vi.fn().mockReturnValue('/tmp/x'),
      listTasks: vi.fn().mockResolvedValue([]),
    } as any;

    const agent = { emitEvent: vi.fn(), telemetry: { track: vi.fn() }, turn: { steer: vi.fn() }, context: { appendUserMessage: vi.fn() }, hooks: { fireAndForgetTrigger: vi.fn() }, kimiConfig: undefined };

    const target = await __testAugmentLoadTarget_a38d37baac3b();
    const { BackgroundManager } = target;

    const manager = new BackgroundManager(agent as any, persistence as any);

    // Register a foreground (non-detached) task so outputPersistStarted starts false
    const task = {
      idPrefix: 'agent',
      description: 'flush pending',
      timeoutMs: 0,
      start: () => new Promise(() => {}),
      toInfo: (base: any) => ({ ...base, kind: 'agent' }),
    } as any;

    const taskId = manager.registerTask(task, { detached: false });
    const entry = (manager as any).tasks.get(taskId) as any;

    // Simulate buffered pre-detach output
    entry.pendingOutput = ['one', 'two'];
    entry.pendingOutputBytes = Buffer.byteLength('onetwo', 'utf-8');
    entry.outputPersistStarted = false;

    // Call private startOutputPersist
    (manager as any).startOutputPersist(entry);

    // Wait for the queued append to run
    await entry.outputWriteQueue;

    // Should have enqueued a single appendTaskOutput with the joined pending output
    expect(appendTaskOutput).toHaveBeenCalledWith(taskId, 'onetwo');

    // pending buffers cleared
    expect(entry.pendingOutput).toEqual([]);
    expect(entry.pendingOutputBytes).toBe(0);

    // Calling again should be idempotent and not call appendTaskOutput again
    appendTaskOutput.mockClear();
    (manager as any).startOutputPersist(entry);
    // allow any microtasks
    await Promise.resolve();
    expect(appendTaskOutput).not.toHaveBeenCalled();
  });
});

import * as __testAugmentVitest_eb020db9e026 from "vitest";

const __testAugmentLoadTarget_a38d37baac3b = async () => {
  __testAugmentVitest_eb020db9e026.vi.doUnmock("../../../src/agent/background/index.js");
  __testAugmentVitest_eb020db9e026.vi.resetModules();
  return import("../../../src/agent/background/index.js");
};
