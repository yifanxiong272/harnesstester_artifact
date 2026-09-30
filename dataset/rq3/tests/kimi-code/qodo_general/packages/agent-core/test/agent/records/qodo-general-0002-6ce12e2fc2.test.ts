import { describe, expect, it } from 'vitest';

import { buildReplay } from '../../../src';
import {
  AGENT_WIRE_PROTOCOL_VERSION,
  InMemoryAgentRecordPersistence,
  type AgentRecord,
} from '../../../src/agent/records';
import type { ContextMessage } from '../../../src/agent/context';
import { testAgent } from '../harness/agent';

import path from 'node:path';
import { promises as fs } from 'node:fs';
import { FsSearchService } from '../../../src/services/fs/fsSearchService';
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

  it('FsSearchService.grepWithNode returns contextual matches and respects limits', async () => {
    const sessions = { get: vi.fn().mockResolvedValue({ metadata: { cwd: '/root' } }) } as any;
    const logger = { warn: vi.fn() } as any;
    const service = new FsSearchService(sessions, logger);
  
    // Stub walk to report three files; one of them will cause readFile to throw.
    vi.spyOn(service as any, 'walk').mockImplementation(async (_rootAbs: string, _rootRel: string, _matcher: any, visit: any) => {
      await visit('f1.txt', 'f1.txt', 'file');
      await visit('f2.txt', 'f2.txt', 'file');
      await visit('skip.txt', 'skip.txt', 'file');
    });
  
    // fs.readFile returns content for f1 and f2; skip.txt throws.
    vi.spyOn(fs, 'readFile').mockImplementation(async (p: string, _enc?: any) => {
      const b = path.basename(p);
      if (b === 'skip.txt') throw new Error('permission denied');
      if (b === 'f1.txt') return 'before line\nmatched line\nafter line\n';
      if (b === 'f2.txt') return 'MATCHED line in uppercase\nanother\n';
      return '';
    });
  
    const req = {
      pattern: 'matched',
      regex: false,
      case_sensitive: false,
      context_lines: 1,
      follow_gitignore: false,
      include_globs: undefined,
      exclude_globs: undefined,
      max_matches_per_file: 1,
      max_total_matches: 1,
      max_files: 10,
    } as any;
  
    const out = await (service as any).grepWithNode('/root', req, new AbortController().signal, Date.now());
  
    // Because max_total_matches = 1, we should have exactly one file with a match and truncated true.
    expect(out.files_scanned).toBe(1);
    expect(out.truncated).toBe(true);
    expect(out.files.length).toBe(1);
    const file = out.files[0];
    expect(['f1.txt', 'f2.txt']).toContain(file.path);
    expect(file.matches.length).toBe(1);
    // match should include before/after arrays of length <= context_lines
    expect(Array.isArray(file.matches[0].before)).toBe(true);
    expect(Array.isArray(file.matches[0].after)).toBe(true);
  
    vi.restoreAllMocks();
  });


  it('FsSearchService.search discovers files and applies glob filters and limits', async () => {
    const sessions = { get: vi.fn().mockResolvedValue({ metadata: { cwd: '/root' } }) } as any;
    const logger = { warn: vi.fn() } as any;
    const service = new FsSearchService(sessions, logger);
  
    // realpath -> /root
    vi.spyOn(fs, 'realpath').mockResolvedValue('/root');
  
    // Prepare dirents at root only. Return empty for any subdirectory to avoid recursion.
    const rootDirents = [
      { name: 'foo.txt', isDirectory: () => false, isSymbolicLink: () => false },
      { name: 'bar.md', isDirectory: () => false, isSymbolicLink: () => false },
      { name: 'sub', isDirectory: () => true, isSymbolicLink: () => false },
      { name: 'afoo.txt', isDirectory: () => false, isSymbolicLink: () => false },
    ] as any[];
  
    vi.spyOn(fs, 'readdir').mockImplementation(async (p: string, _opts?: any) => {
      // Only return entries for the root path; other paths simulate empty directories.
      if (p === '/root') return rootDirents;
      return [];
    });
  
    // 1) Basic match for 'foo' should find foo.txt and afoo.txt (two matches)
    const resAll = await service.search('session', {
      query: 'foo',
      limit: 10,
      follow_gitignore: false,
    } as any);
  
    // We expect 2 items (foo.txt and afoo.txt). They should have positive scores and match positions.
    expect(resAll.items.length).toBeGreaterThanOrEqual(2);
    for (const it of resAll.items) {
      expect(it.score).toBeGreaterThan(0);
      expect(Array.isArray(it.match_positions)).toBe(true);
    }
  
    // 2) include_globs to only include bar.* (searching 'bar' should yield only bar.md)
    const resInclude = await service.search('session', {
      query: 'bar',
      limit: 10,
      follow_gitignore: false,
      include_globs: ['**/*.md'],
    } as any);
    expect(resInclude.items.length).toBe(1);
    expect(resInclude.items[0].name).toBe('bar.md');
  
    // 3) exclude_globs to remove bar.md (search 'bar' with exclusion)
    const resExclude = await service.search('session', {
      query: 'bar',
      limit: 10,
      follow_gitignore: false,
      exclude_globs: ['**/bar.*'],
    } as any);
    expect(resExclude.items.length).toBe(0);
  
    // 4) limit/truncation: set limit to 1 while two matches exist -> truncated true
    const resLimit = await service.search('session', {
      query: 'foo',
      limit: 1,
      follow_gitignore: false,
    } as any);
    expect(resLimit.items.length).toBe(1);
    expect(resLimit.truncated).toBe(true);
  
    vi.restoreAllMocks();
  });


  it('FsSearchService.matcher reads .gitignore and caches the result', async () => {
    const sessions = { get: vi.fn().mockResolvedValue({ metadata: { cwd: '/root' } }) } as any;
    const logger = { warn: vi.fn() } as any;
    const service = new FsSearchService(sessions, logger);
  
    // Mock readFile to return a .gitignore content once
    const readSpy = vi.spyOn(fs, 'readFile').mockImplementation(async (p: string, _enc: string) => {
      if (p === '/root/.gitignore') return 'ignored-file\nsubdir/\n';
      throw new Error('not found');
    });
  
    // First call should read the file
    const ig1 = await (service as any).matcher('/root');
    expect(ig1).toBeDefined();
    // .git/ should be in the ignore by default
    expect(ig1.ignores('.git/')).toBe(true);
    expect(ig1.ignores('ignored-file')).toBe(true);
    expect(ig1.ignores('subdir/')).toBe(true);
  
    // Second call should return cached instance and not call readFile again
    const ig2 = await (service as any).matcher('/root');
    expect(ig2).toBe(ig1);
    expect(readSpy).toHaveBeenCalledTimes(1);
  
    vi.restoreAllMocks();
  });


  it('FsSearchService.search matches files and respects include/exclude globs', async () => {
    // Arrange: mock session and logger
    const sessions = { get: vi.fn().mockResolvedValue({ metadata: { cwd: '/root' } }) } as any;
    const logger = { warn: vi.fn() } as any;
    const service = new FsSearchService(sessions, logger);
  
    // realpath returns /root
    vi.spyOn(fs, 'realpath').mockResolvedValue('/root');
  
    // Prepare Dirent-like objects
    const rootEntries = [
      { name: 'foo.txt', isDirectory: () => false, isSymbolicLink: () => false } as any,
      { name: 'bar.md', isDirectory: () => false, isSymbolicLink: () => false } as any,
      { name: 'sub', isDirectory: () => true, isSymbolicLink: () => false } as any,
      { name: '.git', isDirectory: () => true, isSymbolicLink: () => false } as any,
    ];
    const subEntries = [
      { name: 'nested.txt', isDirectory: () => false, isSymbolicLink: () => false } as any,
    ];
  
    // Mock readdir to return different entries per path so recursion is deterministic
    vi.spyOn(fs, 'readdir').mockImplementation(async (p: string, _opts?: any) => {
      // Only root and /root/sub are relevant in this test.
      if (p === '/root') return rootEntries;
      if (p === '/root/sub') return subEntries;
      return [];
    });
  
    // Act: search for "foo" without gitignore and no globs
    const res1 = await service.search('session', {
      query: 'foo',
      limit: 10,
      follow_gitignore: false,
    } as any);
  
    // Assert: foo.txt found and has positive score and match positions
    expect(res1.items.some((it) => it.name === 'foo.txt')).toBeTruthy();
    const foo = res1.items.find((it) => it.name === 'foo.txt')!;
    expect(foo.score).toBeGreaterThan(0);
    // match positions should refer to 'foo' in 'foo.txt' (indices 0,1,2)
    expect(foo.match_positions).toEqual([0, 1, 2]);
  
    // Act: include_globs that only include bar.* should filter out foo.txt
    const res2 = await service.search('session', {
      query: 'foo',
      limit: 10,
      follow_gitignore: false,
      include_globs: ['bar.*'],
    } as any);
    expect(res2.items.length).toBe(0);
  
    // Act: exclude_globs that exclude bar.* should filter out bar.md when searching for 'bar'
    const res3 = await service.search('session', {
      query: 'bar',
      limit: 10,
      follow_gitignore: false,
      exclude_globs: ['bar.*'],
    } as any);
    expect(res3.items.some((it) => it.name === 'bar.md')).toBeFalsy();
  
    // Cleanup
    vi.restoreAllMocks();
  });


  it('FsSearchService.probeRg warns when rg is missing and caches the null result', async () => {
    const sessions = { get: vi.fn().mockResolvedValue({ metadata: { cwd: '/root' } }) } as any;
    const logger = { warn: vi.fn() } as any;
    const service = new (FsSearchService as any)(sessions, logger);
  
    // Make whichBinary fail by having fs.stat always reject
    vi.spyOn(fs, 'stat').mockRejectedValue(new Error('not found'));
  
    // Call probeRg (protected) via any-cast
    const out1 = await (service as any).probeRg();
    expect(out1).toBeNull();
    expect(logger.warn).toHaveBeenCalledTimes(1);
    // second call should hit the cache and not warn again
    const out2 = await (service as any).probeRg();
    expect(out2).toBeNull();
    expect(logger.warn).toHaveBeenCalledTimes(1);
  
    vi.restoreAllMocks();
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
