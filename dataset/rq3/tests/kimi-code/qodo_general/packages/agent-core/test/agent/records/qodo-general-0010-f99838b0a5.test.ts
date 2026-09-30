import { describe, expect, it } from 'vitest';

import { buildReplay } from '../../../src';
import {
  AGENT_WIRE_PROTOCOL_VERSION,
  InMemoryAgentRecordPersistence,
  type AgentRecord,
} from '../../../src/agent/records';
import type { ContextMessage } from '../../../src/agent/context';
import { testAgent } from '../harness/agent';
import { FsWatcherService } from '../../../src/services/fs/fsWatcherService';
import { FsWatchLimitError } from '../../../src/services/fs/fsWatcher';
import { vi } from 'vitest';

describe('AgentRecords persistence metadata', () => {
  it('writes metadata before the first persisted record', async () => {
    const persistence = new InMemoryAgentRecordPersistence();
    const records = testAgent({ persistence }).agent.records;

    records.logRecord({
      type: 'turn.prompt',
      input: [{ type: 'text', text: 'hello' }],
      origin: { kind: 'user' },
    });
    await records.flush();

    expect(persistence.records).toHaveLength(2);
    expect(persistence.records[0]).toMatchObject({
      type: 'metadata',
      protocol_version: AGENT_WIRE_PROTOCOL_VERSION,
    });
    expect(persistence.records[0]).not.toHaveProperty('app_version');
    expect(persistence.records[0]).not.toHaveProperty('resumed');
    expect(persistence.records[1]?.type).toBe('turn.prompt');
  });

  it('does not write metadata when replaying an empty stream', async () => {
    const persistence = new InMemoryAgentRecordPersistence();
    const records = testAgent({ persistence }).agent.records;

    await records.replay();
    records.logRecord({
      type: 'turn.prompt',
      input: [{ type: 'text', text: 'one' }],
      origin: { kind: 'user' },
    });
    await records.flush();

    expect(persistence.records.map((record) => record.type)).toEqual([
      'metadata',
      'turn.prompt',
    ]);
  });

  it('rejects replaying a non-empty stream without metadata', async () => {
    const persistence = new InMemoryAgentRecordPersistence([
      {
        type: 'turn.prompt',
        input: [{ type: 'text', text: 'one' }],
        origin: { kind: 'user' },
      },
    ]);
    const records = testAgent({ persistence }).agent.records;

    await expect(records.replay()).rejects.toThrow(
      'AgentRecords replay expected metadata as the first record',
    );
  });

  it('does not duplicate metadata after replaying existing records', async () => {
    const persistence = new InMemoryAgentRecordPersistence([
      {
        type: 'metadata',
        protocol_version: AGENT_WIRE_PROTOCOL_VERSION,
        created_at: 1,
      },
      {
        type: 'turn.prompt',
        input: [{ type: 'text', text: 'one' }],
        origin: { kind: 'user' },
      },
    ]);
    const records = testAgent({ persistence }).agent.records;

    await records.replay();
    records.logRecord({
      type: 'turn.prompt',
      input: [{ type: 'text', text: 'two' }],
      origin: { kind: 'user' },
    });
    await records.flush();

    expect(persistence.records.map((record) => record.type)).toEqual([
      'metadata',
      'turn.prompt',
      'turn.prompt',
    ]);
    expect(persistence.records.filter((record) => record.type === 'metadata')).toHaveLength(1);
  });

  it('does not rewrite records that already use the current wire version', async () => {
    const persistence = new RecordingInMemoryAgentRecordPersistence([
      {
        type: 'metadata',
        protocol_version: AGENT_WIRE_PROTOCOL_VERSION,
        created_at: 1,
      },
      {
        type: 'turn.prompt',
        input: [{ type: 'text', text: 'one' }],
        origin: { kind: 'user' },
      },
    ]);
    const records = testAgent({ persistence }).agent.records;

    await records.replay();

    expect(persistence.rewrites).toEqual([]);
  });

  it('rewrites migrated records to the current wire version after replay', async () => {
    const persistence = new RecordingInMemoryAgentRecordPersistence([
      {
        type: 'metadata',
        protocol_version: '1.0',
        created_at: 1,
      },
      {
        type: 'context.append_message',
        message: {
          role: 'assistant',
          content: [],
          toolCalls: [
            {
              type: 'function',
              id: 'call_legacy_bash',
              function: {
                name: 'Bash',
                arguments: '{"command":"pwd"}',
              },
            },
          ],
        },
      } as unknown as AgentRecord,
    ]);
    const records = testAgent({ persistence }).agent.records;

    await records.replay();

    expect(persistence.rewrites).toHaveLength(1);
    expect(persistence.records[0]).toMatchObject({
      type: 'metadata',
      protocol_version: AGENT_WIRE_PROTOCOL_VERSION,
    });
    const migrated = persistence.records[1] as unknown as {
      readonly message: {
        readonly toolCalls: readonly Record<string, unknown>[];
      };
    };
    expect(migrated.message.toolCalls[0]).toMatchObject({
      name: 'Bash',
      arguments: '{"command":"pwd"}',
    });
    expect(migrated.message.toolCalls[0]?.['function']).toBeUndefined();
  });

  it('warns but continues when replaying records from a newer wire version', async () => {
    const persistence = new InMemoryAgentRecordPersistence([
      {
        type: 'metadata',
        protocol_version: '9.9',
        created_at: 1,
      },
    ]);
    const records = testAgent({ persistence }).agent.records;

    const result = await records.replay();
    expect(result.warning).toContain('9.9');
    expect(result.warning).toContain(AGENT_WIRE_PROTOCOL_VERSION);
  });

  it('rejects replaying records without a registered migration path', async () => {
    const persistence = new InMemoryAgentRecordPersistence([
      {
        type: 'metadata',
        protocol_version: '0.9',
        created_at: 1,
      },
    ]);
    const records = testAgent({ persistence }).agent.records;

    await expect(records.replay()).rejects.toThrow('Missing wire migration for version 0.9');
  });

  it('restores goal.* records during replay', async () => {
    const persistence = new InMemoryAgentRecordPersistence([
      { type: 'metadata', protocol_version: AGENT_WIRE_PROTOCOL_VERSION, created_at: 1 },
      {
        type: 'goal.create',
        goalId: 'g1',
        objective: 'do work',
        completionCriterion: 'tests pass',
      },
      { type: 'goal.update', budgetLimits: { turnBudget: 20 } },
      { type: 'goal.update', tokensUsed: 5, wallClockMs: 0 },
      { type: 'goal.update', turnsUsed: 1 },
      { type: 'goal.update', status: 'blocked', reason: 'needs credentials', actor: 'model' },
    ]);
    const { agent } = testAgent({ persistence });

    await expect(agent.records.replay()).resolves.toEqual({ warning: undefined });
    expect(agent.context.history).toHaveLength(0);
    expect(agent.goal.getGoal().goal).toMatchObject({
      goalId: 'g1',
      objective: 'do work',
      completionCriterion: 'tests pass',
      status: 'blocked',
      terminalReason: 'needs credentials',
      tokensUsed: 5,
      turnsUsed: 1,
      budget: expect.objectContaining({ turnBudget: 20 }),
    });
    expect(agent.replayBuilder.buildResult()).toEqual([
      expect.objectContaining({
        type: 'goal_updated',
        snapshot: expect.objectContaining({ goalId: 'g1', status: 'active' }),
        change: { kind: 'created' },
      }),
      expect.objectContaining({
        type: 'goal_updated',
        snapshot: expect.objectContaining({
          goalId: 'g1',
          status: 'blocked',
          terminalReason: 'needs credentials',
        }),
        change: {
          kind: 'lifecycle',
          status: 'blocked',
          reason: 'needs credentials',
          actor: 'model',
        },
      }),
    ]);
  });

  it('restores forked records as fork boundaries that clear copied goals', async () => {
    const persistence = new InMemoryAgentRecordPersistence([
      { type: 'metadata', protocol_version: AGENT_WIRE_PROTOCOL_VERSION, created_at: 1 },
      {
        type: 'goal.create',
        goalId: 'source-goal',
        objective: 'source work',
      },
      { type: 'forked', time: 2 },
    ]);
    const { agent } = testAgent({ persistence });

    await expect(agent.records.replay()).resolves.toEqual({ warning: undefined });

    expect(agent.goal.getGoal().goal).toBeNull();
    expect(persistence.records.map((record) => record.type)).toEqual([
      'metadata',
      'goal.create',
      'forked',
    ]);
    const reminder = agent.context.history.at(-1);
    expect(reminder?.origin).toEqual({ kind: 'system_trigger', name: 'goal_fork_cleared' });
    expect(JSON.stringify(reminder?.content)).toContain('This fork does not have a current goal.');
  });

  it('keeps goals created after the forked boundary', async () => {
    const persistence = new InMemoryAgentRecordPersistence([
      { type: 'metadata', protocol_version: AGENT_WIRE_PROTOCOL_VERSION, created_at: 1 },
      {
        type: 'goal.create',
        goalId: 'source-goal',
        objective: 'source work',
      },
      { type: 'forked', time: 2 },
      {
        type: 'goal.create',
        goalId: 'fork-goal',
        objective: 'fork work',
      },
    ]);
    const { agent } = testAgent({ persistence });

    await expect(agent.records.replay()).resolves.toEqual({ warning: undefined });

    expect(agent.goal.getGoal().goal).toMatchObject({
      goalId: 'fork-goal',
      objective: 'fork work',
    });
    expect(agent.context.history.at(-1)?.origin).toEqual({
      kind: 'system_trigger',
      name: 'goal_fork_cleared',
    });
  });

  it('does not add a fork-cleared reminder when a forked record has no copied goal', async () => {
    const persistence = new InMemoryAgentRecordPersistence([
      { type: 'metadata', protocol_version: AGENT_WIRE_PROTOCOL_VERSION, created_at: 1 },
      { type: 'forked', time: 2 },
    ]);
    const { agent } = testAgent({ persistence });

    await expect(agent.records.replay()).resolves.toEqual({ warning: undefined });

    expect(agent.goal.getGoal().goal).toBeNull();
    expect(agent.context.history).toHaveLength(0);
  });
});

