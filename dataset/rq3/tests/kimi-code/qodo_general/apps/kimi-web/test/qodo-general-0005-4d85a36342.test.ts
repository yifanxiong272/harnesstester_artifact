import { describe, expect, it } from 'vitest';
import type { AppMessage, AppMessageContent } from '../src/api/types';
import { latestTodos } from '../src/composables/latestTodos';
import { messagesToTurns } from '../src/composables/messagesToTurns';

function message(
  id: string,
  role: AppMessage['role'],
  content: AppMessageContent[],
  extra: Partial<AppMessage> = {},
): AppMessage {
  return {
    id,
    sessionId: 'session-1',
    role,
    content,
    createdAt: '2026-01-01T00:00:00.000Z',
    ...extra,
  };
}

describe('messagesToTurns', () => {
  it('merges an assistant turn and folds tool results into it', () => {
    const turns = messagesToTurns(
      [
        message('u1', 'user', [{ type: 'text', text: 'hello' }]),
        message('a1', 'assistant', [
          { type: 'thinking', thinking: 'plan' },
          { type: 'toolUse', toolCallId: 'tool-1', toolName: 'read', input: { path: 'src/a.ts' } },
        ]),
        message('t1', 'tool', [{ type: 'toolResult', toolCallId: 'tool-1', output: 'alpha\nbeta' }]),
        message('a2', 'assistant', [{ type: 'text', text: 'done' }]),
      ],
      [],
      undefined,
      false,
      [],
    );

    expect(turns).toHaveLength(2);
    expect(turns[1]).toMatchObject({
      role: 'assistant',
      thinking: 'plan',
      text: 'done',
    });
    expect(turns[1]?.tools).toMatchObject([
      { id: 'tool-1', status: 'ok', output: ['alpha', 'beta'] },
    ]);
  });

  it('splits assistant turns when prompt ids differ', () => {
    const turns = messagesToTurns(
      [
        message('a1', 'assistant', [{ type: 'text', text: 'one' }], { promptId: 'p1' }),
        message('a2', 'assistant', [{ type: 'text', text: 'two' }], { promptId: 'p2' }),
      ],
      [],
      undefined,
      false,
      [],
    );

    expect(turns.map((turn) => turn.text)).toEqual(['one', 'two']);
  });

  it('renders compaction summaries as divider turns', () => {
    const turns = messagesToTurns(
      [
        message('s1', 'assistant', [{ type: 'text', text: 'summary' }], {
          metadata: { origin: { kind: 'compaction_summary' } },
        }),
      ],
      [],
      undefined,
      false,
      [],
    );

    expect(turns).toMatchObject([{ role: 'compaction', text: 'summary' }]);
  });
});

