import { describe, expect, it } from 'vitest';
import { createInitialState, reduceAppEvent } from '../src/api/daemon/eventReducer';
import type { AppMessage, AppSession } from '../src/api/types';
import { COMPACTION_MARKER_METADATA_KEY } from '../src/api/types';

function makeSession(id: string, updatedAt: string): AppSession {
  return {
    id,
    title: id,
    createdAt: updatedAt,
    updatedAt,
    status: 'idle',
    archived: false,
    cwd: '/workspace',
    model: 'kimi-code',
    usage: {
      inputTokens: 0,
      outputTokens: 0,
      cacheReadTokens: 0,
      cacheCreationTokens: 0,
      totalCostUsd: 0,
      contextTokens: 0,
      contextLimit: 0,
      turnCount: 0,
    },
    messageCount: 0,
    lastSeq: 0,
  };
}

function makeMessage(sessionId: string, createdAt: string): AppMessage {
  return {
    id: `msg_${createdAt}`,
    sessionId,
    role: 'user',
    content: [{ type: 'text', text: 'hi' }],
    createdAt,
  };
}

describe('reduceAppEvent messageCreated', () => {
  it('bumps the session updatedAt so it floats to the top of the sidebar', () => {
    const state = {
      ...createInitialState(),
      sessions: [makeSession('s-old', '2026-01-01T00:00:00.000Z')],
    };
    const next = reduceAppEvent(
      state,
      { type: 'messageCreated', message: makeMessage('s-old', '2026-06-01T12:00:00.000Z') },
      { sessionId: 's-old', seq: 1 },
    );
    expect(next.sessions[0]?.updatedAt).toBe('2026-06-01T12:00:00.000Z');
  });

  it('does not move a session backwards when an older message arrives', () => {
    const state = {
      ...createInitialState(),
      sessions: [makeSession('s-new', '2026-06-01T12:00:00.000Z')],
    };
    const next = reduceAppEvent(
      state,
      { type: 'messageCreated', message: makeMessage('s-new', '2026-01-01T00:00:00.000Z') },
      { sessionId: 's-new', seq: 1 },
    );
    expect(next.sessions[0]?.updatedAt).toBe('2026-06-01T12:00:00.000Z');
  });

  it('leaves other sessions untouched', () => {
    const state = {
      ...createInitialState(),
      sessions: [
        makeSession('s-a', '2026-01-01T00:00:00.000Z'),
        makeSession('s-b', '2026-01-01T00:00:00.000Z'),
      ],
    };
    const next = reduceAppEvent(
      state,
      { type: 'messageCreated', message: makeMessage('s-a', '2026-06-01T12:00:00.000Z') },
      { sessionId: 's-a', seq: 1 },
    );
    expect(next.sessions.find((s) => s.id === 's-a')?.updatedAt).toBe('2026-06-01T12:00:00.000Z');
    expect(next.sessions.find((s) => s.id === 's-b')?.updatedAt).toBe('2026-01-01T00:00:00.000Z');
  });

  it('handles various no-op/unknown/default events without throwing and advances seq/warnings accordingly', () => {
    let state = createInitialState();
  
    // agentDelta should be a silent advance (no warnings)
    state = reduceAppEvent(state, { type: 'agentDelta', payload: {} } as any, { sessionId: 's', seq: 5 });
    expect(state.lastSeqBySession['s']).toBe(5);
    expect(state.warnings).toHaveLength(0);
  
    // historyCompacted advances seq but otherwise does nothing here
    state = reduceAppEvent(state, { type: 'historyCompacted', sessionId: 's', beforeSeq: 1 } as any, { sessionId: 's', seq: 7 });
    expect(state.lastSeqBySession['s']).toBe(7);
  
    // workspaceCreated/Updated/Deleted are no-ops here (should not throw)
    state = reduceAppEvent(state, { type: 'workspaceCreated', workspace: {} } as any, { sessionId: 's', seq: 8 });
    state = reduceAppEvent(state, { type: 'workspaceUpdated', workspace: {} } as any, { sessionId: 's', seq: 9 });
    state = reduceAppEvent(state, { type: 'workspaceDeleted', workspaceId: 'w' } as any, { sessionId: 's', seq: 10 });
    // still no warnings
    expect(state.warnings).toHaveLength(0);
  
    // unknown event with raw === null should push an "Unhandled event: (unknown)" warning
    state = reduceAppEvent(state, { type: 'unknown', raw: null } as any, { sessionId: 's', seq: 11 });
    expect(state.warnings.some((w) => w.includes('Unhandled event'))).toBe(true);
  
    // An event type not explicitly listed in the switch should hit the default branch's exhaustiveness guard
    // and not throw at runtime.
    const acted = reduceAppEvent(state, { type: 'someCompletelyUnknownType', whatever: 1 } as any, { sessionId: 's', seq: 12 });
    expect(acted).toBeDefined();
    // seq was advanced for the last call
    expect(acted.lastSeqBySession['s']).toBe(12);
  });


  it('messageUpdated replaces content and durationMs for matching message', () => {
    const m1 = {
      id: 'm1',
      sessionId: 's',
      role: 'assistant',
      content: [{ type: 'text', text: 'old' }],
      durationMs: 100,
      createdAt: '2026-01-01T00:00:00.000Z',
    };
    const m2 = {
      id: 'm2',
      sessionId: 's',
      role: 'assistant',
      content: [{ type: 'text', text: 'keep' }],
      createdAt: '2026-01-02T00:00:00.000Z',
    };
    const state = { ...createInitialState(), messagesBySession: { s: [m1, m2] } };
  
    const next = reduceAppEvent(
      state,
      {
        type: 'messageUpdated',
        sessionId: 's',
        messageId: 'm1',
        content: [{ type: 'text', text: 'updated' }],
        durationMs: 200,
      } as any,
      { sessionId: 's', seq: 2 },
    );
  
    const updated = next.messagesBySession['s']!;
    const gotM1 = updated.find((x) => x.id === 'm1')!;
    const gotM2 = updated.find((x) => x.id === 'm2')!;
    expect(gotM1.content).toEqual([{ type: 'text', text: 'updated' }]);
    expect((gotM1 as any).durationMs).toBe(200);
    // ensure other message unchanged
    expect(gotM2.content).toEqual([{ type: 'text', text: 'keep' }]);
  });


  it('applies assistantDelta updates for text, thinking and creates missing slots', () => {
    const msg = {
      id: 'm1',
      sessionId: 's',
      role: 'assistant',
      content: [
        { type: 'image', source: { url: 'x' } } as any,
        { type: 'text', text: 'OLD' } as any,
        { type: 'thinking', thinking: 'A', signature: 'sig' } as any,
      ],
      createdAt: '2026-05-01T00:00:00.000Z',
    };
    let state = { ...createInitialState(), messagesBySession: { s: [msg] } };
  
    // 1) Replace non-text (image) slot with text
    state = reduceAppEvent(
      state,
      { type: 'assistantDelta', sessionId: 's', messageId: 'm1', contentIndex: 0, delta: { text: 'NEW' } } as any,
      { sessionId: 's', seq: 1 },
    );
    expect((state.messagesBySession['s']![0].content[0] as any).type).toBe('text');
    expect((state.messagesBySession['s']![0].content[0] as any).text).toBe('NEW');
  
    // 2) Replace existing text slot with a thinking slot (existing.type !== 'thinking')
    state = reduceAppEvent(
      state,
      { type: 'assistantDelta', sessionId: 's', messageId: 'm1', contentIndex: 1, delta: { thinking: 'T' } } as any,
      { sessionId: 's', seq: 2 },
    );
    const slot1 = state.messagesBySession['s']![0].content[1] as any;
    expect(slot1.type).toBe('thinking');
    expect(slot1.thinking).toBe('T');
  
    // 3) Accumulate into an existing thinking slot and preserve signature
    state = reduceAppEvent(
      state,
      { type: 'assistantDelta', sessionId: 's', messageId: 'm1', contentIndex: 2, delta: { thinking: 'B' } } as any,
      { sessionId: 's', seq: 3 },
    );
    const slot2 = state.messagesBySession['s']![0].content[2] as any;
    expect(slot2.type).toBe('thinking');
    expect(slot2.thinking).toBe('AB'); // original 'A' + appended 'B'
    expect(slot2.signature).toBe('sig');
  
    // 4) Create a missing slot beyond current length (index 4)
    state = reduceAppEvent(
      state,
      { type: 'assistantDelta', sessionId: 's', messageId: 'm1', contentIndex: 4, delta: { text: 'LATE' } } as any,
      { sessionId: 's', seq: 4 },
    );
    const created = state.messagesBySession['s']![0].content[4] as any;
    expect(created.type).toBe('text');
    expect(created.text).toBe('LATE');
  });


  it('reconciles optimistic user echo by exact content match', () => {
    const state = {
      ...createInitialState(),
      // Put an optimistic user message into the session transcript
      messagesBySession: {
        s: [
          {
            id: 'opt-msg-1',
            sessionId: 's',
            role: 'user',
            content: [{ type: 'text', text: 'hello' }],
            createdAt: '2026-01-01T00:00:00.000Z',
            metadata: { 'kimiWeb.optimisticUserMessage': true, local: true },
          },
        ],
      },
    };
  
    // Daemon echo of the same user message (different id, same content)
    const event = {
      type: 'messageCreated',
      message: {
        id: 'server-echo-1',
        sessionId: 's',
        role: 'user',
        content: [{ type: 'text', text: 'hello' }],
        createdAt: '2026-06-01T00:00:00.000Z',
      },
    };
  
    const next = reduceAppEvent(state, event as any, { sessionId: 's', seq: 10 });
  
    // Optimistic id should be preserved (reconciled), content replaced with server's content,
    // and optimistic metadata should still be present (merged).
    const msgs = next.messagesBySession['s']!;
    expect(msgs).toHaveLength(1);
    expect(msgs[0].id).toBe('opt-msg-1'); // preserved id
    expect(msgs[0].content).toEqual([{ type: 'text', text: 'hello' }]);
    expect(msgs[0].metadata).toMatchObject({ 'kimiWeb.optimisticUserMessage': true, local: true });
    // lastSeqBySession advanced
    expect(next.lastSeqBySession['s']).toBe(10);
  });


  it('processes approvals/questions/tasks/goals/config and unknown events', () => {
    let state = createInitialState();
  
    // approvals: request -> present, then resolved -> removed
    state = reduceAppEvent(state, { type: 'approvalRequested', sessionId: 's', approval: { approvalId: 'ap1' } as any }, { sessionId: 's', seq: 1 });
    expect(state.approvalsBySession['s']?.some((a) => a.approvalId === 'ap1')).toBe(true);
    state = reduceAppEvent(state, { type: 'approvalResolved', sessionId: 's', approvalId: 'ap1' }, { sessionId: 's', seq: 2 });
    expect(state.approvalsBySession['s']?.some((a) => a.approvalId === 'ap1')).toBe(false);
  
    // questions: request -> present, answered -> removed
    state = reduceAppEvent(state, { type: 'questionRequested', sessionId: 's', question: { questionId: 'q1' } as any }, { sessionId: 's', seq: 3 });
    expect(state.questionsBySession['s']?.some((q) => q.questionId === 'q1')).toBe(true);
    state = reduceAppEvent(state, { type: 'questionAnswered', sessionId: 's', questionId: 'q1' }, { sessionId: 's', seq: 4 });
    expect(state.questionsBySession['s']?.some((q) => q.questionId === 'q1')).toBe(false);
  
    // tasks: create a task, then create again with same id patches it
    state = reduceAppEvent(state, { type: 'taskCreated', sessionId: 's', task: { id: 't1', status: 'running' } as any }, { sessionId: 's', seq: 5 });
    expect(state.tasksBySession['s']?.some((t) => t.id === 't1')).toBe(true);
    state = reduceAppEvent(state, { type: 'taskCreated', sessionId: 's', task: { id: 't1', status: 'done' } as any }, { sessionId: 's', seq: 6 });
    expect(state.tasksBySession['s']?.find((t) => t.id === 't1')?.status).toBe('done');
  
    // taskProgress: if same as last chunk, skip; otherwise append
    state.tasksBySession['s'] = [{ id: 'tp', outputLines: ['a'] } as any];
    state = reduceAppEvent(state, { type: 'taskProgress', sessionId: 's', taskId: 'tp', outputChunk: 'a' }, { sessionId: 's', seq: 7 });
    expect((state.tasksBySession['s']!.find((t) => t.id === 'tp') as any).outputLines.length).toBe(1);
    state = reduceAppEvent(state, { type: 'taskProgress', sessionId: 's', taskId: 'tp', outputChunk: 'b' }, { sessionId: 's', seq: 8 });
    expect((state.tasksBySession['s']!.find((t) => t.id === 'tp') as any).outputLines.at(-1)).toBe('b');
  
    // taskCompleted updates status and output fields
    state = reduceAppEvent(state, { type: 'taskCompleted', sessionId: 's', taskId: 'tp', status: 'complete', outputPreview: 'preview', outputBytes: 123 }, { sessionId: 's', seq: 9 });
    const completed = state.tasksBySession['s']!.find((t) => t.id === 'tp') as any;
    expect(completed.status).toBe('complete');
    expect(completed.outputPreview).toBe('preview');
    expect(completed.outputBytes).toBe(123);
  
    // goals: set a goal, then update with null to delete, and ensure 'complete' deletes
    state = reduceAppEvent(state, { type: 'goalUpdated', sessionId: 's', goal: { id: 'g1', status: 'active' } as any }, { sessionId: 's', seq: 10 });
    expect(state.goalBySession['s']?.id).toBe('g1');
    state = reduceAppEvent(state, { type: 'goalUpdated', sessionId: 's', goal: null }, { sessionId: 's', seq: 11 });
    expect(state.goalBySession['s']).toBeUndefined();
    state = reduceAppEvent(state, { type: 'goalUpdated', sessionId: 's', goal: { id: 'g2', status: 'complete' } as any }, { sessionId: 's', seq: 12 });
    expect(state.goalBySession['s']).toBeUndefined();
  
    // configChanged
    state = reduceAppEvent(state, { type: 'configChanged', config: { some: 'cfg' } as any }, { sessionId: 's', seq: 13 });
    expect(state.config).toEqual({ some: 'cfg' });
  
    // unknown events:
    // _noop true -> no warning added
    state = reduceAppEvent(state, { type: 'unknown', raw: { _noop: true } as any }, { sessionId: 's', seq: 14 });
    expect(state.warnings.length).toBe(0);
  
    // agent error/ warning -> adds a warning containing the message
    state = reduceAppEvent(state, { type: 'unknown', raw: { _agentError: true, message: 'provider failed' } as any }, { sessionId: 's', seq: 15 });
    expect(state.warnings.some((w) => (w as string).includes('provider failed'))).toBe(true);
  
    // truly unknown -> generic Unhandled event warning (type present)
    state = reduceAppEvent(state, { type: 'unknown', raw: { type: 'weirdType' } as any }, { sessionId: 's', seq: 16 });
    expect(state.warnings.some((w) => (w as string).includes('Unhandled event'))).toBe(true);
  });


  it('reconciles optimistic user message echoes by promptId and by loose shape', () => {
    // prepare state with an optimistic message stamped with promptId
    const optimistic = {
      id: 'opt1',
      sessionId: 's',
      role: 'user',
      content: [{ type: 'text', text: 'optimistic' }],
      createdAt: '2026-03-01T00:00:00.000Z',
      promptId: 'p1',
      metadata: { 'kimiWeb.optimisticUserMessage': true } as any,
    };
    let state = { ...createInitialState(), messagesBySession: { s: [optimistic] } };
  
    // server echo arrives with the same promptId -> should reconcile into the optimistic message id
    const serverEcho = {
      id: 'server-e1',
      sessionId: 's',
      role: 'user',
      content: [{ type: 'text', text: 'server text' }],
      createdAt: '2026-03-01T00:00:01.000Z',
      promptId: 'p1',
      metadata: {},
    };
    let next = reduceAppEvent(state, { type: 'messageCreated', message: serverEcho }, { sessionId: 's', seq: 1 });
    const msgs = next.messagesBySession['s']!;
    expect(msgs.length).toBe(1);
    // id should remain the optimistic id, content should reflect server content
    expect(msgs[0].id).toBe('opt1');
    expect((msgs[0].content[0] as any).text).toBe('server text');
    expect(msgs[0].promptId).toBe('p1');
  
    // Now test loose fallback: optimistic message with a file, server echo uses resolved image
    const optimistic2 = {
      id: 'opt2',
      sessionId: 's2',
      role: 'user',
      content: [
        { type: 'text', text: 'img' },
        { type: 'file', fileId: 'file-123' as any },
      ],
      createdAt: '2026-04-01T00:00:00.000Z',
      metadata: { 'kimiWeb.optimisticUserMessage': true } as any,
    };
    state = { ...createInitialState(), messagesBySession: { s2: [optimistic2] } };
  
    const serverEcho2 = {
      id: 'server-e2',
      sessionId: 's2',
      role: 'user',
      // server returns an image part instead of file part; JSON differs but shape (text + 1 media) is same
      content: [
        { type: 'text', text: 'img' },
        { type: 'image', url: 'data:...' },
      ],
      createdAt: '2026-04-01T00:00:01.000Z',
      metadata: {},
    };
    next = reduceAppEvent(state, { type: 'messageCreated', message: serverEcho2 }, { sessionId: 's2', seq: 2 });
    const msgs2 = next.messagesBySession['s2']!;
    expect(msgs2.length).toBe(1);
    // id should remain the optimistic id (opt2) after reconciliation
    expect(msgs2[0].id).toBe('opt2');
    // server text should replace the content's text slot
    expect((msgs2[0].content[0] as any).text).toBe('img');
  });


  it('handles session lifecycle and compaction events', () => {
    const state = {
      ...createInitialState(),
      sessions: [makeSession('s1', '2026-01-01T00:00:00.000Z')],
      messagesBySession: {
        s1: [
          { id: 'm-existing', sessionId: 's1', role: 'assistant', content: [], createdAt: '2026-01-02T00:00:00.000Z' },
        ],
      },
    };
  
    // sessionCreated for a new session should prepend it
    const s2 = makeSession('s2', '2026-02-02T00:00:00.000Z');
    let next = reduceAppEvent(state, { type: 'sessionCreated', session: s2 }, { sessionId: 's2', seq: 1 });
    expect(next.sessions[0]?.id).toBe('s2');
    expect(next.sessions.length).toBe(2);
  
    // duplicate sessionCreated should not add again
    next = reduceAppEvent(next, { type: 'sessionCreated', session: s2 }, { sessionId: 's2', seq: 2 });
    expect(next.sessions.filter((s) => s.id === 's2').length).toBe(1);
  
    // sessionUpdated replaces the session entry
    const s2patched = { ...s2, title: 'patched-title' };
    next = reduceAppEvent(next, { type: 'sessionUpdated', session: s2patched }, { sessionId: 's2', seq: 3 });
    expect(next.sessions.find((s) => s.id === 's2')?.title).toBe('patched-title');
  
    // sessionStatusChanged updates status and currentPromptId
    next = reduceAppEvent(next, { type: 'sessionStatusChanged', sessionId: 's2', status: 'busy', currentPromptId: 'p1' }, { sessionId: 's2', seq: 4 });
    const s2after = next.sessions.find((s) => s.id === 's2')!;
    expect(s2after.status).toBe('busy');
    expect(s2after.currentPromptId).toBe('p1');
  
    // sessionMetaUpdated patches only provided fields
    next = reduceAppEvent(next, { type: 'sessionMetaUpdated', sessionId: 's2', title: 'meta-title', lastPrompt: 'lp' }, { sessionId: 's2', seq: 5 });
    expect(next.sessions.find((s) => s.id === 's2')?.title).toBe('meta-title');
    expect(next.sessions.find((s) => s.id === 's2')?.lastPrompt).toBe('lp');
  
    // sessionUsageUpdated: empty model should preserve prior model
    const prevModel = next.sessions.find((s) => s.id === 's2')?.model;
    next = reduceAppEvent(next, { type: 'sessionUsageUpdated', sessionId: 's2', usage: { inputTokens: 1, outputTokens: 2, cacheReadTokens: 0, cacheCreationTokens: 0, totalCostUsd: 0, contextTokens: 0, contextLimit: 0, turnCount: 0 }, model: '' }, { sessionId: 's2', seq: 6 });
    expect(next.sessions.find((s) => s.id === 's2')?.model).toBe(prevModel);
  
    // non-empty model overwrites
    next = reduceAppEvent(next, { type: 'sessionUsageUpdated', sessionId: 's2', usage: { inputTokens: 1, outputTokens: 2, cacheReadTokens: 0, cacheCreationTokens: 0, totalCostUsd: 0, contextTokens: 0, contextLimit: 0, turnCount: 0 }, model: 'new-model' }, { sessionId: 's2', seq: 7 });
    expect(next.sessions.find((s) => s.id === 's2')?.model).toBe('new-model');
  
    // compactionStarted sets compactionBySession
    next = reduceAppEvent(next, { type: 'compactionStarted', sessionId: 's1', trigger: 'manual' }, { sessionId: 's1', seq: 8 });
    expect(next.compactionBySession['s1']?.status).toBe('running');
    expect(next.compactionBySession['s1']?.trigger).toBe('manual');
  
    // compactionCompleted appends a marker message (id derived from seq) and removes compaction entry
    next = reduceAppEvent(next, { type: 'compactionCompleted', sessionId: 's1', tokensBefore: 100, tokensAfter: 10, summary: 'compacted-ok' }, { sessionId: 's1', seq: 9 });
    expect(next.compactionBySession['s1']).toBeUndefined();
    const markerId = `compaction_s1_9`;
    const msgs = next.messagesBySession['s1']!;
    expect(msgs.some((m) => m.id === markerId)).toBe(true);
    const markerMsg = msgs.find((m) => m.id === markerId)!;
    expect(markerMsg.content.length).toBeGreaterThanOrEqual(0);
    // metadata origin indicates compaction_summary
    expect((markerMsg.metadata as any).origin?.kind).toBe('compaction_summary');
  
    // compactionCancelled removes a running compaction entry
    next = reduceAppEvent(next, { type: 'compactionStarted', sessionId: 's2', trigger: 'auto' }, { sessionId: 's2', seq: 10 });
    expect(next.compactionBySession['s2']?.status).toBe('running');
    next = reduceAppEvent(next, { type: 'compactionCancelled', sessionId: 's2' }, { sessionId: 's2', seq: 11 });
    expect(next.compactionBySession['s2']).toBeUndefined();
  
    // sessionDeleted removes per-session maps and clears activeSessionId if matching
    next.activeSessionId = 's1';
    // add some per-session entries to verify deletion
    next.messagesBySession['s1'] = next.messagesBySession['s1'] ?? [];
    next.tasksBySession['s1'] = [{ id: 'task1' } as any];
    next.goalBySession['s1'] = { id: 'g1', status: 'active' } as any;
    next.approvalsBySession['s1'] = [{ approvalId: 'a1' } as any];
    next.questionsBySession['s1'] = [{ questionId: 'q1' } as any];
    next.lastSeqBySession['s1'] = 42;
  
    next = reduceAppEvent(next, { type: 'sessionDeleted', session: { id: 's1' } as any, sessionId: 's1' }, { sessionId: 's1', seq: 12 });
    expect(next.sessions.some((s) => s.id === 's1')).toBe(false);
    expect(next.messagesBySession['s1']).toBeUndefined();
    expect(next.tasksBySession['s1']).toBeUndefined();
    expect(next.goalBySession['s1']).toBeUndefined();
    expect(next.approvalsBySession['s1']).toBeUndefined();
    expect(next.questionsBySession['s1']).toBeUndefined();
    expect(next.lastSeqBySession['s1']).toBeUndefined();
    expect(next.activeSessionId).toBeUndefined();
  });


  it('handles unknown events: noop, agent errors/warnings, and truly unknown types', () => {
    const sid = 's-unk';
    const state = { ...createInitialState() };
    // _noop should not add a warning
    const afterNoop = reduceAppEvent(
      state,
      { type: 'unknown' as const, raw: { _noop: true } },
      { sessionId: sid, seq: 1 },
    );
    expect(afterNoop.warnings.length).toBe(0);
    // agent error should surface message (label comes from i18n so just assert suffix)
    const afterAgentErr = reduceAppEvent(
      afterNoop,
      { type: 'unknown' as const, raw: { _agentError: true, message: 'boom' } },
      { sessionId: sid, seq: 2 },
    );
    expect(afterAgentErr.warnings.length).toBe(1);
    expect(afterAgentErr.warnings[0].endsWith(': boom')).toBe(true);
    // truly unknown should push "Unhandled event: <type>"
    const afterTrulyUnknown = reduceAppEvent(
      afterAgentErr,
      { type: 'unknown' as const, raw: { type: 'mystery' } },
      { sessionId: sid, seq: 3 },
    );
    expect(afterTrulyUnknown.warnings.some((w) => w.startsWith('Unhandled event:'))).toBe(true);
  });


  it('toolOutput appends output lines to toolUse content parts', () => {
    const sid = 's-tool';
    const toolPart = { type: 'toolUse' as const, toolCallId: 'call-1', outputLines: ['A'] };
    const msg = {
      id: 'm-tool',
      sessionId: sid,
      role: 'assistant',
      content: [toolPart, { type: 'text', text: 'x' }],
      createdAt: '2026-03-03T00:00:00.000Z',
    };
    const state = { ...createInitialState(), messagesBySession: { [sid]: [msg] } };
    const next = reduceAppEvent(
      state,
      { type: 'toolOutput' as const, sessionId: sid, toolCallId: 'call-1', outputChunk: 'B' },
      { sessionId: sid, seq: 1 },
    );
    const updated = next.messagesBySession[sid]!.find((m) => m.id === 'm-tool')!;
    const firstPart = updated.content[0] as any;
    expect(firstPart.outputLines).toEqual(['A', 'B']);
  });


  it('assistantDelta updates text, creates missing slots, and concatenates thinking', () => {
    const sid = 's-delta';
    const msgText = {
      id: 'm-text',
      sessionId: sid,
      role: 'assistant',
      content: [{ type: 'text', text: 'hello' }],
      createdAt: '2026-01-02T00:00:00.000Z',
    };
    const msgThinking = {
      id: 'm-think',
      sessionId: sid,
      role: 'assistant',
      content: [{ type: 'thinking', thinking: 'foo', signature: 'sig' }],
      createdAt: '2026-01-02T00:00:01.000Z',
    };
    const state = {
      ...createInitialState(),
      messagesBySession: { [sid]: [msgText, msgThinking] },
    };
    // Append text to existing text slot
    const next1 = reduceAppEvent(
      state,
      {
        type: 'assistantDelta' as const,
        sessionId: sid,
        messageId: 'm-text',
        contentIndex: 0,
        delta: { text: ' world' },
      },
      { sessionId: sid, seq: 1 },
    );
    const m1 = next1.messagesBySession[sid]!.find((m) => m.id === 'm-text')!;
    expect((m1.content[0] as any).text).toBe('hello world');
    // Produce a delta at a far index to exercise slot-creation loop
    const next2 = reduceAppEvent(
      next1,
      {
        type: 'assistantDelta' as const,
        sessionId: sid,
        messageId: 'm-text',
        contentIndex: 2,
        delta: { text: 'slot2' },
      },
      { sessionId: sid, seq: 2 },
    );
    const m2 = next2.messagesBySession[sid]!.find((m) => m.id === 'm-text')!;
    // slot 2 should exist and contain the text 'slot2'
    expect((m2.content[2] as any).text).toBe('slot2');
    // Thinking concatenation: should append to existing thinking and keep signature
    const next3 = reduceAppEvent(
      next2,
      {
        type: 'assistantDelta' as const,
        sessionId: sid,
        messageId: 'm-think',
        contentIndex: 0,
        delta: { thinking: 'bar' },
      },
      { sessionId: sid, seq: 3 },
    );
    const mt = next3.messagesBySession[sid]!.find((m) => m.id === 'm-think')!;
    const thinkingPart = mt.content[0] as any;
    expect(thinkingPart.thinking).toBe('foobar');
    expect(thinkingPart.signature).toBe('sig');
  });


  it('compactionCompleted appends marker and clears compaction state', () => {
    const sid = 's-comp';
    const state = {
      ...createInitialState(),
      sessions: [makeSession(sid, '2026-01-01T00:00:00.000Z')],
      messagesBySession: {
        [sid]: [
          makeMessage(sid, '2026-01-01T00:00:00.000Z'),
        ],
      },
      compactionBySession: {
        [sid]: { status: 'running', trigger: 'manual' },
      },
    };
    const ev = {
      type: 'compactionCompleted' as const,
      sessionId: sid,
      tokensBefore: 123,
      tokensAfter: 45,
      summary: 'Compacted summary',
    };
    const next = reduceAppEvent(state, ev, { sessionId: sid, seq: 7 });
    // compaction entry removed
    expect(next.compactionBySession[sid]).toBeUndefined();
    const msgs = next.messagesBySession[sid] ?? [];
    expect(msgs.length).toBe(2);
    const marker = msgs[1]!;
    expect(marker.id).toBe(`compaction_${sid}_7`);
    // metadata must contain compaction marker metadata key
    expect(marker.metadata).toHaveProperty(COMPACTION_MARKER_METADATA_KEY);
    const meta = marker.metadata[COMPACTION_MARKER_METADATA_KEY];
    expect(meta.trigger).toBe('manual');
    expect(meta.tokensBefore).toBe(123);
    expect(meta.tokensAfter).toBe(45);
    // content includes the summary text
    expect(marker.content.length).toBeGreaterThanOrEqual(1);
    expect((marker.content[0] as any).text).toBe('Compacted summary');
  });

});
