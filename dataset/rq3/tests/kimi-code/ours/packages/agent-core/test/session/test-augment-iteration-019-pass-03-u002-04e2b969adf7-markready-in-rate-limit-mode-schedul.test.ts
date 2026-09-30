import { createControlledPromise } from '@antfu/utils';
import { APIProviderRateLimitError } from '@moonshot-ai/kosong';
import { describe, expect, it, vi } from 'vitest';

import {
  type QueuedSubagentTask,
  type RunSubagentOptions,
  type SpawnSubagentOptions,
  type SubagentHandle,
} from '../../src/session/subagent-host';
import {
  SubagentBatch,
  resolveSwarmMaxConcurrency,
  type SubagentBatchLauncher,
  type SubagentResult,
  type SubagentSuspendedEvent,
} from '../../src/session/subagent-batch';
import { userCancellationReason } from '../../src/utils/abort';

const signal = new AbortController().signal;

describe('SubagentBatch scheduling contract', () => {












  __testAugmentVitest_5c5400a73e5c.it("markready_in_rate_limit_mode_schedules_retry_round_019_pass_03", async () => {
    __testAugmentVitest_5c5400a73e5c.vi.useFakeTimers();
    try {
      // The mock runner exposes attempts so we can drive outcomes deterministically.
      const { runBatch, attempts } = createMockBatchRunner({ readyDelay: undefined });

      // Start a small batch with three tasks so we can cause a rate-limit on the first
      // and still have queued work to observe requeueing.
      const running = runBatch(Array.from({ length: 3 }, (_, i) => queuedTask(i + 1)), { signal: undefined });

      // Ensure initial attempts are created (all three should be started immediately in this small case).
      await __testAugmentVitest_5c5400a73e5c.vi.advanceTimersByTimeAsync(0);
      __testAugmentVitest_5c5400a73e5c.expect(attempts.length).toBeGreaterThanOrEqual(3);

      // Mark all active attempts ready so they appear started to the batch controller.
      attempts.slice(0, 3).forEach((a) => a.markReady());

      // Cause the first attempt to be rate-limited. Because other work remains, the batch
      // should requeue the rate-limited task and enter rate-limit mode.
      attempts[0]!.outcome.resolve({ type: 'rate_limited', agentId: 'agent-1' });
      await __testAugmentVitest_5c5400a73e5c.vi.advanceTimersByTimeAsync(0);

      // Let another attempt complete so work advances while in rate-limit mode.
      attempts[1]!.outcome.resolve({
        task: attempts[1]!.task,
        agentId: 'agent-2',
        status: 'completed',
        result: 'completed 2',
      });
      await __testAugmentVitest_5c5400a73e5c.vi.advanceTimersByTimeAsync(0);

      // At this point the requeued task should be scheduled no earlier than now + 3000ms.
      // Advance just before the retry time and assert no new attempt started.
      await __testAugmentVitest_5c5400a73e5c.vi.advanceTimersByTimeAsync(2999);
      __testAugmentVitest_5c5400a73e5c.expect(attempts.length).toBeLessThanOrEqual(4);

      // Move past the retry interval; the requeued attempt should be launched and its record
      // should indicate the original agent id via retryAgentId.
      await __testAugmentVitest_5c5400a73e5c.vi.advanceTimersByTimeAsync(1);
      __testAugmentVitest_5c5400a73e5c.expect(attempts.length).toBeGreaterThanOrEqual(4);
      const newAttempt = attempts[attempts.length - 1]!;
      __testAugmentVitest_5c5400a73e5c.expect(newAttempt.retryAgentId).toBe('agent-1');

      // Clean up by resolving remaining outcomes so the running promise can settle.
      attempts.forEach((a) => {
        // If not already resolved, mark them completed.
        try {
          a.outcome.resolve({ task: a.task, agentId: a.task.data ? `agent-${String(a.task.data)}` : 'agent-x', status: 'completed', result: 'ok' });
        } catch (e) {
          // ignore duplicate resolves
        }
      });
      await running.catch(() => {});
    } finally {
      __testAugmentVitest_5c5400a73e5c.vi.useRealTimers();
    }
  });
});



type MockAttemptOutcome<T> =
  | SubagentResult<T>
  | {
      readonly type: 'rate_limited';
      readonly agentId: string;
    };

type MockAttemptRecord = {
  readonly task: QueuedSubagentTask<number>;
  readonly retryAgentId?: string;
  readonly markReady: () => void;
  readonly outcome: ReturnType<typeof createControlledPromise<MockAttemptOutcome<number>>>;
};

type MockBatchRunnerOptions = {
  readonly onSuspended?: (event: SubagentSuspendedEvent) => void;
  readonly readyDelay?: (attemptIndex: number) => number | undefined;
  readonly maxConcurrency?: number;
};

