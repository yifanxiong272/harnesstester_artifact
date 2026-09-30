import { describe, expect, it } from 'vitest';

import {
  AgentSideConnection,
  ClientSideConnection,
  ndJsonStream,
  type Client,
  type ContentBlock,
  type ReadTextFileRequest,
  type ReadTextFileResponse,
  type RequestPermissionRequest,
  type RequestPermissionResponse,
  type SessionNotification,
  type WriteTextFileRequest,
  type WriteTextFileResponse,
} from '@agentclientprotocol/sdk';
import type { Event, KimiHarness, Session } from '@moonshot-ai/kimi-code-sdk';

import { AcpServer } from '../src/server';
import { AUTHED_STATUS } from './_helpers/harness-stubs';
import { AcpSession } from '../src/session';

class CollectingClient implements Client {
  readonly updates: SessionNotification[] = [];

  /**
   * Updates produced AFTER `session/new` returns. Phase 9.3 makes
   * `newSession` emit exactly one `available_commands_update` on
   * creation; existing tests assert only on prompt-driven updates,
   * so we filter that variant out.
   */
  get promptUpdates(): readonly SessionNotification[] {
    return this.updates.filter(
      (n) =>
        (n.update as { sessionUpdate?: string }).sessionUpdate !==
        'available_commands_update',
    );
  }

  async requestPermission(_p: RequestPermissionRequest): Promise<RequestPermissionResponse> {
    throw new Error('CollectingClient.requestPermission should not be called in tool-call-stream test');
  }
  async sessionUpdate(n: SessionNotification): Promise<void> {
    this.updates.push(n);
  }
  async writeTextFile(_p: WriteTextFileRequest): Promise<WriteTextFileResponse> {
    throw new Error('CollectingClient.writeTextFile should not be called in tool-call-stream test');
  }
  async readTextFile(_p: ReadTextFileRequest): Promise<ReadTextFileResponse> {
    throw new Error('CollectingClient.readTextFile should not be called in tool-call-stream test');
  }
}

function makeInMemoryStreamPair(): {
  agentStream: ReturnType<typeof ndJsonStream>;
  clientStream: ReturnType<typeof ndJsonStream>;
} {
  const clientToAgent = new TransformStream<Uint8Array, Uint8Array>();
  const agentToClient = new TransformStream<Uint8Array, Uint8Array>();
  const agentStream = ndJsonStream(agentToClient.writable, clientToAgent.readable);
  const clientStream = ndJsonStream(clientToAgent.writable, agentToClient.readable);
  return { agentStream, clientStream };
}

function makeScriptedSession(
  sessionId: string,
  script: readonly Event[],
): Session {
  const listeners = new Set<(event: Event) => void>();
  const session = {
    id: sessionId,
    prompt: async (_input: unknown) => {
      for (const ev of script) {
        for (const fn of listeners) fn(ev);
      }
    },
    cancel: async () => undefined,
    onEvent: (fn: (event: Event) => void) => {
      listeners.add(fn);
      return () => {
        listeners.delete(fn);
      };
    },
  } as unknown as Session;
  return session;
}

const textBlock = (text: string): ContentBlock => ({ type: 'text', text });

async function flushNdjson(): Promise<void> {
  // Let queued sessionUpdate writes drain through the ndjson stream.
  await new Promise((resolve) => setTimeout(resolve, 25));
}