describe('latestTodos', () => {
  it('returns the newest todo write and ignores later read-only queries', () => {
    expect(
      latestTodos([
        message('a1', 'assistant', [
          {
            type: 'toolUse',
            toolCallId: 'todo-1',
            toolName: 'TodoWrite',
            input: { todos: [{ title: 'old', status: 'pending' }] },
          },
        ]),
        message('a2', 'assistant', [
          {
            type: 'toolUse',
            toolCallId: 'todo-2',
            toolName: 'TodoWrite',
            input: JSON.stringify({ todos: [{ content: 'new', status: 'completed' }] }),
          },
        ]),
        message('a3', 'assistant', [
          { type: 'toolUse', toolCallId: 'todo-3', toolName: 'TodoRead', input: {} },
        ]),
      ]),
    ).toEqual([{ title: 'new', status: 'done' }]);
  });
});

  it('builds approval blocks for multiple kinds and attaches them to the correct assistant turns', () => {
    const approvals = [
      {
        approvalId: 'ap-diff',
        toolCallId: 'call-diff',
        action: 'do-diff',
        display: { kind: 'diff', path: '/p', diff: [{ kind: 'rem', gutter: '1', text: '- a' }] },
      },
      {
        approvalId: 'ap-shell',
        toolCallId: 'call-shell',
        action: 'run-me',
        display: { kind: 'shell' }, // no command -> fallback to action
      },
      {
        approvalId: 'ap-fileop',
        toolCallId: 'call-fileop',
        action: 'fileop',
        display: { kind: 'file_op', operation: 'delete', path: '/x', detail: 'danger' },
      },
      {
        approvalId: 'ap-url',
        toolCallId: 'call-url',
        action: 'https://example.com/fallback',
        display: { kind: 'url' }, // no url -> fallback to action
      },
      {
        approvalId: 'ap-search',
        toolCallId: 'call-search',
        action: 'search-action',
        display: { kind: 'search', query: 'q1', scope: 'all' },
      },
      {
        approvalId: 'ap-invoke',
        toolCallId: 'call-invoke',
        action: 'invoke-action',
        toolName: 'SomeTool',
        display: { kind: 'invocation', kind: 'skill_call', name: 'SkillX', description: 'Do X' },
      },
      {
        approvalId: 'ap-todo',
        toolCallId: 'call-todo',
        action: 'todo-action',
        display: { kind: 'todo_list', items: [{ title: 'T1', status: 'done' }, {}] },
      },
    ];
  
    // For each approval we create an assistant toolUse turn, then a user message to flush it.
    const msgs = [
      message('a1', 'assistant', [{ type: 'toolUse', toolCallId: 'call-diff', toolName: 'x', input: {} }]),
      message('u1', 'user', [{ type: 'text', text: 'ok' }]),
      message('a2', 'assistant', [{ type: 'toolUse', toolCallId: 'call-shell', toolName: 'x', input: {} }]),
      message('u2', 'user', [{ type: 'text', text: 'ok' }]),
      message('a3', 'assistant', [{ type: 'toolUse', toolCallId: 'call-fileop', toolName: 'x', input: {} }]),
      message('u3', 'user', [{ type: 'text', text: 'ok' }]),
      message('a4', 'assistant', [{ type: 'toolUse', toolCallId: 'call-url', toolName: 'x', input: {} }]),
      message('u4', 'user', [{ type: 'text', text: 'ok' }]),
      message('a5', 'assistant', [{ type: 'toolUse', toolCallId: 'call-search', toolName: 'x', input: {} }]),
      message('u5', 'user', [{ type: 'text', text: 'ok' }]),
      message('a6', 'assistant', [{ type: 'toolUse', toolCallId: 'call-invoke', toolName: 'x', input: {} }]),
      message('u6', 'user', [{ type: 'text', text: 'ok' }]),
      message('a7', 'assistant', [{ type: 'toolUse', toolCallId: 'call-todo', toolName: 'x', input: {} }]),
      message('u7', 'user', [{ type: 'text', text: 'ok' }]),
    ];
  
    const turns = messagesToTurns(msgs, approvals as any, undefined, false, []);
  
    const findApprovalFor = (callId: string) =>
      turns.find((turn) => (turn.blocks ?? []).some((b) => b.kind === 'tool' && b.tool.id === callId))
        ?.approval;
  
    const diff = findApprovalFor('call-diff') as any;
    expect(diff).toBeTruthy();
    expect(diff.kind).toBe('diff');
    expect(diff.path).toBe('/p');
    expect(Array.isArray(diff.diff) && diff.diff.length > 0).toBe(true);
  
    const shell = findApprovalFor('call-shell') as any;
    expect(shell).toBeTruthy();
    expect(shell.kind).toBe('shell');
    expect(shell.command).toBe('run-me'); // fell back to approval.action
  
    const fileop = findApprovalFor('call-fileop') as any;
    expect(fileop).toBeTruthy();
    expect(fileop.kind).toBe('fileop');
    expect(fileop.op).toBe('delete');
    expect(fileop.path).toBe('/x');
    expect(fileop.detail).toBe('danger');
  
    const url = findApprovalFor('call-url') as any;
    expect(url).toBeTruthy();
    expect(url.kind).toBe('url');
    expect(url.url).toBe('https://example.com/fallback');
  
    const search = findApprovalFor('call-search') as any;
    expect(search).toBeTruthy();
    expect(search.kind).toBe('search');
    expect(search.query).toBe('q1');
  
    const inv = findApprovalFor('call-invoke') as any;
    expect(inv).toBeTruthy();
    expect(inv.kind).toBe('invocation');
    // name should pick up display.name when present
    expect(inv.name).toBe('SkillX');
  
    const todo = findApprovalFor('call-todo') as any;
    expect(todo).toBeTruthy();
    expect(todo.kind).toBe('todo');
    expect(Array.isArray(todo.items)).toBe(true);
    expect(todo.items[0]).toMatchObject({ title: 'T1', status: 'done' });
    // second item missing fields should default
    expect(todo.items[1]).toMatchObject({ title: '', status: 'pending' });
  });


  it('normalizeToolOutput stringifies unknown object outputs into a single-line array', () => {
    const obj = { foo: 'bar', n: 1 };
    const turns = messagesToTurns(
      [
        message('a1', 'assistant', [
          {
            type: 'toolUse',
            toolCallId: 'tool-obj-1',
            toolName: 'someTool',
            input: {},
          },
        ]),
        message('t1', 'tool', [
          {
            type: 'toolResult',
            toolCallId: 'tool-obj-1',
            output: obj,
          },
        ]),
      ],
      [],
      undefined,
      false,
      [],
    );
  
    const assistant = turns.find((t) => t.role === 'assistant');
    expect(assistant).toBeTruthy();
    const tool = assistant!.tools?.[0];
    expect(tool).toBeTruthy();
    expect(tool?.output).toEqual([JSON.stringify(obj)]);
  });


  it('returns undefined media when read_media output is invalid JSON', () => {
    const turns = messagesToTurns(
      [
        message('u1', 'user', [{ type: 'text', text: 'please read' }]),
        message('a1', 'assistant', [
          {
            type: 'toolUse',
            toolCallId: 'call-media-invalid',
            toolName: 'read_mediafile',
            input: {},
          },
        ]),
        // tool role message holds the toolResult as a plain (invalid JSON) string
        message('t1', 'tool', [
          {
            type: 'toolResult',
            toolCallId: 'call-media-invalid',
            output: 'not a json array',
          },
        ]),
      ],
      [],
      undefined,
      false,
      [],
    );
  
    const assistant = turns.find((t) => t.role === 'assistant');
    expect(assistant).toBeTruthy();
    const tools = assistant?.tools ?? [];
    expect(tools).toHaveLength(1);
    // Output is a string -> normalized into lines; media should be undefined because the JSON parse failed
    expect(tools[0]).toMatchObject({
      id: 'call-media-invalid',
      output: ['not a json array'],
      media: undefined,
    });
  });


  it('normalizes media output produced by read_media tools including data URLs and system metadata (no padding)', () => {
    // Build an assistant turn that calls a read_media tool, then a tool role message
    // that returns a ContentPart[] (array form) including:
    // - a text part that is exactly the MEDIA_PATH_TAG so the anchored regex matches
    // - another text part with system metadata (mime + dimensions)
    // - an image_url part whose url is a data:... base64 string (no padding -> 'AAAA')
    const msgs = [
      message('u1', 'user', [{ type: 'text', text: 'please read' }]),
      message(
        'a1',
        'assistant',
        [
          {
            type: 'toolUse',
            toolCallId: 'call-media-1',
            toolName: 'read_mediafile',
            input: {},
          },
        ],
      ),
      // tool role message carries the toolResult content as an array (already-structured)
      message(
        't1',
        'tool',
        [
          {
            type: 'toolResult',
            toolCallId: 'call-media-1',
            // output is an actual array of content parts (not a JSON string)
            output: [
              { type: 'text', text: '<image path="/p.jpg">' }, // exact tag line to match anchored regex
              { type: 'text', text: 'Original dimensions: 10x20 pixels\nMime type: image/png' },
              {
                type: 'image_url',
                imageUrl: { url: 'data:image/png;base64,AAAA' }, // 'AAAA' -> bytesFromBase64 -> 3
              },
            ],
          },
        ],
      ),
    ];
  
    const turns = messagesToTurns(msgs, [], undefined, false, []);
    const assistant = turns.find((t) => t.role === 'assistant');
    expect(assistant).toBeTruthy();
    const tools = assistant?.tools ?? [];
    expect(tools).toHaveLength(1);
    const media = tools[0]!.media!;
    // The data URL overrides mime and bytes; path and dimensions come from text parts
    expect(media).toMatchObject({
      kind: 'image',
      url: 'data:image/png;base64,AAAA',
      path: '/p.jpg',
      mimeType: 'image/png',
      bytes: 3,
      dimensions: '10x20',
    });
  });


  it('rebuilds an Agent member card from an Agent tool call and its result', () => {
    const msgs = [
      message('a1', 'assistant', [
        {
          type: 'toolUse',
          toolCallId: 'agent-call-1',
          toolName: 'agent',
          input: JSON.stringify({
            description: 'My Agent',
            subagent_type: 'worker',
            prompt: 'please do it',
          }),
        },
      ]),
      // tool result present -> member should be marked completed and get a summary
      message('t1', 'tool', [
        {
          type: 'toolResult',
          toolCallId: 'agent-call-1',
          output: 'result-line1\nresult-line2',
          isError: false,
        },
      ]),
    ];
  
    const turns = messagesToTurns(msgs, [], undefined, true, []);
    const assistant = turns.find((t) => t.role === 'assistant');
    expect(assistant).toBeTruthy();
    const agentBlock = assistant!.blocks?.find((b) => (b as any).kind === 'agent') as any;
    expect(agentBlock).toBeTruthy();
    const member = agentBlock.member;
    expect(member).toMatchObject({
      id: 'agent-call-1',
      toolCallId: 'agent-call-1',
      name: 'My Agent',
      subagentType: 'worker',
      prompt: 'please do it',
      phase: 'completed',
      status: 'completed',
      summary: 'result-line1\nresult-line2',
    });
  });


  it('normalizes tool output arrays with mixed part types into flattened lines', () => {
    const msgs = [
      message('u1', 'user', [{ type: 'text', text: 'run' }]),
      message('a1', 'assistant', [
        {
          type: 'toolUse',
          toolCallId: 'call-out-1',
          toolName: 'SomeTool',
          input: {},
        },
      ]),
      message('t1', 'tool', [
        {
          type: 'toolResult',
          toolCallId: 'call-out-1',
          // output as an actual array of mixed parts
          output: [
            'lineA\nlineB',
            { type: 'text', text: 't1\nt2' },
            { type: 'think', think: 'thinking' },
            { type: 'image', imageUrl: { url: 'http://x' } },
            { type: 'customType', foo: 'bar' },
            { foo: 'plainobject' }, // no type -> JSON.stringify
          ],
        },
      ]),
    ];
  
    const turns = messagesToTurns(msgs, [], undefined, false, []);
    const assistant = turns.find((t) => t.role === 'assistant');
    expect(assistant).toBeTruthy();
    const tool = assistant!.tools?.[0];
    expect(tool).toBeTruthy();
    expect(tool!.output).toEqual([
      'lineA',
      'lineB',
      't1',
      't2',
      'thinking',
      '[image]',
      '[customType]',
      JSON.stringify({ foo: 'plainobject' }),
    ]);
  });