function createMockBatchRunner(
  options: MockBatchRunnerOptions = {},
): {
  readonly runBatch: <T>(
    tasks: readonly QueuedSubagentTask<T>[],
    options?: { readonly signal?: AbortSignal },
  ) => Promise<Array<SubagentResult<T>>>;
  readonly attempts: MockAttemptRecord[];
} {
  const attempts: MockAttemptRecord[] = [];
  let activeTasks: readonly QueuedSubagentTask<unknown>[] = [];

  const createHandle = <T,>(
    runOptions: RunSubagentOptions,
    agentId: string,
    profileName: string,
    resumed: boolean,
    retryAgentId?: string,
  ): SubagentHandle => {
    const task = findMockTask<T>(activeTasks, runOptions);
    const outcome = createControlledPromise<MockAttemptOutcome<T>>();
    const markReady = () => {
      runOptions.onReady?.();
    };
    const attemptIndex = attempts.length;
    attempts.push({
      task: task as unknown as QueuedSubagentTask<number>,
      retryAgentId,
      markReady,
      outcome: outcome as unknown as MockAttemptRecord['outcome'],
    });

    const delay = options.readyDelay?.(attemptIndex);
    if (delay !== undefined) setTimeout(markReady, delay);

    return {
      agentId,
      profileName,
      resumed,
      completion: completionFromMockOutcome(outcome, runOptions.signal),
    };
  };

  const host = {
    spawn: async (spawnOptions: SpawnSubagentOptions) => {
      const task = findMockTask(activeTasks, spawnOptions);
      return createHandle(
        spawnOptions,
        mockAgentId(task, attempts.length),
        spawnOptions.profileName,
        false,
      );
    },
    resume: async (agentId: string, runOptions: RunSubagentOptions) =>
      createHandle(runOptions, agentId, 'subagent', true),
    retry: async (agentId: string, runOptions: RunSubagentOptions) =>
      createHandle(runOptions, agentId, 'subagent', true, agentId),
    suspended: (event: SubagentSuspendedEvent) => {
      options.onSuspended?.(event);
    },
  } satisfies SubagentBatchLauncher;

  return {
    runBatch: <T,>(
      tasks: readonly QueuedSubagentTask<T>[],
      runOptions?: { readonly signal?: AbortSignal },
    ) => {
      activeTasks = tasks.map((task) => ({
        ...task,
        signal: task.signal ?? runOptions?.signal,
      }));
      return new SubagentBatch(host, activeTasks as readonly QueuedSubagentTask<T>[], {
        maxConcurrency: options.maxConcurrency,
      }).run();
    },
    attempts,
  };
}

function findMockTask<T>(
  tasks: readonly QueuedSubagentTask<unknown>[],
  options: RunSubagentOptions,
): QueuedSubagentTask<T> {
  const task = tasks.find(
    (candidate) =>
      candidate.prompt === options.prompt &&
      candidate.parentToolCallId === options.parentToolCallId,
  );
  if (task === undefined) {
    throw new Error(`No mock queued task for prompt "${options.prompt}"`);
  }
  return task as QueuedSubagentTask<T>;
}

function mockAgentId(task: QueuedSubagentTask<unknown>, attemptIndex: number): string {
  if (typeof task.data === 'number') return `agent-${String(task.data)}`;
  return `agent-${String(attemptIndex + 1)}`;
}

function completionFromMockOutcome<T>(
  outcome: ReturnType<typeof createControlledPromise<MockAttemptOutcome<T>>>,
  signal: AbortSignal,
): SubagentHandle['completion'] {
  return new Promise((resolve, reject) => {
    const abort = () => {
      reject(signal.reason ?? new Error('Aborted'));
    };
    signal.addEventListener('abort', abort, { once: true });
    outcome.then(
      (result) => {
        signal.removeEventListener('abort', abort);
        if (isMockRateLimitOutcome(result)) {
          reject(new APIProviderRateLimitError('Rate limited', result.agentId));
          return;
        }
        if (result.status === 'completed') {
          resolve({ result: result.result ?? '', usage: result.usage });
          return;
        }
        reject(new Error(result.error ?? result.status));
      },
      (error: unknown) => {
        signal.removeEventListener('abort', abort);
        reject(error);
      },
    );
  });
}

function isMockRateLimitOutcome<T>(
  outcome: MockAttemptOutcome<T>,
): outcome is Extract<MockAttemptOutcome<T>, { readonly type: 'rate_limited' }> {
  return 'type' in outcome && outcome.type === 'rate_limited';
}

function queuedTask(index: number): QueuedSubagentTask<number> {
  return {
    kind: 'spawn',
    data: index,
    profileName: 'coder',
    parentToolCallId: 'call_swarm',
    prompt: `Review item-${String(index)}`,
    description: `Review #${String(index)}`,
    runInBackground: false,
  };
}

import * as __testAugmentVitest_5c5400a73e5c from "vitest";

const __testAugmentLoadTarget_22145f3f46b2 = async () => {
  __testAugmentVitest_5c5400a73e5c.vi.doUnmock("../../src/session/subagent-batch.js");
  __testAugmentVitest_5c5400a73e5c.vi.resetModules();
  return import("../../src/session/subagent-batch.js");
};
