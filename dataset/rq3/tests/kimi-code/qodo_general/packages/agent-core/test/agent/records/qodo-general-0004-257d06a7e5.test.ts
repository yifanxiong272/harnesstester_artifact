import { describe, expect, it } from 'vitest';

import { buildReplay } from '../../../src';
import {
  AGENT_WIRE_PROTOCOL_VERSION,
  InMemoryAgentRecordPersistence,
  type AgentRecord,
} from '../../../src/agent/records';
import type { ContextMessage } from '../../../src/agent/context';
import { testAgent } from '../harness/agent';
import { FsService } from '../../../src/services/fs/fsService';
import { FsPathNotFoundError, FsIsBinaryError, FsAlreadyExistsError } from '../../../src/services/fs/fs';
import { promises as fsp } from 'node:fs';
import path from 'node:path';
import os from 'node:os';

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

  it('FsService.statMany returns entries and nulls for missing paths', async () => {
    const tmp = await fsp.mkdtemp(path.join(os.tmpdir(), 'fs-service-statmany-'));
    try {
      await fsp.writeFile(path.join(tmp, 'a.txt'), 'a');
  
      const sessions = {
        get: async (_id: string) => ({ metadata: { cwd: tmp } }),
      };
      const svc = new FsService(sessions as any);
  
      const out = await svc.statMany('s', { paths: ['a.txt', 'missing.txt'] });
  
      expect(out.entries['a.txt']?.name).toBe('a.txt');
      expect(out.entries['missing.txt']).toBeNull();
    } finally {
      await fsp.rm(tmp, { recursive: true, force: true });
    }
  });


  it('FsService.list respects exclude_globs, show_hidden and .gitignore', async () => {
    const tmp = await fsp.mkdtemp(path.join(os.tmpdir(), 'fs-service-list-'));
    try {
      // Create files to test exclusion/hidden/gitignore handling
      await fsp.writeFile(path.join(tmp, 'visible.txt'), 'v');
      await fsp.writeFile(path.join(tmp, '.secret'), 'hidden');
      await fsp.writeFile(path.join(tmp, 'exclude.js'), 'x');
      await fsp.writeFile(path.join(tmp, 'ignored.log'), 'i');
      // .gitignore should cause ignored.log to be skipped when follow_gitignore is true
      await fsp.writeFile(path.join(tmp, '.gitignore'), 'ignored.log\n');
      await fsp.mkdir(path.join(tmp, 'sub'));
      await fsp.writeFile(path.join(tmp, 'sub', 'subfile.txt'), 's');
  
      const sessions = {
        get: async (_id: string) => ({ metadata: { cwd: tmp } }),
      };
      const svc = new FsService(sessions as any);
  
      const res = await svc.list('s', {
        path: '.',
        depth: 2,
        limit: 100,
        show_hidden: false,
        follow_gitignore: true,
        exclude_globs: ['**/*.js'],
        sort: 'name_asc',
        include_git_status: false,
      });
  
      // top-level visible items should include visible.txt and the sub directory
      const topNames = res.items.map((i) => i.name);
      expect(topNames).toContain('visible.txt');
      expect(topNames).toContain('sub');
  
      // hidden file and excluded patterns should not be present
      expect(topNames).not.toContain('.secret');
      expect(topNames).not.toContain('exclude.js');
      expect(topNames).not.toContain('ignored.log');
  
      // children_by_path should include 'sub' with subfile.txt
      expect(res.children_by_path).toBeDefined();
      expect(res.children_by_path?.['sub']?.some((c) => c.name === 'subfile.txt')).toBe(true);
    } finally {
      await fsp.rm(tmp, { recursive: true, force: true });
    }
  });


  it('FsService matcher reads .gitignore and list respects follow_gitignore', async () => {
    const tmp = await fsp.mkdtemp(path.join(os.tmpdir(), 'fs-service-test-'));
    try {
      // Create a .gitignore that ignores the secrets/ directory
      await fsp.writeFile(path.join(tmp, '.gitignore'), 'secrets/\n');
      await fsp.mkdir(path.join(tmp, 'secrets'));
      await fsp.writeFile(path.join(tmp, 'secrets', 'hidden.txt'), 'secret');
      await fsp.writeFile(path.join(tmp, 'visible.txt'), 'ok');
      
      const sessions = {
        get: async (_id: string) => ({ metadata: { cwd: tmp } }),
      };
      const svc = new FsService(sessions as any);
      
      // Access protected matcher via any cast to test caching and behavior
      const realCwd = await fsp.realpath(tmp);
      const ig1 = await (svc as any).matcher(realCwd);
      expect(typeof ig1.ignores).toBe('function');
      // Should be cached: second call returns same instance
      const ig2 = await (svc as any).matcher(realCwd);
      expect(ig1).toBe(ig2);
      
      // Now call list with follow_gitignore true; secrets/ should be ignored
      const res = await svc.list('s', {
        path: '.',
        depth: 1,
        limit: 100,
        show_hidden: true,
        follow_gitignore: true,
        exclude_globs: [],
        sort: 'name_asc',
        include_git_status: false,
      });
      const names = res.items.map((it) => it.name).sort();
      expect(names).toContain('visible.txt');
      // secrets directory should be ignored
      expect(names).not.toContain('secrets');
    } finally {
      await fsp.rm(tmp, { recursive: true, force: true });
    }
  });


  it('stat non-existent path throws FsPathNotFoundError', async () => {
    const tmp = await fsp.mkdtemp(path.join(os.tmpdir(), 'fs-test-'));
    try {
      const sessions = { get: async () => ({ metadata: { cwd: tmp } }) } as any;
      const svc = new FsService(sessions);
      await expect(svc.stat('session', { path: 'this-does-not-exist.txt' })).rejects.toBeInstanceOf(FsPathNotFoundError);
    } finally {
      await fsp.rm(tmp, { recursive: true, force: true });
    }
  });


  it('throws appropriate errors for mkdir edge cases', async () => {
    const tmp = await fsp.mkdtemp(path.join(os.tmpdir(), 'fs-test-'));
    try {
      const sessions = { get: async () => ({ metadata: { cwd: tmp } }) } as any;
      const svc = new FsService(sessions);
      // non-recursive mkdir with missing parent should raise FsPathNotFoundError
      await expect(
        svc.mkdir('session', { path: 'missing_parent/inner', recursive: false }),
      ).rejects.toBeInstanceOf(FsPathNotFoundError);
      // create a file at 'targetfile' then attempt mkdir on same path should yield EEXIST -> FsAlreadyExistsError
      const existing = path.join(tmp, 'targetfile');
      await fsp.writeFile(existing, 'content');
      await expect(
        svc.mkdir('session', { path: 'targetfile', recursive: false }),
      ).rejects.toBeInstanceOf(FsAlreadyExistsError);
    } finally {
      await fsp.rm(tmp, { recursive: true, force: true });
    }
  });


  it('detects binary file and blocks utf-8 reads', async () => {
    const tmp = await fsp.mkdtemp(path.join(os.tmpdir(), 'fs-test-'));
    try {
      const file = path.join(tmp, 'binfile.bin');
      const buf = Buffer.from([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);
      await fsp.writeFile(file, buf);
      const sessions = { get: async () => ({ metadata: { cwd: tmp } }) } as any;
      const svc = new FsService(sessions);
      const dl = await svc.resolveDownload('session', 'binfile.bin');
      expect(dl.size).toBe(buf.length);
      expect(dl.mime).toBe('application/octet-stream');
      // requesting utf-8 should be rejected because file is binary
      await expect(
        svc.read('session', { path: 'binfile.bin', offset: 0, length: 100, encoding: 'utf-8' }),
      ).rejects.toBeInstanceOf(FsIsBinaryError);
      // base64 should succeed and use base64 encoding
      const base = await svc.read('session', { path: 'binfile.bin', offset: 0, length: 100, encoding: 'base64' });
      expect(base.encoding).toBe('base64');
      expect(base.content).toBeDefined();
    } finally {
      await fsp.rm(tmp, { recursive: true, force: true });
    }
  });


  it('reads text file correctly using FsService', async () => {
    const tmp = await fsp.mkdtemp(path.join(os.tmpdir(), 'fs-test-'));
    try {
      const file = path.join(tmp, 'hello.txt');
      await fsp.writeFile(file, 'line1\nline2\n', 'utf-8');
      const sessions = { get: async () => ({ metadata: { cwd: tmp } }) } as any;
      const svc = new FsService(sessions);
      const res = await svc.read('session', {
        path: 'hello.txt',
        offset: 0,
        length: 1000,
        encoding: 'utf-8',
      });
      expect(res.path).toBe('hello.txt');
      expect(res.encoding).toBe('utf-8');
      expect(res.is_binary).toBe(false);
      expect(res.size).toBeGreaterThan(0);
      // content has two logical lines (last newline is not counted as extra)
      expect(res.line_count).toBe(2);
      expect(res.content).toContain('line1');
      // resolvePath for '.' should be a directory
      const rp = await svc.resolvePath('session', '.');
      expect(rp.isDirectory).toBe(true);
    } finally {
      await fsp.rm(tmp, { recursive: true, force: true });
    }
  });

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
