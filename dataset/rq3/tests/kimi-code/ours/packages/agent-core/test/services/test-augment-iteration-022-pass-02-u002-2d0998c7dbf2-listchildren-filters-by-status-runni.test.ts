import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  type AgentContextData,
  type CoreRPC,
  type ContextMessage,
  type CreateSessionPayload,
  Emitter,
  type ForkSessionPayload,
  IInstantiationService,
  type RenameSessionPayload,
  type ResumeSessionResult,
  type SessionMeta,
  type SessionSummary,
  type UpdateSessionMetadataPayload,
} from '../../src';
import { TestInstantiationService } from '../../src/di/test';
import { emptySessionUsage, type Event, type Session } from '@moonshot-ai/protocol';

import {
  IApprovalService,
  type IAuthSummaryService,
  type ICoreProcessService,
  type IEventService,
  IPromptService,
  IQuestionService,
  type ISessionService,
  PromptService,
  SessionNotFoundError,
  SessionUndoUnavailableError,
  SessionService,
  toProtocolSession,
} from '../../src/services';

type WithSessionId<T> = T & { readonly sessionId: string };

interface FakeBridgeState {
  sessions: SessionSummary[];
  createPayloads: CreateSessionPayload[];
  metas: Map<string, SessionMeta>;
  archivedIds: string[];
  closedIds: string[];
  renamedTitles: Map<string, string>;
  metadataPatches: Map<string, UpdateSessionMetadataPayload['metadata']>;
  forkPayloads: Array<WithSessionId<Omit<ForkSessionPayload, 'sessionId'>>>;
  compactions: Array<{ sessionId: string; agentId: string; instruction?: string }>;
  undoPayloads: Array<{ sessionId: string; agentId: string; count: number }>;
  resumedIds: string[];
  contexts: Map<string, AgentContextData>;
  postUndoContexts: Map<string, AgentContextData>;
}

function makeFakeBridge(state: FakeBridgeState): ICoreProcessService {
  const rpc: Partial<CoreRPC> = {
    createSession: vi
      .fn()
      .mockImplementation(async (payload: CreateSessionPayload): Promise<SessionSummary> => {
        state.createPayloads.push(payload);
        const id = payload.id ?? `sess_${state.sessions.length + 1}`;
        const created: SessionSummary = {
          id,
          workDir: payload.workDir,
          sessionDir: `/tmp/sessions/${id}`,
          createdAt: 1_000_000 + state.sessions.length * 1_000,
          updatedAt: 1_000_000 + state.sessions.length * 1_000,
          metadata: payload.metadata,
          title: undefined,
        };
        state.sessions.push(created);
        return created;
      }),
    listSessions: vi
      .fn()
      .mockImplementation(
        async (
          input?: { workDir?: string },
        ): Promise<readonly SessionSummary[]> => {
          if (input?.workDir !== undefined) {
            return state.sessions.filter((s) => s.workDir === input.workDir);
          }
          return state.sessions;
        },
      ),
    forkSession: vi
      .fn()
      .mockImplementation(async (payload: ForkSessionPayload): Promise<ResumeSessionResult> => {
        const source = state.sessions.find((s) => s.id === payload.sessionId);
        if (source === undefined) {
          throw new Error(`missing source ${payload.sessionId}`);
        }
        state.forkPayloads.push({
          sessionId: payload.sessionId,
          id: payload.id,
          title: payload.title,
          metadata: payload.metadata,
        });
        const id = payload.id ?? `sess_fork_${state.sessions.length + 1}`;
        const created: SessionSummary = {
          id,
          workDir: source.workDir,
          sessionDir: `/tmp/sessions/${id}`,
          createdAt: 2_000_000 + state.sessions.length * 1_000,
          updatedAt: 2_000_000 + state.sessions.length * 1_000,
          metadata: {
            ...source.metadata,
            ...payload.metadata,
          },
          title: payload.title,
        };
        state.sessions.push(created);
        const sourceMeta = state.metas.get(source.id);
        const sessionMetadata: SessionMeta = {
          title: payload.title ?? `Fork: ${source.title ?? source.id}`,
          createdAt: new Date(0).toISOString(),
          updatedAt: new Date(0).toISOString(),
          isCustomTitle: payload.title !== undefined,
          agents: {},
          custom: {
            ...sourceMeta?.custom,
            ...payload.metadata,
          },
          forkedFrom: source.id,
        };
        state.metas.set(id, sessionMetadata);
        return {
          ...created,
          sessionMetadata,
          agents: {},
        };
      }),
    archiveSession: vi.fn().mockImplementation(async ({ sessionId }: { sessionId: string }) => {
      state.archivedIds.push(sessionId);
    }),
    renameSession: vi
      .fn()
      .mockImplementation(async (payload: WithSessionId<RenameSessionPayload>) => {
        state.renamedTitles.set(payload.sessionId, payload.title);
        const existing = state.metas.get(payload.sessionId);
        if (existing !== undefined) {
          state.metas.set(payload.sessionId, { ...existing, title: payload.title });
        } else {
          state.metas.set(payload.sessionId, {
            title: payload.title,
            createdAt: new Date(0).toISOString(),
            updatedAt: new Date(0).toISOString(),
            isCustomTitle: true,
            agents: {},
            custom: {},
          });
        }
      }),
    updateSessionMetadata: vi
      .fn()
      .mockImplementation(
        async (payload: WithSessionId<UpdateSessionMetadataPayload>) => {
          state.metadataPatches.set(payload.sessionId, payload.metadata);
        },
      ),
    getSessionMetadata: vi
      .fn()
      .mockImplementation(async ({ sessionId }: { sessionId: string }): Promise<SessionMeta> => {
        const found = state.metas.get(sessionId);
        if (found === undefined) {
          throw new Error(`no metadata for ${sessionId}`);
        }
        return found;
      }),
    beginCompaction: vi
      .fn()
      .mockImplementation(async (payload: { sessionId: string; agentId: string; instruction?: string }) => {
        state.compactions.push(payload);
      }),
    resumeSession: vi.fn().mockImplementation(async ({ sessionId }: { sessionId: string }) => {
      state.resumedIds.push(sessionId);
      const found = state.sessions.find((session) => session.id === sessionId);
      if (found === undefined) throw new Error(`missing session ${sessionId}`);
      return found as ResumeSessionResult;
    }),
    undoHistory: vi
      .fn()
      .mockImplementation(async (payload: { sessionId: string; agentId: string; count: number }) => {
        state.undoPayloads.push(payload);
        const next = state.postUndoContexts.get(payload.sessionId);
        if (next !== undefined) {
          state.contexts.set(payload.sessionId, next);
        }
      }),
    getContext: vi
      .fn()
      .mockImplementation(async ({ sessionId }: { sessionId: string }): Promise<AgentContextData> => {
        return state.contexts.get(sessionId) ?? { history: [], tokenCount: 0 };
      }),
    getConfig: vi.fn().mockResolvedValue({
      modelAlias: 'kimi-k2',
      thinkingLevel: 'auto',
      modelCapabilities: { max_context_tokens: 100 },
    }),
    getPermission: vi.fn().mockResolvedValue({ mode: 'manual' }),
    getPlan: vi.fn().mockResolvedValue(null),
  };
  return {
    rpc: rpc as CoreRPC,
    ready: async () => undefined,
    dispose: () => undefined,
    _serviceBrand: undefined,
  };
}