describe('AcpServer tool-call streaming', () => {
  it('streams tool_call (start) → tool_call_update (delta x N) → end_turn for a single tool call', async () => {
    const sessionId = 'sess-tc-1';
    const turnId = 1;
    const toolCallId = 'tc-abc';
    const session = makeScriptedSession(sessionId, [
      {
        type: 'tool.call.started',
        sessionId,
        agentId: 'main',
        turnId,
        toolCallId,
        name: 'Read',
        args: { path: 'a' },
      } as Event,
      {
        type: 'tool.call.delta',
        sessionId,
        agentId: 'main',
        turnId,
        toolCallId,
        argumentsPart: ', "lim',
      } as Event,
      {
        type: 'tool.call.delta',
        sessionId,
        agentId: 'main',
        turnId,
        toolCallId,
        argumentsPart: 'it": 5}',
      } as Event,
      { type: 'turn.ended', sessionId, agentId: 'main', turnId, reason: 'completed' } as Event,
    ]);
    const harness = {
      auth: { status: async () => AUTHED_STATUS },
      createSession: async () => session,
    } as unknown as KimiHarness;

    const { agentStream, clientStream } = makeInMemoryStreamPair();
    new AgentSideConnection((c) => new AcpServer(harness, c), agentStream);
    const collecting = new CollectingClient();
    const client = new ClientSideConnection(() => collecting, clientStream);

    await client.newSession({ cwd: '/tmp/x', mcpServers: [] });
    const response = await client.prompt({ sessionId, prompt: [textBlock('go')] });
    expect(response.stopReason).toBe('end_turn');
    await flushNdjson();

    expect(collecting.promptUpdates).toHaveLength(3);

    // 1) tool_call (creation) with stringified initial args.
    expect(collecting.promptUpdates[0]?.update).toMatchObject({
      sessionUpdate: 'tool_call',
      toolCallId: `${turnId}:${toolCallId}`,
      title: 'Read',
      kind: 'read',
      status: 'in_progress',
      rawInput: { path: 'a' },
      content: [
        {
          type: 'content',
          content: { type: 'text', text: JSON.stringify({ path: 'a' }) },
        },
      ],
    });

    // 2) first delta — cumulative args = initial + first part.
    const firstCumulative = `${JSON.stringify({ path: 'a' })}, "lim`;
    expect(collecting.promptUpdates[1]?.update).toMatchObject({
      sessionUpdate: 'tool_call_update',
      toolCallId: `${turnId}:${toolCallId}`,
      status: 'in_progress',
      content: [
        { type: 'content', content: { type: 'text', text: firstCumulative } },
      ],
    });

    // 3) second delta — cumulative args = initial + first + second.
    const secondCumulative = `${firstCumulative}it": 5}`;
    expect(collecting.promptUpdates[2]?.update).toMatchObject({
      sessionUpdate: 'tool_call_update',
      toolCallId: `${turnId}:${toolCallId}`,
      status: 'in_progress',
      content: [
        { type: 'content', content: { type: 'text', text: secondCumulative } },
      ],
    });
  });

  it('uses turn-prefixed toolCallId so identical SDK ids across turns do not collide', async () => {
    // We script two consecutive `tool.call.started` events with the
    // SAME SDK `toolCallId` but DIFFERENT `turnId` to assert the ACP
    // wire ids are distinct.
    const sessionId = 'sess-tc-collision';
    const session = makeScriptedSession(sessionId, [
      {
        type: 'tool.call.started',
        sessionId,
        agentId: 'main',
        turnId: 1,
        toolCallId: 'X',
        name: 'Bash',
        args: { cmd: 'ls' },
      } as Event,
      {
        type: 'tool.call.started',
        sessionId,
        agentId: 'main',
        turnId: 2,
        toolCallId: 'X',
        name: 'Bash',
        args: { cmd: 'pwd' },
      } as Event,
      { type: 'turn.ended', sessionId, agentId: 'main', turnId: 2, reason: 'completed' } as Event,
    ]);
    const harness = {
      auth: { status: async () => AUTHED_STATUS },
      createSession: async () => session,
    } as unknown as KimiHarness;

    const { agentStream, clientStream } = makeInMemoryStreamPair();
    new AgentSideConnection((c) => new AcpServer(harness, c), agentStream);
    const collecting = new CollectingClient();
    const client = new ClientSideConnection(() => collecting, clientStream);

    await client.newSession({ cwd: '/tmp/x', mcpServers: [] });
    await client.prompt({ sessionId, prompt: [textBlock('go')] });
    await flushNdjson();

    const startUpdates = collecting.updates.filter(
      (n) => (n.update as { sessionUpdate: string }).sessionUpdate === 'tool_call',
    );
    expect(startUpdates).toHaveLength(2);
    const ids = startUpdates.map((n) => (n.update as { toolCallId: string }).toolCallId);
    expect(ids).toEqual(['1:X', '2:X']);
    expect(ids[0]).not.toBe(ids[1]);
  });

  it('emits agent_thought_chunk for thinking.delta events', async () => {
    const sessionId = 'sess-thinking';
    const session = makeScriptedSession(sessionId, [
      { type: 'thinking.delta', sessionId, agentId: 'main', turnId: 1, delta: 'hmm' } as Event,
      { type: 'turn.ended', sessionId, agentId: 'main', turnId: 1, reason: 'completed' } as Event,
    ]);
    const harness = {
      auth: { status: async () => AUTHED_STATUS },
      createSession: async () => session,
    } as unknown as KimiHarness;

    const { agentStream, clientStream } = makeInMemoryStreamPair();
    new AgentSideConnection((c) => new AcpServer(harness, c), agentStream);
    const collecting = new CollectingClient();
    const client = new ClientSideConnection(() => collecting, clientStream);

    await client.newSession({ cwd: '/tmp/x', mcpServers: [] });
    await client.prompt({ sessionId, prompt: [textBlock('go')] });
    await flushNdjson();

    expect(collecting.promptUpdates).toHaveLength(1);
    expect(collecting.promptUpdates[0]?.update).toMatchObject({
      sessionUpdate: 'agent_thought_chunk',
      content: { type: 'text', text: 'hmm' },
    });
  });

  it('relays only `status` tool.progress updates as title-bearing tool_call_update', async () => {
    const sessionId = 'sess-progress';
    const turnId = 1;
    const toolCallId = 'tc-prog';
    const session = makeScriptedSession(sessionId, [
      {
        type: 'tool.call.started',
        sessionId,
        agentId: 'main',
        turnId,
        toolCallId,
        name: 'Bash',
        args: { cmd: 'pnpm test' },
      } as Event,
      {
        type: 'tool.progress',
        sessionId,
        agentId: 'main',
        turnId,
        toolCallId,
        update: { kind: 'stdout', text: 'should not stream' },
      } as Event,
      {
        type: 'tool.progress',
        sessionId,
        agentId: 'main',
        turnId,
        toolCallId,
        update: { kind: 'status', text: 'running test suite' },
      } as Event,
      { type: 'turn.ended', sessionId, agentId: 'main', turnId, reason: 'completed' } as Event,
    ]);
    const harness = {
      auth: { status: async () => AUTHED_STATUS },
      createSession: async () => session,
    } as unknown as KimiHarness;

    const { agentStream, clientStream } = makeInMemoryStreamPair();
    new AgentSideConnection((c) => new AcpServer(harness, c), agentStream);
    const collecting = new CollectingClient();
    const client = new ClientSideConnection(() => collecting, clientStream);

    await client.newSession({ cwd: '/tmp/x', mcpServers: [] });
    await client.prompt({ sessionId, prompt: [textBlock('go')] });
    await flushNdjson();

    // 1 start + 1 status (stdout is dropped) = 2 updates.
    expect(collecting.promptUpdates).toHaveLength(2);
    const second = collecting.promptUpdates[1]?.update as {
      sessionUpdate: string;
      title?: string;
    };
    expect(second.sessionUpdate).toBe('tool_call_update');
    expect(second.title).toBe('running test suite');
  });

  it('lazy-creates tool_call on the first delta and upgrades on tool.call.started (production event order)', async () => {
    // The agent-core actually emits `tool.call.delta` events DURING
    // the provider's args-streaming phase and only fires
    // `tool.call.started` afterwards. The adapter must therefore
    // lazy-create the wire `tool_call` from the first delta, otherwise
    // Zed sees `tool_call_update` notifications for an unknown id and
    // surfaces "Tool call not found" until the start eventually lands.
    // This test pins the production order delta → delta → started →
    // result → end.
    const sessionId = 'sess-tc-lazy';
    const turnId = 1;
    const toolCallId = 'tc-stream';
    const session = makeScriptedSession(sessionId, [
      {
        type: 'tool.call.delta',
        sessionId,
        agentId: 'main',
        turnId,
        toolCallId,
        name: 'Read',
        argumentsPart: '{"path":',
      } as Event,
      {
        type: 'tool.call.delta',
        sessionId,
        agentId: 'main',
        turnId,
        toolCallId,
        argumentsPart: '"a"}',
      } as Event,
      {
        type: 'tool.call.started',
        sessionId,
        agentId: 'main',
        turnId,
        toolCallId,
        name: 'Read',
        args: { path: 'a' },
        description: 'Reading a',
      } as Event,
      {
        type: 'tool.result',
        sessionId,
        agentId: 'main',
        turnId,
        toolCallId,
        output: 'file content',
        isError: false,
      } as Event,
      { type: 'turn.ended', sessionId, agentId: 'main', turnId, reason: 'completed' } as Event,
    ]);
    const harness = {
      auth: { status: async () => AUTHED_STATUS },
      createSession: async () => session,
    } as unknown as KimiHarness;

    const { agentStream, clientStream } = makeInMemoryStreamPair();
    new AgentSideConnection((c) => new AcpServer(harness, c), agentStream);
    const collecting = new CollectingClient();
    const client = new ClientSideConnection(() => collecting, clientStream);

    await client.newSession({ cwd: '/tmp/x', mcpServers: [] });
    const response = await client.prompt({ sessionId, prompt: [textBlock('go')] });
    expect(response.stopReason).toBe('end_turn');
    await flushNdjson();

    // delta(lazy-create) + delta(cumulative) + started(upgrade) + result
    expect(collecting.promptUpdates).toHaveLength(4);

    // 1) Lazy create: `tool_call` MUST land before any update, with
    // `name`-derived title and the first delta fragment as content.
    expect(collecting.promptUpdates[0]?.update).toMatchObject({
      sessionUpdate: 'tool_call',
      toolCallId: `${turnId}:${toolCallId}`,
      title: 'Read',
      kind: 'read',
      status: 'pending',
      content: [
        { type: 'content', content: { type: 'text', text: '{"path":' } },
      ],
    });

    // 2) Second delta: cumulative args replace content.
    expect(collecting.promptUpdates[1]?.update).toMatchObject({
      sessionUpdate: 'tool_call_update',
      toolCallId: `${turnId}:${toolCallId}`,
      status: 'in_progress',
      content: [
        { type: 'content', content: { type: 'text', text: '{"path":"a"}' } },
      ],
    });

    // 3) Start arrives after lazy-create: emitted as `tool_call_update`
    // carrying the canonical title (from `description`), `rawInput`,
    // and canonical stringified args. Status flips to `in_progress`.
    expect(collecting.promptUpdates[2]?.update).toMatchObject({
      sessionUpdate: 'tool_call_update',
      toolCallId: `${turnId}:${toolCallId}`,
      title: 'Reading a',
      kind: 'read',
      status: 'in_progress',
      rawInput: { path: 'a' },
      content: [
        {
          type: 'content',
          content: { type: 'text', text: JSON.stringify({ path: 'a' }) },
        },
      ],
    });

    // 4) Result: terminal update.
    expect(collecting.promptUpdates[3]?.update).toMatchObject({
      sessionUpdate: 'tool_call_update',
      toolCallId: `${turnId}:${toolCallId}`,
      status: 'completed',
    });
  });

  it('keeps the start-first path unchanged when no deltas precede tool.call.started', async () => {
    // Some providers (or the synthetic / replay paths) emit
    // `tool.call.started` without a preceding args stream. The adapter
    // must still send a `tool_call` CREATE in that case and NOT an
    // update — clients otherwise have no card to update.
    const sessionId = 'sess-tc-startfirst';
    const turnId = 1;
    const toolCallId = 'tc-start';
    const session = makeScriptedSession(sessionId, [
      {
        type: 'tool.call.started',
        sessionId,
        agentId: 'main',
        turnId,
        toolCallId,
        name: 'Read',
        args: { path: 'a' },
      } as Event,
      { type: 'turn.ended', sessionId, agentId: 'main', turnId, reason: 'completed' } as Event,
    ]);
    const harness = {
      auth: { status: async () => AUTHED_STATUS },
      createSession: async () => session,
    } as unknown as KimiHarness;

    const { agentStream, clientStream } = makeInMemoryStreamPair();
    new AgentSideConnection((c) => new AcpServer(harness, c), agentStream);
    const collecting = new CollectingClient();
    const client = new ClientSideConnection(() => collecting, clientStream);

    await client.newSession({ cwd: '/tmp/x', mcpServers: [] });
    await client.prompt({ sessionId, prompt: [textBlock('go')] });
    await flushNdjson();

    expect(collecting.promptUpdates).toHaveLength(1);
    expect(collecting.promptUpdates[0]?.update).toMatchObject({
      sessionUpdate: 'tool_call',
      toolCallId: `${turnId}:${toolCallId}`,
      title: 'Read',
      status: 'in_progress',
      rawInput: { path: 'a' },
    });
  });

  it('maps auth-coded session.prompt rejection to RequestError.authRequired', async () => {
    const { ErrorCodes } = await import('@moonshot-ai/kimi-code-sdk');
    const { RequestError } = await import('@agentclientprotocol/sdk');
    // session.prompt rejects synchronously with an auth-coded payload.
    const session: any = {
      id: 'sess-prompt-auth',
      prompt: async () => {
        // Simulate a thrown KimiError-like object with .code
        throw { code: ErrorCodes.AUTH_LOGIN_REQUIRED, message: 'login needed' };
      },
      onEvent: (_fn: (e: any) => void) => {
        // return unsub
        return () => {};
      },
      setApprovalHandler: (_fn: any) => {},
      setQuestionHandler: (_fn: any) => {},
    } as unknown as Session;
    const conn = {
      sessionUpdate: async (_n: unknown) => undefined,
    } as unknown as AgentSideConnection;
    const acpModule = await import('../src/session');
    const acp = new acpModule.AcpSession(conn, session);
    await expect(acp.prompt([{ type: 'text', text: 'hi' }])).rejects.toBeInstanceOf(RequestError);
  });


  it('setThinking updates state when session.setThinking is missing', async () => {
    // Minimal session stub: no setThinking implemented.
    const session: any = {
      id: 'sess-setthinking',
      // constructor expects optional setApprovalHandler / setQuestionHandler;
      // provide sane no-op implementations so the ctor doesn't throw.
      setApprovalHandler: (_fn: any) => {},
      setQuestionHandler: (_fn: any) => {},
      onEvent: (_fn: (e: any) => void) => {
        return () => {};
      },
    } as unknown as Session;
    const conn = {
      sessionUpdate: async (_n: unknown) => undefined,
    } as unknown as AgentSideConnection;
    const acp = new (await import('../src/session')).AcpSession(conn, session);
    // initial state default false
    expect(acp.currentThinkingEnabled).toBe(false);
    await acp.setThinking(true);
    // AcpSession should flip its internal toggle even though the Session
    // has no setThinking method (the SDK call is tolerant).
    expect(acp.currentThinkingEnabled).toBe(true);
    // Flip off: since we have no harness, currentModelAlwaysThinking() -> false,
    // so calling setThinking(false) should set it to false.
    await acp.setThinking(false);
    expect(acp.currentThinkingEnabled).toBe(false);
  });


  it('handleApproval returns rejected decision when requestPermission throws', async () => {
    let capturedHandler: ((req: unknown) => Promise<unknown>) | undefined;
    const session = {
      id: 'sess-approval-fail',
      setApprovalHandler: (fn: (req: unknown) => Promise<unknown>) => {
        capturedHandler = fn;
      },
      // satisfy constructor guard
      setQuestionHandler: (fn: (req: unknown) => Promise<unknown>) => {
        (session as any)._question = fn;
      },
      onEvent: (_fn: (e: any) => void) => {
        return () => {};
      },
    } as unknown as Session;
    const conn = {
      sessionUpdate: async (_n: unknown) => undefined,
      requestPermission: async (_p: unknown) => {
        throw new Error('rpc-failure');
      },
    } as unknown as AgentSideConnection;
    const recordedTelemetry: Array<{ event: string; props?: Record<string, unknown> }> = [];
    const track = (event: string, props?: Record<string, unknown>) => {
      recordedTelemetry.push({ event, props });
    };
    const acp = new AcpSession(conn, session, undefined, track);
    expect(typeof capturedHandler).toBe('function');
    // Minimal approval request; use a non-plan_review display to avoid the plan parsing path
    const req = {
      toolCallId: 't1',
      toolName: 'T',
      display: { kind: 'generic', title: 'Ask' },
    } as unknown as any;
    const res = await (capturedHandler as (r: unknown) => Promise<unknown>)(req);
    expect(res).toEqual({ decision: 'rejected' });
    // No telemetry for this kind of display (we didn't use plan_review)
    expect(recordedTelemetry).toHaveLength(0);
  });


  it('handleQuestion returns null for empty questions array', async () => {
    let capturedHandler: ((req: unknown) => Promise<unknown>) | undefined;
    const session = {
      id: 'sess-q-empty',
      // capture the installed question handler so the test can invoke it
      setQuestionHandler: (fn: (req: unknown) => Promise<unknown>) => {
        capturedHandler = fn;
      },
      setApprovalHandler: (fn: (req: unknown) => Promise<unknown>) => {
        // satisfy constructor guard without doing anything
        (session as any)._approval = fn;
      },
      onEvent: (_fn: (e: any) => void) => {
        return () => {};
      },
    } as unknown as Session;
    const conn = {
      sessionUpdate: async (_n: unknown) => undefined,
      requestPermission: async (_p: unknown) => {
        // should not be invoked for empty questions case
        throw new Error('should-not-be-called');
      },
    } as unknown as AgentSideConnection;
    const acp = new AcpSession(conn, session);
    // ensure handler was installed
    expect(typeof capturedHandler).toBe('function');
    // call with empty questions to exercise the early-return branch
    const result = await (capturedHandler as (r: unknown) => Promise<unknown>)({ questions: [] });
    expect(result).toBeNull();
  });


  it('prompt maps non-auth error to internal RequestError', async () => {
    // session.prompt throws a plain Error -> mapPromptError should convert it
    const session = {
      id: 'sess-err-map',
      prompt: async () => {
        throw new Error('boom');
      },
      cancel: async () => undefined,
      onEvent: (_fn: (e: any) => void) => {
        return () => {};
      },
      // make constructor guards happy
      setApprovalHandler: (fn: (req: unknown) => Promise<unknown>) => {
        // no-op store
        (session as any)._approval = fn;
      },
      setQuestionHandler: (fn: (req: unknown) => Promise<unknown>) => {
        (session as any)._question = fn;
      },
    } as unknown as Session;
    const conn = {
      sessionUpdate: async (_n: unknown) => undefined,
    } as unknown as AgentSideConnection;
    const acp = new AcpSession(conn, session);
    await expect(acp.prompt([textBlock('hello')])).rejects.toThrow('session prompt failed');
  });


  it('setModel with ,thinking suffix calls session.setModel and setThinking and updates state', async () => {
    const calls: string[] = [];
    const sessionStub = {
      id: 'sess-setmodel',
      // record the calls made by AcpSession
      setModel: async (id: string) => {
        calls.push(`setModel:${id}`);
      },
      setThinking: async (lvl: string) => {
        calls.push(`setThinking:${lvl}`);
      },
      // optional methods referenced by constructor guards
      setApprovalHandler: () => {},
      setQuestionHandler: () => {},
    } as unknown as Session;
  
    // minimal conn stub; emit is not relevant for this test
    const connStub = {
      sessionUpdate: async () => {},
    } as unknown as AgentSideConnection;
  
    // Construct AcpSession directly (no harness passed so emitConfigOptionUpdate is a no-op)
    const acp = new AcpSession(connStub as any, sessionStub as any, undefined, undefined, 'initial-base', undefined, false);
  
    // Call setModel with the legacy merged form
    await acp.setModel('newmodel,thinking');
  
    // The SDK should receive the base model (without ",thinking")
    expect(calls).toContain('setModel:newmodel');
    // The adapter should call the session.setThinking with the "on" level ('high')
    expect(calls).toContain('setThinking:high');
    // Adapter-side state updated
    expect(acp.currentModelId).toBe('newmodel');
    expect(acp.currentThinkingEnabled).toBe(true);
  });


  it('emits help and usage reports for built-in slash commands', async () => {
    const sessionId = 'sess-builtins';
    // A session stub that supplies the SDK methods used by the built-in handlers.
    const session = {
      id: sessionId,
      prompt: async () => {
        // Builtins are handled before calling session.prompt; nothing to do.
      },
      cancel: async () => undefined,
      onEvent: () => {
        return () => {};
      },
      setApprovalHandler: () => {},
      setQuestionHandler: () => {},
      getStatus: async () => ({
        model: 'mymodel',
        thinkingLevel: 'high',
        permission: 'manual',
        planMode: false,
        contextTokens: 1234,
        maxContextTokens: 8000,
        contextUsage: 0.123,
      }),
      getUsage: async () => ({
        total: { inputOther: 1, output: 2, inputCacheRead: 3, inputCacheCreation: 4 },
        currentTurn: { inputOther: 5, output: 6, inputCacheRead: 7, inputCacheCreation: 8 },
        byModel: { 'mymodel': { inputOther: 1, output: 2, inputCacheRead: 3, inputCacheCreation: 4 } },
      }),
      listMcpServers: async () => [
        { name: 'mcp1', status: 'ok', transport: 'http', toolCount: 2 },
      ],
      listBackgroundTasks: async () => [
        { taskId: 't1', status: 'running', description: 'desc', kind: 'process', command: 'echo hi' },
      ],
    } as unknown as Session;
    const harness = {
      auth: { status: async () => AUTHED_STATUS },
      createSession: async () => session,
    } as unknown as KimiHarness;
  
    const { agentStream, clientStream } = makeInMemoryStreamPair();
    new AgentSideConnection((c) => new AcpServer(harness, c), agentStream);
    const collecting = new CollectingClient();
    const client = new ClientSideConnection(() => collecting, clientStream);
  
    await client.newSession({ cwd: '/tmp/x', mcpServers: [] });
  
    // /help should produce an agent_message_chunk with the help text
    const respHelp = await client.prompt({ sessionId, prompt: [textBlock('/help')] });
    expect(respHelp.stopReason).toBe('end_turn');
    await flushNdjson();
    expect(collecting.promptUpdates.length).toBeGreaterThan(0);
    const first = collecting.promptUpdates[collecting.promptUpdates.length - 1];
    expect(first.update).toMatchObject({
      sessionUpdate: 'agent_message_chunk',
    });
    // Help text must include the header
    expect((first.update as any).content.text).toEqual(expect.stringContaining('Available ACP commands:'));
  
    // /usage should produce an agent_message_chunk with usage details
    const respUsage = await client.prompt({ sessionId, prompt: [textBlock('/usage')] });
    expect(respUsage.stopReason).toBe('end_turn');
    await flushNdjson();
    const last = collecting.promptUpdates[collecting.promptUpdates.length - 1];
    expect(last.update).toMatchObject({
      sessionUpdate: 'agent_message_chunk',
    });
    expect((last.update as any).content.text).toEqual(expect.stringContaining('Session usage:'));
  });

});
