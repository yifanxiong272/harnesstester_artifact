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












  __testAugmentVitest_5c5400a73e5c.it("preaborted_task_signal_yields_aborted_not_started_result_round_019", async () => {
    // Reuse the seed's mock runner and helpers.
    const { runBatch } = createMockBatchRunner();

    // Make a task whose own signal is already aborted with a user cancellation reason.
    const taskSignalController = new AbortController();
    taskSignalController.abort(userCancellationReason());
    const tasks = [{ ...queuedTask(1), signal: taskSignalController.signal }];

    // Because the task.signal is present and already aborted, the batch treats it
    // as the batchSignal and immediately finishes with user-cancellation semantics.
    const results = await runBatch(tasks, { signal: undefined });

    __testAugmentVitest_5c5400a73e5c.expect(results).toHaveLength(1);
    const r = results[0]! as SubagentResult<number>;
    __testAugmentVitest_5c5400a73e5c.expect(r.status).toBe('aborted');
    __testAugmentVitest_5c5400a73e5c.expect(r.state).toBe('not_started');
    __testAugmentVitest_5c5400a73e5c.expect(r.error).toBe(
      'The user manually interrupted this subagent batch before this subagent was started.',
    );
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