function freshState(): FakeBridgeState {
  return {
    sessions: [],
    createPayloads: [],
    metas: new Map(),
    archivedIds: [],
    closedIds: [],
    renamedTitles: new Map(),
    metadataPatches: new Map(),
    forkPayloads: [],
    compactions: [],
    undoPayloads: [],
    resumedIds: [],
    contexts: new Map(),
    postUndoContexts: new Map(),
  };
}

function textMessage(
  role: ContextMessage['role'],
  text: string,
  origin?: ContextMessage['origin'],
): ContextMessage {
  return {
    role,
    content: [{ type: 'text', text }],
    toolCalls: [],
    origin,
  };
}

let state: FakeBridgeState;
let svc: SessionService;
let promptStub: ReturnType<typeof makePromptServiceStub>;
let approvalStub: ReturnType<typeof makeApprovalServiceStub>;
let questionStub: ReturnType<typeof makeQuestionServiceStub>;
let eventBus: ReturnType<typeof makeEventServiceStub>;
let instantiation: TestInstantiationService;

function makeEventServiceStub(): {
  eventService: IEventService;
  events: unknown[];
} {
  const events: unknown[] = [];
  const emitter = new Emitter<never>();
  return {
    events,
    eventService: {
      _serviceBrand: undefined,
      publish: vi.fn((event: unknown) => {
        events.push(event);
        emitter.fire(event as never);
      }) as IEventService['publish'],
      onDidPublish: emitter.event as unknown as IEventService['onDidPublish'],
    },
  };
}

