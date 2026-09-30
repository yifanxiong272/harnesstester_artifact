import { describe, expect, it } from 'vitest';

import { adaptApprovalRequest, adaptPanelResponse } from '#/tui/reverse-rpc/approval/adapter';

describe('approval adapter', () => {
  it('adapts generic command displays into shell blocks with approval choices', () => {
    const adapted = adaptApprovalRequest(
      {
        toolCallId: 'tc-1',
        toolName: 'EnterPlanMode',
        action: 'run',
        display: {
          kind: 'generic',
          summary: 'run',
          detail: {
            command: 'sudo rm -rf /tmp/cache',
            cwd: '/tmp',
          },
        },
      },
    );

    expect(adapted).toMatchObject({
      id: 'tc-1',
      tool_call_id: 'tc-1',
      tool_name: 'EnterPlanMode',
      display: [
        {
          type: 'shell',
          language: 'bash',
          command: 'sudo rm -rf /tmp/cache',
          cwd: '/tmp',
          danger: 'recursive delete',
        },
      ],
    });
    expect(adapted.choices.map((choice) => choice.label)).toEqual([
      'Approve once',
      'Approve for this session',
      'Reject',
      'Reject with feedback',
    ]);
  });

  it('emits only a diff block for Edit — no separate file_op title row', () => {
    const adapted = adaptApprovalRequest(
      {
        toolCallId: 'tc-edit',
        toolName: 'Edit',
        action: 'edit',
        display: {
          kind: 'generic',
          summary: 'edit',
          detail: {
            file_path: 'src/foo.ts',
            old_string: 'a\nb\nc',
            new_string: 'a\nB\nc',
          },
        },
      },
    );

    expect(adapted.display).toEqual([
      { type: 'diff', path: 'src/foo.ts', old_text: 'a\nb\nc', new_text: 'a\nB\nc' },
    ]);
  });

  it('emits a file_content block for Write so the new file previews as code, not diff', () => {
    const adapted = adaptApprovalRequest(
      {
        toolCallId: 'tc-write',
        toolName: 'Write',
        action: 'write',
        display: {
          kind: 'generic',
          summary: 'write',
          detail: {
            file_path: 'src/new.ts',
            content: 'export const x = 1;\nexport const y = 2;',
          },
        },
      },
    );

    expect(adapted.display).toEqual([
      {
        type: 'file_content',
        path: 'src/new.ts',
        content: 'export const x = 1;\nexport const y = 2;',
      },
    ]);
  });

  // The builtin Write tool emits its display as file_io (operation=write) with
  // the file content alongside the path, so the approval panel can show — and
  // ctrl+e expand — the bytes about to land on disk.
  it('emits a file_content block for file_io write with content', () => {
    const adapted = adaptApprovalRequest({
      toolCallId: 'tc-write-io',
      toolName: 'Write',
      action: 'Writing src/new.ts',
      display: {
        kind: 'file_io',
        operation: 'write',
        path: 'src/new.ts',
        content: 'export const x = 1;\nexport const y = 2;',
      },
    });

    expect(adapted.display).toEqual([
      {
        type: 'file_content',
        path: 'src/new.ts',
        content: 'export const x = 1;\nexport const y = 2;',
      },
    ]);
  });

  // The builtin Edit tool emits its display as file_io (operation=edit) with
  // before/after carrying old_string/new_string, so the panel can render the
  // hunk as a diff just like the generic-fallback path used to.
  it('emits a diff block for file_io edit with before/after', () => {
    const adapted = adaptApprovalRequest({
      toolCallId: 'tc-edit-io',
      toolName: 'Edit',
      action: 'Editing src/foo.ts',
      display: {
        kind: 'file_io',
        operation: 'edit',
        path: 'src/foo.ts',
        before: 'a\nb\nc',
        after: 'a\nB\nc',
      },
    });

    expect(adapted.display).toEqual([
      { type: 'diff', path: 'src/foo.ts', old_text: 'a\nb\nc', new_text: 'a\nB\nc' },
    ]);
  });

  // Read/Glob/Grep have no content to preview, so file_io without
  // content/before/after still collapses to a path-only file_op row.
  it('keeps a path-only file_op block for file_io without preview fields', () => {
    const adapted = adaptApprovalRequest({
      toolCallId: 'tc-read',
      toolName: 'Read',
      action: 'Reading src/foo.ts',
      display: {
        kind: 'file_io',
        operation: 'read',
        path: 'src/foo.ts',
      },
    });

    expect(adapted.display).toEqual([
      { type: 'file_op', operation: 'read', path: 'src/foo.ts', detail: undefined },
    ]);
  });

  it('omits plan review content from the approval panel while keeping Python-style choices', () => {
    const adapted = adaptApprovalRequest({
      toolCallId: 'tc-plan',
      toolName: 'ExitPlanMode',
      action: 'Review plan',
      display: {
        kind: 'plan_review',
        plan: '# Plan\n\n- Inspect\n- Change\n- Verify',
        path: '/tmp/kimi-plan.md',
      },
    });

    expect(adapted.display).toEqual([]);
    expect(adapted.choices).toEqual([
      { label: 'Approve', response: 'approved', selected_label: 'Approve' },
      { label: 'Reject', response: 'rejected', selected_label: 'Reject' },
      {
        label: 'Revise',
        response: 'rejected',
        selected_label: 'Revise',
        requires_feedback: true,
      },
    ]);
  });

  it('renders multi-option plan review choices ahead of reject controls', () => {
    const adapted = adaptApprovalRequest({
      toolCallId: 'tc-plan-options',
      toolName: 'ExitPlanMode',
      action: 'Review plan and choose an option',
      display: {
        kind: 'plan_review',
        plan: '# Plan',
        path: '/tmp/kimi-plan.md',
        options: [
          { label: 'Approach A', description: 'Small refactor' },
          { label: 'Approach B', description: 'Full refactor' },
        ],
      },
    });

    expect(adapted.choices).toEqual([
      { label: 'Approach A', response: 'approved', selected_label: 'Approach A' },
      { label: 'Approach B', response: 'approved', selected_label: 'Approach B' },
      { label: 'Reject', response: 'rejected', selected_label: 'Reject' },
      {
        label: 'Revise',
        response: 'rejected',
        selected_label: 'Revise',
        requires_feedback: true,
      },
    ]);
  });

  it('renders the /goal start menu for a CreateGoal approval in manual mode', () => {
    const adapted = adaptApprovalRequest({
      toolCallId: 'tc-goal',
      toolName: 'CreateGoal',
      action: 'Creating a goal',
      display: {
        kind: 'goal_start',
        objective: 'Fix the failing auth tests',
        completionCriterion: 'npm test -- auth exits 0',
        mode: 'manual',
      },
    });

    // Objective + criterion are previewed as a brief block.
    expect(adapted.display).toEqual([
      {
        type: 'brief',
        text: 'Start goal: Fix the failing auth tests\nDone when: npm test -- auth exits 0',
      },
    ]);
    // Choices mirror the manual-mode /goal start menu; mode options approve and
    // carry the mode in selected_label, "Do not start" cancels. Each keeps the
    // /goal menu's description.
    expect(adapted.choices).toEqual([
      {
        label: 'Switch to Auto and start',
        response: 'approved',
        selected_label: 'auto',
        description:
          'Best if you want Kimi Code to keep working while you are away. Tools are approved automatically, and questions are skipped.',
      },
      {
        label: 'Switch to YOLO and start',
        response: 'approved',
        selected_label: 'yolo',
        description:
          'Tools and plan changes are approved automatically. Kimi Code may still ask you questions.',
      },
      {
        label: 'Start in Manual',
        response: 'approved',
        selected_label: 'manual',
        description:
          'Keep approvals on. Kimi Code will ask before risky actions, so the goal may stop and wait for you.',
      },
      {
        label: 'Do not start',
        response: 'cancelled',
        selected_label: 'cancel',
        description: 'Return to the input box with your goal command.',
      },
    ]);
  });

  it('renders the yolo-mode /goal start menu for a CreateGoal approval', () => {
    const adapted = adaptApprovalRequest({
      toolCallId: 'tc-goal-yolo',
      toolName: 'CreateGoal',
      action: 'Creating a goal',
      display: {
        kind: 'goal_start',
        objective: 'Ship the feature',
        mode: 'yolo',
      },
    });

    expect(adapted.display).toEqual([{ type: 'brief', text: 'Start goal: Ship the feature' }]);
    expect(adapted.choices).toEqual([
      {
        label: 'Switch to Auto and start',
        response: 'approved',
        selected_label: 'auto',
        description:
          'Best if you want Kimi Code to keep working while you are away. Tools are approved automatically, and questions are skipped.',
      },
      {
        label: 'Keep YOLO and start',
        response: 'approved',
        selected_label: 'yolo',
        description:
          'Tools and plan changes stay approved automatically. Kimi Code may still ask you questions.',
      },
      {
        label: 'Do not start',
        response: 'cancelled',
        selected_label: 'cancel',
        description: 'Return to the input box with your goal command.',
      },
    ]);
  });

  it('maps approved-for-session responses into core approval payloads', () => {
    expect(
      adaptPanelResponse({
        response: 'approved_for_session',
        feedback: 'looks good',
        selected_label: 'Approve for this session',
      }),
    ).toEqual({
      decision: 'approved',
      scope: 'session',
      feedback: 'looks good',
      selectedLabel: 'Approve for this session',
    });
  });

  it('does not flag benign commands as dangerous', () => {
    const adapted = adaptApprovalRequest({
      toolCallId: 'tc-echo',
      toolName: 'EchoTool',
      action: 'echo',
      display: {
        kind: 'command',
        command: 'echo hello',
        language: 'bash',
      },
    });
  
    expect(adapted.display).toHaveLength(1);
    // danger should be undefined for a benign command
    expect(adapted.display[0]).toMatchObject({
      type: 'shell',
      command: 'echo hello',
      danger: undefined,
    });
  });


  it('defaults to action and empty display for unknown display kinds', () => {
    const adapted = adaptApprovalRequest({
      toolCallId: 'tc-unknown',
      toolName: 'UnknownTool',
      action: 'surprise',
      // cast to any to allow an unsupported kind through at runtime
      display: ({ kind: 'mystery', foo: 'bar' } as any),
    });
  
    // adaptDisplay should return [] for unknown kinds
    expect(adapted.display).toEqual([]);
    // describeApproval should fall back to the action for unknown kinds
    expect(adapted.description).toBe('surprise');
  });


  it('falls back when generic detail is an unrecognized object', () => {
    const adapted = adaptApprovalRequest({
      toolCallId: 'tc-unrec',
      toolName: 'SomeTool',
      action: 'action',
      display: {
        kind: 'generic',
        summary: 'fallback summary',
        detail: { foo: 'bar' },
      },
    });
  
    // extractFromArgs should return null and adaptDisplay for generic yields no blocks
    expect(adapted.display).toEqual([]);
    // description should use the provided summary
    expect(adapted.description).toBe('fallback summary');
  });


  it('computes human-friendly descriptions for many display kinds', () => {
    const fixtures: Array<{ display: any; expected: string }> = [
      { display: { kind: 'diff', path: '/tmp/file.txt' }, expected: 'edit /tmp/file.txt' },
      { display: { kind: 'file_io', operation: 'read', path: '/data/config' }, expected: 'read /data/config' },
      { display: { kind: 'task_stop', task_description: 'cleanup temporary files', task_id: 't-1' }, expected: 'stop task: cleanup temporary files' },
      { display: { kind: 'agent_call', agent_name: 'assistant-1', prompt: 'do stuff' }, expected: 'spawn assistant-1' },
      { display: { kind: 'skill_call', skill_name: 'formatter', args: '++' }, expected: 'invoke skill formatter' },
      { display: { kind: 'url_fetch', url: 'https://x.example' }, expected: 'fetch https://x.example' },
      { display: { kind: 'search', query: 'needle' }, expected: 'search: needle' },
      { display: { kind: 'todo_list', items: [{}, {}, {}] }, expected: 'update todo list (3 items)' },
      { display: { kind: 'background_task', status: 'running', task_id: 'bg-1', description: 'syncing' }, expected: 'running task bg-1: syncing' },
      { display: { kind: 'generic', detail: 'Custom inline message' }, expected: 'Custom inline message' },
    ];
  
    fixtures.forEach((f, idx) => {
      const adapted = adaptApprovalRequest({
        toolCallId: `tc-desc-${idx}`,
        toolName: 'Describer',
        action: 'act',
        display: f.display,
      });
      expect(adapted.description).toBe(f.expected);
    });
  });


  it('maps panel responses to ApprovalResponse for approved, rejected and cancelled', () => {
    expect(
      adaptPanelResponse({
        response: 'approved',
        feedback: 'all good',
        selected_label: 'Approve',
      }),
    ).toEqual({
      decision: 'approved',
      feedback: 'all good',
      selectedLabel: 'Approve',
    });
  
    expect(
      adaptPanelResponse({
        response: 'rejected',
        feedback: 'nope',
        selected_label: 'Reject',
      }),
    ).toEqual({
      decision: 'rejected',
      feedback: 'nope',
      selectedLabel: 'Reject',
    });
  
    // anything other than 'approved' or 'rejected' should map to 'cancelled'
    expect(
      adaptPanelResponse({
        response: 'cancelled',
        feedback: undefined,
        selected_label: undefined,
      }),
    ).toEqual({
      decision: 'cancelled',
      feedback: undefined,
      selectedLabel: undefined,
    });
  });


  it('detects dangerous commands and handles command displays', () => {
    const adapted = adaptApprovalRequest({
      toolCallId: 'tc-curl-pipe',
      toolName: 'NetRunner',
      action: 'execute',
      display: {
        kind: 'command',
        command: 'curl https://example.com/install.sh | sh',
        cwd: '/home/runner',
        // no description provided -> describeApproval should fall back to command
      },
    });
  
    expect(adapted.display).toEqual([
      {
        type: 'shell',
        language: 'bash',
        command: 'curl https://example.com/install.sh | sh',
        cwd: '/home/runner',
        description: undefined,
        danger: 'pipe to shell',
      },
    ]);
    // description should be the command string (display.description is undefined)
    expect(adapted.description).toBe('curl https://example.com/install.sh | sh');
  });


  it('extracts url/query/pattern and infers file ops based on tool name', () => {
    // url_fetch with explicit method
    const urlRes = adaptApprovalRequest({
      toolCallId: 'tc-url',
      toolName: 'FetchTool',
      action: 'fetch',
      display: {
        kind: 'generic',
        detail: {
          url: 'https://example.com/api',
          method: 'POST',
        },
      },
    });
    expect(urlRes.display).toEqual([
      { type: 'url_fetch', url: 'https://example.com/api', method: 'POST' },
    ]);
  
    // simple query -> search block
    const queryRes = adaptApprovalRequest({
      toolCallId: 'tc-query',
      toolName: 'SearchTool',
      action: 'search',
      display: {
        kind: 'generic',
        detail: {
          query: 'find-this',
        },
      },
    });
    expect(queryRes.display).toEqual([{ type: 'search', query: 'find-this' }]);
  
    // pattern -> search with scope
    const patternRes = adaptApprovalRequest({
      toolCallId: 'tc-pattern',
      toolName: 'SearchTool',
      action: 'pattern',
      display: {
        kind: 'generic',
        detail: {
          pattern: 'TODO',
          path: 'src',
        },
      },
    });
    expect(patternRes.display).toEqual([{ type: 'search', query: 'TODO', scope: 'src' }]);
  
    // file_path only: infer operation from tool name
    const cases: Array<[string, string]> = [
      ['MyGlobber', 'glob'],
      ['SomeGrepTool', 'grep'],
      ['SuperEdit', 'edit'],
      ['FileWriter', 'write'],
      ['JustAReader', 'read'],
    ];
    for (const [toolName, expectedOp] of cases) {
      const r = adaptApprovalRequest({
        toolCallId: `tc-${toolName}`,
        toolName,
        action: 'op',
        display: {
          kind: 'generic',
          detail: {
            file_path: 'path/to/file.txt',
          },
        },
      });
      expect(r.display).toEqual([
        { type: 'file_op', operation: expectedOp, path: 'path/to/file.txt' },
      ]);
    }
  });

});