describe('agent replay range build', () => {
  it('returns the complete replay when no range is requested', async () => {
    const firstMessage = userMessage('first');
    const afterClearMessage = userMessage('after-clear');
    const persistence = new InMemoryAgentRecordPersistence([
      { type: 'metadata', protocol_version: AGENT_WIRE_PROTOCOL_VERSION, created_at: 1 },
      { type: 'context.append_message', message: firstMessage },
      { type: 'context.clear' },
      { type: 'context.append_message', message: afterClearMessage },
    ]);

    await expect(buildReplay(persistence)).resolves.toEqual([
      expect.objectContaining({ type: 'message', message: firstMessage }),
      expect.objectContaining({ type: 'message', message: afterClearMessage }),
    ]);
  });

  it('applies start and count to replay records instead of wire records', async () => {
    const message = userMessage('hello');
    const persistence = new RecordingInMemoryAgentRecordPersistence([
      { type: 'metadata', protocol_version: AGENT_WIRE_PROTOCOL_VERSION, created_at: 1 },
      {
        type: 'usage.record',
        model: 'mock-model',
        usage: { inputOther: 1, inputCacheRead: 0, inputCacheCreation: 0, output: 1 },
      },
      {
        type: 'config.update',
        cwd: process.cwd(),
        thinkingLevel: 'off',
      },
      {
        type: 'usage.record',
        model: 'mock-model',
        usage: { inputOther: 2, inputCacheRead: 0, inputCacheCreation: 0, output: 1 },
      },
      { type: 'permission.set_mode', mode: 'yolo' },
      { type: 'context.append_message', message },
    ]);

    const replay = await buildReplay(persistence, { start: 1, count: 2 });

    expect(replay).toEqual([
      expect.objectContaining({ type: 'permission_updated', mode: 'yolo' }),
      expect.objectContaining({ type: 'message', message }),
    ]);
    expect(persistence.rewrites).toEqual([]);
  });

  it('returns the last count replay records when start is omitted', async () => {
    const firstMessage = userMessage('first');
    const secondMessage = userMessage('second');
    const thirdMessage = userMessage('third');
    const persistence = new InMemoryAgentRecordPersistence([
      { type: 'metadata', protocol_version: AGENT_WIRE_PROTOCOL_VERSION, created_at: 1 },
      { type: 'context.append_message', message: firstMessage },
      { type: 'permission.set_mode', mode: 'auto' },
      { type: 'context.append_message', message: secondMessage },
      { type: 'context.append_message', message: thirdMessage },
    ]);

    await expect(buildReplay(persistence, { count: 2 })).resolves.toEqual([
      expect.objectContaining({ type: 'message', message: secondMessage }),
      expect.objectContaining({ type: 'message', message: thirdMessage }),
    ]);
    await expect(buildReplay(persistence, { count: 10 })).resolves.toEqual([
      expect.objectContaining({ type: 'message', message: firstMessage }),
      expect.objectContaining({ type: 'permission_updated', mode: 'auto' }),
      expect.objectContaining({ type: 'message', message: secondMessage }),
      expect.objectContaining({ type: 'message', message: thirdMessage }),
    ]);
  });

  it('continues reading all segments before returning the last count replay records', async () => {
    const beforeClearMessages = Array.from({ length: 50 }, (_item, index) =>
      userMessage(`before-clear-${String(index)}`),
    );
    const afterClearMessages = Array.from({ length: 50 }, (_item, index) =>
      userMessage(`after-clear-${String(index)}`),
    );
    const persistence = new InMemoryAgentRecordPersistence([
      { type: 'metadata', protocol_version: AGENT_WIRE_PROTOCOL_VERSION, created_at: 1 },
      ...beforeClearMessages.map((message) => ({ type: 'context.append_message' as const, message })),
      { type: 'context.clear' },
      ...afterClearMessages.map((message) => ({ type: 'context.append_message' as const, message })),
    ]);

    const replay = await buildReplay(persistence, { count: 10 });

    expect(replay).toHaveLength(10);
    expect(replay).toEqual(
      afterClearMessages.slice(-10).map((message) =>
        expect.objectContaining({ type: 'message', message }),
      ),
    );
  });

  it('continues reading after count so later wire records can patch captured replay records', async () => {
    const persistence = new InMemoryAgentRecordPersistence([
      { type: 'metadata', protocol_version: AGENT_WIRE_PROTOCOL_VERSION, created_at: 1 },
      { type: 'full_compaction.begin', source: 'manual', instruction: 'keep facts' },
      {
        type: 'context.apply_compaction',
        summary: 'Compacted summary.',
        compactedCount: 0,
        tokensBefore: 10,
        tokensAfter: 3,
      },
      { type: 'permission.set_mode', mode: 'auto' },
    ]);

    await expect(buildReplay(persistence, { start: 0, count: 1 })).resolves.toEqual([
      expect.objectContaining({
        type: 'compaction',
        instruction: 'keep facts',
        result: {
          summary: 'Compacted summary.',
          compactedCount: 0,
          tokensBefore: 10,
          tokensAfter: 3,
        },
      }),
    ]);
  });

  it('does not rewrite migrated wire records while projecting', async () => {
    const persistence = new RecordingInMemoryAgentRecordPersistence([
      { type: 'metadata', protocol_version: '1.0', created_at: 1 },
      { type: 'permission.set_mode', mode: 'auto' },
    ]);

    await expect(buildReplay(persistence, { start: 0, count: 1 })).resolves.toEqual([
      expect.objectContaining({ type: 'permission_updated', mode: 'auto' }),
    ]);
    expect(persistence.rewrites).toEqual([]);
  });

  it('keeps the start offset correct when undo removes more messages than count', async () => {
    const firstMessage = userMessage('first');
    const removedBeforeStart = userMessage('removed-before-start');
    const removedAtStart = userMessage('removed-at-start');
    const removedAfterStart = userMessage('removed-after-start');
    const nextMessage = userMessage('next');
    const expectedMessage = userMessage('expected');
    const persistence = new InMemoryAgentRecordPersistence([
      { type: 'metadata', protocol_version: AGENT_WIRE_PROTOCOL_VERSION, created_at: 1 },
      { type: 'context.append_message', message: firstMessage },
      { type: 'context.append_message', message: removedBeforeStart },
      { type: 'context.append_message', message: removedAtStart },
      { type: 'context.append_message', message: removedAfterStart },
      { type: 'context.undo', count: 3 },
      { type: 'context.append_message', message: nextMessage },
      { type: 'context.append_message', message: expectedMessage },
    ]);

    await expect(buildReplay(persistence, { start: 2, count: 1 })).resolves.toEqual([
      expect.objectContaining({ type: 'message', message: expectedMessage }),
    ]);
  });

  it('clamps results at undo boundaries', async () => {
    const firstMessage = userMessage('first');
    const secondMessage = userMessage('second');
    const afterClearMessage = userMessage('after-clear');
    const persistence = new InMemoryAgentRecordPersistence([
      { type: 'metadata', protocol_version: AGENT_WIRE_PROTOCOL_VERSION, created_at: 1 },
      { type: 'context.append_message', message: firstMessage },
      { type: 'context.append_message', message: secondMessage },
      { type: 'context.clear' },
      { type: 'context.append_message', message: afterClearMessage },
    ]);

    await expect(buildReplay(persistence, { start: 0, count: 10 })).resolves.toEqual([
      expect.objectContaining({ type: 'message', message: firstMessage }),
      expect.objectContaining({ type: 'message', message: secondMessage }),
    ]);
    await expect(buildReplay(persistence, { start: 2, count: 10 })).resolves.toEqual([
      expect.objectContaining({ type: 'message', message: afterClearMessage }),
    ]);
  });
});

  it('forgetConnection disposes sessions and clears connection state', () => {
    const watchers: any[] = [];
    const factory = () => {
      const handlers = new Map<string, Function[]>();
      const w = {
        add: vi.fn(),
        unwatch: vi.fn(),
        on: (ev: string, cb: Function) => {
          handlers.set(ev, (handlers.get(ev) || []).concat(cb));
        },
        emitAll: (eventName: string, absPath: string) => {
          (handlers.get('all') || []).forEach((cb) => cb(eventName, absPath));
        },
        close: vi.fn(() => Promise.resolve()),
      };
      watchers.push(w);
      return w as unknown as import('chokidar').FSWatcher;
    };
  
    const lookup = { resolve: vi.fn(() => ({ send: vi.fn() })) };
    const logger = { warn: vi.fn(), debug: vi.fn() };
    const sessionService = {} as any;
  
    const service = new (FsWatcherService as any)(
      lookup,
      { watcherFactory: factory },
      logger,
      sessionService,
    ) as InstanceType<typeof FsWatcherService>;
  
    // add two sessions under the same connection
    service.addPaths('s1', 'connA', ['/a/x']);
    service.addPaths('s2', 'connA', ['/b/y']);
    expect(service.countForConnection('connA')).toBe(2);
    // Now forget the connection; this should remove entries for both sessions
    service.forgetConnection('connA');
    // after forget, the connection should report zero paths
    expect(service.countForConnection('connA')).toBe(0);
    // watchedPaths for both sessions should be empty arrays
    expect(service.watchedPaths('connA', 's1')).toEqual([]);
    expect(service.watchedPaths('connA', 's2')).toEqual([]);
  });


  it('removes paths, unwatch is called and watcher.close errors are logged', async () => {
    const handlers = new Map<string, Function[]>();
    const watcher = {
      add: vi.fn(),
      unwatch: vi.fn(),
      on: (ev: string, cb: Function) => {
        handlers.set(ev, (handlers.get(ev) || []).concat(cb));
      },
      emitAll: (eventName: string, absPath: string) => {
        (handlers.get('all') || []).forEach((cb) => cb(eventName, absPath));
      },
      close: vi.fn(() => Promise.reject(new Error('close failed'))),
    };
  
    const factory = () => watcher as unknown as import('chokidar').FSWatcher;
    const logger = { warn: vi.fn(), debug: vi.fn() };
    const lookup = { resolve: vi.fn(() => ({ send: vi.fn() })) };
    const sessionService = {} as any;
  
    const service = new (FsWatcherService as any)(
      lookup,
      { watcherFactory: factory },
      logger,
      sessionService,
    ) as InstanceType<typeof FsWatcherService>;
  
    const p = '/dispose/path';
    service.addPaths('s-x', 'conn-x', [p]);
    // now remove the path - this should call unwatch and ultimately attempt to close watcher
    const remaining = service.removePaths('s-x', 'conn-x', [p]);
    expect(remaining).toEqual([]);
    // unwatch should have been called for the path
    expect(watcher.unwatch).toHaveBeenCalledWith(p);
    // wait a tick so the rejected close() promise is observed by the dispose catch handler
    await Promise.resolve();
    // logger.warn should have been invoked because close() rejects
    expect((logger.warn as any).mock.calls.length).toBeGreaterThanOrEqual(1);
  });


  it('coalesces raw changes and forwards frames, including truncated windows and send errors', async () => {
    const watchers: any[] = [];
    const factory = () => {
      const handlers = new Map<string, Function[]>();
      const w = {
        add: vi.fn(),
        unwatch: vi.fn(),
        on: (ev: string, cb: Function) => {
          handlers.set(ev, (handlers.get(ev) || []).concat(cb));
        },
        emitAll: (eventName: string, absPath: string) => {
          (handlers.get('all') || []).forEach((cb) => cb(eventName, absPath));
        },
        close: vi.fn(() => Promise.resolve()),
      };
      watchers.push(w);
      return w as unknown as import('chokidar').FSWatcher;
    };
  
    const sentFrames: any[] = [];
    const goodSink = { send: (frame: any) => sentFrames.push(frame) };
    const throwingSink = { send: (_: any) => { throw new Error('send failed'); } };
  
    const lookup = {
      resolve: vi.fn((connectionId: string) => (connectionId === 'good' ? goodSink : throwingSink)),
    };
    const logger = { warn: vi.fn(), debug: vi.fn() };
    const sessionService = {} as any;
  
    // very small debounce and low maxChangesPerWindow to trigger truncation
    const service = new (FsWatcherService as any)(
      lookup,
      { watcherFactory: factory, debounceMs: 10, maxChangesPerWindow: 1 },
      logger,
      sessionService,
    ) as InstanceType<typeof FsWatcherService>;
  
    // add watched root for both a 'good' and a 'bad' connection
    service.addPaths('session1', 'good', ['/root']);
    service.addPaths('session1', 'bad', ['/root']);
  
    // emit two raw events which should cause truncation (maxChangesPerWindow = 1)
    // use fake timers so the debounce timer can be advanced deterministically
    vi.useFakeTimers();
    try {
      watchers[0].emitAll('add', '/root/file1');
      watchers[0].emitAll('add', '/root/file2');
      // advance time to trigger the debounce flush
      vi.advanceTimersByTime(20);
      // allow microtasks to run
      await Promise.resolve();
    } finally {
      vi.useRealTimers();
    }
  
    // good sink should have received one frame with truncated true and count 2
    expect(sentFrames.length).toBe(1);
    const frame = sentFrames[0];
    expect(frame.type).toBe('event.fs.changed');
    expect(frame.session_id).toBe('session1');
    expect(frame.payload.truncated).toBe(true);
    expect(frame.payload.count).toBe(2);
  
    // Now emit one more event to exercise the path where a sink.send throws and is caught
    vi.useFakeTimers();
    try {
      watchers[0].emitAll('add', '/root/file3');
      vi.advanceTimersByTime(20);
      await Promise.resolve();
    } finally {
      vi.useRealTimers();
    }
  
    // the throwing sink should have caused logger.warn to be called at least once
    expect((logger.warn as any).mock.calls.length).toBeGreaterThanOrEqual(1);
  });


  it('debounces and forwards frames, handles truncation and send exceptions', async () => {
    // create watchers that capture handlers so we can emit 'all' events
    const watchers: any[] = [];
    const factory = () => {
      const handlers = new Map<string, Function[]>();
      const w = {
        add: vi.fn(),
        unwatch: vi.fn(),
        on: (ev: string, cb: Function) => {
          handlers.set(ev, (handlers.get(ev) || []).concat(cb));
        },
        emitAll: (eventName: string, absPath: string) => {
          (handlers.get('all') || []).forEach((cb) => cb(eventName, absPath));
        },
        close: vi.fn(() => Promise.resolve()),
      };
      (w as any).__handlers = handlers;
      watchers.push(w);
      return w as unknown as import('chokidar').FSWatcher;
    };
  
    const sentGood: any[] = [];
    const goodSink = { send: (f: any) => sentGood.push(f) };
    const throwingSink = { send: (_: any) => { throw new Error('send failed'); } };
  
    const lookup = {
      resolve: vi.fn((connectionId: string) =>
        connectionId === 'good' ? goodSink : throwingSink),
    };
    const logger = { warn: vi.fn(), debug: vi.fn() };
    const sessionService = {};
  
    // use very small debounce and low maxChangesPerWindow to trigger truncation
    const service = new FsWatcherService(
      lookup as any,
      { watcherFactory: factory, debounceMs: 10, maxChangesPerWindow: 1 },
      logger as any,
      sessionService as any,
    );
  
    // watch the same root for two connections: one good, one that will throw on send
    service.addPaths('session1', 'good', ['/root']);
    service.addPaths('session1', 'bad', ['/root']);
  
    const watcher = watchers[0];
  
    // Use fake timers to control debounce
    vi.useFakeTimers();
    try {
      // emit two events within the debounce window; this should trigger truncation (maxChangesPerWindow = 1)
      watcher.emitAll('add', '/root/file1');
      watcher.emitAll('add', '/root/file2');
  
      // advance timers to fire the debounce flush
      vi.advanceTimersByTime(20);
  
      // allow any microtasks to run
      await Promise.resolve();
    } finally {
      vi.useRealTimers();
    }
  
    // good sink should have been sent a frame describing a truncated window
    expect(sentGood.length).toBe(1);
    const frame = sentGood[0];
    expect(frame.type).toBe('event.fs.changed');
    expect(frame.session_id).toBe('session1');
    expect(frame.payload.truncated).toBe(true);
    expect(frame.payload.count).toBe(2);
  
    // the bad sink throws; the service should catch and log via logger.warn
    expect(logger.warn).toHaveBeenCalled();
  });


  it('adds/removes paths and enforces per-connection path limits', () => {
    // fake watcher factory that records add/unwatch/close calls
    const watchers: any[] = [];
    const factory = () => {
      const handlers = new Map<string, Function[]>();
      const w = {
        add: vi.fn(),
        unwatch: vi.fn(),
        on: (ev: string, cb: Function) => {
          handlers.set(ev, (handlers.get(ev) || []).concat(cb));
        },
        emitAll: (eventName: string, ...args: unknown[]) => {
          (handlers.get('all') || []).forEach((cb) => cb(...args));
        },
        close: vi.fn(() => Promise.resolve()),
      };
      (w as any).__handlers = handlers;
      watchers.push(w);
      return w as unknown as import('chokidar').FSWatcher;
    };
  
    const send = vi.fn();
    const lookup = { resolve: vi.fn(() => ({ send })) };
    const logger = { warn: vi.fn(), debug: vi.fn() };
    const sessionService = {};
  
    const service = new FsWatcherService(
      lookup,
      { watcherFactory: factory, maxPathsPerConnection: 2 },
      logger as any,
      sessionService as any,
    );
  
    const p1 = '/root/a';
    const got1 = service.addPaths('s1', 'c1', [p1]);
    expect(got1).toEqual([p1]);
    expect(service.countForConnection('c1')).toBe(1);
    expect(service.watchedPaths('c1', 's1')).toEqual([p1]);
    // underlying watcher.add should have been invoked for the path
    expect(watchers[0].add).toHaveBeenCalledWith(p1);
  
    // adding the same path again should be idempotent
    const gotDup = service.addPaths('s1', 'c1', [p1]);
    expect(gotDup).toEqual([p1]);
    expect(service.countForConnection('c1')).toBe(1);
  
    // add a second distinct path
    const p2 = '/root/b';
    const got2 = service.addPaths('s1', 'c1', [p2]);
    expect(new Set(got2)).toEqual(new Set([p1, p2]));
    expect(service.countForConnection('c1')).toBe(2);
  
    // adding a third path should exceed the per-connection limit
    expect(() => {
      service.addPaths('s1', 'c1', ['/root/c']);
    }).toThrowError(FsWatchLimitError);
  
    // remove one path and ensure unwatch called
    const remainingAfterRemove = service.removePaths('s1', 'c1', [p1]);
    // remaining should include p2
    expect(remainingAfterRemove).toEqual([p2]);
    expect(watchers[0].unwatch).toHaveBeenCalledWith(p1);
  
    // remove the last path -> should dispose session and call close
    const remainingEmpty = service.removePaths('s1', 'c1', [p2]);
    expect(remainingEmpty).toEqual([]);
    expect(watchers[0].unwatch).toHaveBeenCalledWith(p2);
    // close() should have been called as part of session disposal
    expect(watchers[0].close).toHaveBeenCalled();
  });


class RecordingInMemoryAgentRecordPersistence extends InMemoryAgentRecordPersistence {
  readonly rewrites: AgentRecord[][] = [];

  override rewrite(records: readonly AgentRecord[]): void {
    this.rewrites.push([...records]);
    super.rewrite(records);
  }
}

function userMessage(text: string): ContextMessage {
  return {
    role: 'user',
    content: [{ type: 'text', text }],
    toolCalls: [],
  };
}