function makePromptServiceStub(): {
  promptService: IPromptService;
  calls: Array<{ sid: string; patch: Record<string, unknown>; source: string; promptId: string | undefined }>;
  activePromptIds: Map<string, string | undefined>;
} {
  const calls: Array<{ sid: string; patch: Record<string, unknown>; source: string; promptId: string | undefined }> = [];
  const activePromptIds = new Map<string, string | undefined>();
  const applyAgentState = vi
    .fn()
    .mockImplementation(async (sid: string, patch: Record<string, unknown>, source: string, promptId?: string) => {
      calls.push({ sid, patch, source, promptId });
    });
  const emitter = new Emitter<never>();
  const promptService: IPromptService = {
    _serviceBrand: undefined,
    list: vi.fn() as unknown as IPromptService['list'],
    submit: vi.fn() as unknown as IPromptService['submit'],
    startBtw: vi.fn().mockResolvedValue('btw_test') as unknown as IPromptService['startBtw'],
    steer: vi.fn() as unknown as IPromptService['steer'],
    abort: vi.fn() as unknown as IPromptService['abort'],
    abortBySession: vi.fn() as unknown as IPromptService['abortBySession'],
    getCurrentPromptId: vi.fn().mockImplementation((sid: string) => activePromptIds.get(sid)) as unknown as IPromptService['getCurrentPromptId'],
    applyAgentState,
    onDidComplete: emitter.event as unknown as IPromptService['onDidComplete'],
    onDidAbort: emitter.event as unknown as IPromptService['onDidAbort'],
    getAgentStateSnapshot: vi.fn().mockReturnValue(undefined) as unknown as IPromptService['getAgentStateSnapshot'],
  };
  return { promptService, calls, activePromptIds };
}

function makeApprovalServiceStub(): {
  approvalService: IApprovalService;
  pending: Map<string, unknown[]>;
} {
  const pending = new Map<string, unknown[]>();
  const approvalService: IApprovalService = {
    _serviceBrand: undefined,
    request: vi.fn() as unknown as IApprovalService['request'],
    resolve: vi.fn() as unknown as IApprovalService['resolve'],
    listPending: vi.fn().mockImplementation((sessionId: string) => {
      return (pending.get(sessionId) ?? []) as unknown as ReturnType<IApprovalService['listPending']>;
    }),
  } as unknown as IApprovalService;
  return { approvalService, pending };
}

function makeQuestionServiceStub(): {
  questionService: IQuestionService;
  pending: Map<string, unknown[]>;
} {
  const pending = new Map<string, unknown[]>();
  const questionService: IQuestionService = {
    _serviceBrand: undefined,
    request: vi.fn() as unknown as IQuestionService['request'],
    resolve: vi.fn() as unknown as IQuestionService['resolve'],
    dismiss: vi.fn() as unknown as IQuestionService['dismiss'],
    listPending: vi.fn().mockImplementation((sessionId: string) => {
      return (pending.get(sessionId) ?? []) as unknown as ReturnType<IQuestionService['listPending']>;
    }),
  } as unknown as IQuestionService;
  return { questionService, pending };
}

function makeTestInstantiation(stubs: {
  promptService: IPromptService;
  approvalService: IApprovalService;
  questionService: IQuestionService;
}): TestInstantiationService {
  const ix = new TestInstantiationService(undefined, true);
  ix.stub(IInstantiationService, ix);
  ix.stub(IPromptService, stubs.promptService);
  ix.stub(IApprovalService, stubs.approvalService);
  ix.stub(IQuestionService, stubs.questionService);
  return ix;
}

beforeEach(() => {
  state = freshState();
  promptStub = makePromptServiceStub();
  approvalStub = makeApprovalServiceStub();
  questionStub = makeQuestionServiceStub();
  eventBus = makeEventServiceStub();
  instantiation = makeTestInstantiation({
    promptService: promptStub.promptService,
    approvalService: approvalStub.approvalService,
    questionService: questionStub.questionService,
  });
  svc = new SessionService(
    makeFakeBridge(state),
    eventBus.eventService,
    instantiation,
    approvalStub.approvalService,
    questionStub.questionService,
  );
});

afterEach(() => {
  svc.dispose();
  instantiation.dispose();
});










describe('SessionService.undo', () => {


  __testAugmentVitest_16fbd6ce41c1.it("listChildren_filters_by_status_running_round_022_pass_02", async () => {
    // Create parent + children
    const parent = await svc.create({ metadata: { cwd: '/tmp/parent-filter' }, title: 'Parent' });
    const a = await svc.createChild(parent.id, { title: 'A' });
    const b = await svc.createChild(parent.id, { title: 'B' });
    const c = await svc.createChild(parent.id, { title: 'C' });

    // Make child B appear 'running' by starting a turn for it
    eventBus.eventService.publish({ type: 'turn.started', sessionId: b.id } as unknown as Event);

    // list children filtered by status running -> should return only B
    const page = await svc.listChildren(parent.id, { status: 'running' });
    __testAugmentVitest_16fbd6ce41c1.expect(page.items.map((s) => s.id)).toEqual([b.id]);
  });
});



import * as __testAugmentVitest_16fbd6ce41c1 from "vitest";

const __testAugmentLoadTarget_45c738e80166 = async () => {
  __testAugmentVitest_16fbd6ce41c1.vi.doUnmock("../../src/services/session/sessionService.js");
  __testAugmentVitest_16fbd6ce41c1.vi.resetModules();
  return import("../../src/services/session/sessionService.js");
};
