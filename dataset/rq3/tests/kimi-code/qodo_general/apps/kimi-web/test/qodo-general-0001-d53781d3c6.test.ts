import { computed, ref } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AppSession } from '../src/api/types';
import { createInitialState } from '../src/api/daemon/eventReducer';
import { useWorkspaceState, type UseWorkspaceStateDeps } from '../src/composables/client/useWorkspaceState';
import type { ExtendedState } from '../src/composables/useKimiWebClient';

const apiMock = vi.hoisted(() => ({
  abortPrompt: vi.fn(),
  abortSession: vi.fn(),
}));

vi.mock('../src/api', () => ({
  getKimiWebApi: () => apiMock,
}));

function createSession(): AppSession {
  return {
    id: 'sess_1',
    title: 'Session',
    createdAt: '2026-01-01T00:00:00.000Z',
    updatedAt: '2026-01-01T00:00:00.000Z',
    status: 'running',
    archived: false,
    currentPromptId: 'prompt_live',
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

function createState(): ExtendedState {
  return {
    ...createInitialState(),
    sessions: [createSession()],
    activeSessionId: 'sess_1',
    connected: true,
    serverVersion: '',
    workspaceName: 'kimi-web',
    connection: 'connected',
    permission: 'manual',
    thinking: 'high',
    planMode: false,
    swarmMode: false,
    goalMode: false,
    loading: false,
    sessionLoading: false,
    queuedBySession: {},
    gitStatusBySession: {},
    promptIdBySession: { sess_1: 'prompt_stale' },
    sendingBySession: {},
    unreadBySession: {},
    authReady: true,
    defaultModel: null,
    managedProviderStatus: null,
    workspaces: [],
    activeWorkspaceId: null,
    fsHome: null,
    recentRoots: [],
    hiddenWorkspaceRoots: [],
    availableOpenInApps: [],
    config: null,
    sideChatMessagesByAgent: {},
    sideChatSendingByAgent: {},
    sideChatUserMessageIdsBySession: {},
    messagesLoadingMoreBySession: {},
    messagesHasMoreBySession: {},
    messagesLoadMoreErrorBySession: {},
  };
}

function createDeps(): UseWorkspaceStateDeps {
  return {
    taskPoller: {},
    sideChat: {},
    modelProvider: {},
    pushOperationFailure: vi.fn(),
    activity: computed(() => 'running'),
    inFlightPromptSessions: new Set(),
    sessionsKnownEmpty: new Set(),
    setSessions: vi.fn(),
    updateSession: vi.fn(),
    upsertSessionFront: vi.fn(),
    appendSession: vi.fn(),
    forgetSession: vi.fn(),
    setActiveSessionId: vi.fn(),
    updateSessionMessages: vi.fn(),
    nextOptimisticMsgId: () => 'msg_opt_1',
    getEventConn: () => null,
    syncSessionFromSnapshot: vi.fn(),
    subscribeToSessionEvents: vi.fn(),
    hasLoadedMessages: vi.fn(),
    refreshSessionStatus: vi.fn(),
    persistSessionProfile: vi.fn(),
    mergedWorkspaces: computed(() => []),
    workspacesView: computed(() => []),
    status: computed(() => ({})),
    workspaceIdForSession: vi.fn(),
    savePermissionToStorage: vi.fn(),
    savePlanModeToStorage: vi.fn(),
    saveSwarmModeToStorage: vi.fn(),
    saveGoalModeToStorage: vi.fn(),
    saveUnread: vi.fn(),
    saveActiveWorkspaceToStorage: vi.fn(),
    saveHiddenWorkspacesToStorage: vi.fn(),
    goalErrorMessage: vi.fn(),
    basename: (path: string) => path.split('/').at(-1) ?? path,
    resetFastMoon: vi.fn(),
    initialized: ref(true),
    selectedDiffPath: ref(null),
    fileDiffLines: ref([]),
    fileDiffLoading: ref(false),
  } as unknown as UseWorkspaceStateDeps;
}

describe('useWorkspaceState — abortCurrentPrompt', () => {
  beforeEach(() => {
    apiMock.abortPrompt.mockReset();
    apiMock.abortSession.mockReset();
  });

  it('falls back to session abort when the cached prompt id is already completed', async () => {
    apiMock.abortPrompt.mockResolvedValue({ aborted: false });
    apiMock.abortSession.mockResolvedValue({ aborted: true });
    const state = createState();
    const workspace = useWorkspaceState(state, createDeps());

    await workspace.abortCurrentPrompt();

    expect(apiMock.abortPrompt).toHaveBeenCalledWith('sess_1', 'prompt_stale');
    expect(apiMock.abortSession).toHaveBeenCalledWith('sess_1');
    expect(state.promptIdBySession).toEqual({});
  });

  it('does not fall back when prompt abort succeeds', async () => {
    apiMock.abortPrompt.mockResolvedValue({ aborted: true });
    const workspace = useWorkspaceState(createState(), createDeps());

    await workspace.abortCurrentPrompt();

    expect(apiMock.abortPrompt).toHaveBeenCalledWith('sess_1', 'prompt_stale');
    expect(apiMock.abortSession).not.toHaveBeenCalled();
  });

  it('getFileDownloadUrl and resolveImageUrl cover pass-through and conversion branches', async () => {
    apiMock.getFileDownloadUrl = vi.fn();
    apiMock.readFile = vi.fn();
    apiMock.getFileDownloadUrl.mockReturnValue('http://download/file');
    const state = createState();
    const deps = createDeps();
    const workspace = useWorkspaceState(state, deps);
    // getFileDownloadUrl returns the API-provided URL when active session exists
    const url = workspace.getFileDownloadUrl('/some/path');
    expect(url).toBe('http://download/file');
    expect(apiMock.getFileDownloadUrl).toHaveBeenCalledWith('sess_1', '/some/path');
    // resolveImageUrl: pass-through for external URLs
    expect(await workspace.resolveImageUrl('https://host/image.png')).toBe('https://host/image.png');
    expect(await workspace.resolveImageUrl('data:image/png;base64,AAA')).toBe('data:image/png;base64,AAA');
    // successful readFile -> data: URL conversion (absolute path inside cwd)
    apiMock.readFile.mockResolvedValueOnce({
      path: 'img.png',
      content: 'BASE64DATA',
      encoding: 'base64',
      mime: 'image/png',
      languageId: undefined,
      isBinary: true,
      size: 123,
      lineCount: undefined,
      truncated: false,
    });
    const converted = await workspace.resolveImageUrl('/workspace/img.png');
    expect(converted).toBe('data:image/png;base64,BASE64DATA');
    // truncated or non-binary read falls back to original src
    apiMock.readFile.mockResolvedValueOnce({
      path: 'img.png',
      content: 'XXX',
      encoding: 'base64',
      mime: 'image/png',
      languageId: undefined,
      isBinary: false,
      size: 0,
      lineCount: undefined,
      truncated: false,
    });
    const fallback = await workspace.resolveImageUrl('/workspace/img.png');
    expect(fallback).toBe('/workspace/img.png');
    // absolute path outside cwd -> passthrough
    expect(await workspace.resolveImageUrl('/otherroot/img.png')).toBe('/otherroot/img.png');
    // no active session -> passthrough
    const state2 = createState();
    state2.activeSessionId = undefined as unknown as string;
    const deps2 = createDeps();
    const workspace2 = useWorkspaceState(state2, deps2);
    expect(await workspace2.resolveImageUrl('/workspace/img.png')).toBe('/workspace/img.png');
  });


  it('loadFileDiff success and error paths and clearFileDiff resets state', async () => {
    // prepare API mocks (do not use vi.hoisted inside tests)
    apiMock.getFileDiff = vi.fn();
    // success case
    apiMock.getFileDiff.mockResolvedValueOnce({
      diff: '--- a/file.txt\n+++ b/file.txt\n@@ -1 +1 @@\n-foo\n+bar\n',
    });
    const state1 = createState();
    const deps1 = createDeps();
    const workspace1 = useWorkspaceState(state1, deps1);
    // call loadFileDiff (should parse and populate fileDiffLines)
    await workspace1.loadFileDiff('file.txt');
    expect(deps1.selectedDiffPath.value).toBe('file.txt');
    expect(Array.isArray(deps1.fileDiffLines.value)).toBe(true);
    expect(deps1.fileDiffLines.value.length).toBeGreaterThan(0);
    expect(deps1.fileDiffLoading.value).toBe(false);
    // error case: rejected API should leave fileDiffLines empty and log a warning
    apiMock.getFileDiff.mockRejectedValueOnce(new Error('no diff'));
    const state2 = createState();
    const deps2 = createDeps();
    const workspace2 = useWorkspaceState(state2, deps2);
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    await workspace2.loadFileDiff('other.txt');
    expect(deps2.selectedDiffPath.value).toBe('other.txt');
    expect(deps2.fileDiffLines.value).toEqual([]);
    expect(deps2.fileDiffLoading.value).toBe(false);
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
    // clearFileDiff resets all
    deps2.selectedDiffPath.value = 'x';
    deps2.fileDiffLines.value = [{ line: 'x' } as any];
    deps2.fileDiffLoading.value = true;
    workspace2.clearFileDiff();
    expect(deps2.selectedDiffPath.value).toBeNull();
    expect(deps2.fileDiffLines.value).toEqual([]);
    expect(deps2.fileDiffLoading.value).toBe(false);
  });


  it('loadOlderMessages loads page and updates flags, and handles errors by setting error flag and calling pushOperationFailure', async () => {
    // success case
    apiMock.listMessages = vi.fn().mockResolvedValue({ items: [{ id: 'm_old' }], hasMore: false });
  
    const state = createState();
    // seed existing messages (newest last in chronological order)
    state.messagesBySession['sess_1'] = [
      { id: 'm_new', sessionId: 'sess_1', role: 'assistant', content: [], createdAt: new Date().toISOString(), metadata: {} } as any,
    ];
    const deps = createDeps();
    const ws = useWorkspaceState(state, deps);
    await ws.loadOlderMessages('sess_1');
  
    expect(apiMock.listMessages).toHaveBeenCalledWith('sess_1', { beforeId: 'm_new', pageSize: 50 });
    expect(deps.updateSessionMessages).toHaveBeenCalled();
    expect(state.messagesHasMoreBySession['sess_1']).toBe(false);
    expect(state.messagesLoadingMoreBySession['sess_1']).toBe(false);
  
    // error case
    apiMock.listMessages.mockRejectedValue(new Error('boom'));
    const state2 = createState();
    state2.messagesBySession['sess_1'] = [
      { id: 'm_new', sessionId: 'sess_1', role: 'assistant', content: [], createdAt: new Date().toISOString(), metadata: {} } as any,
    ];
    const deps2 = createDeps();
    deps2.pushOperationFailure = vi.fn();
    const ws2 = useWorkspaceState(state2, deps2);
    await ws2.loadOlderMessages('sess_1');
  
    expect(state2.messagesLoadMoreErrorBySession['sess_1']).toBe(true);
    expect(deps2.pushOperationFailure).toHaveBeenCalledWith('loadOlderMessages', expect.anything(), { sessionId: 'sess_1' });
    expect(state2.messagesLoadingMoreBySession['sess_1']).toBe(false);
  });


  it('getFileDownloadUrl and resolveImageUrl cover pass-through and conversion branches', async () => {
    // Provide the download URL and readFile implementations
    apiMock.getFileDownloadUrl = vi.fn().mockReturnValue('http://download/file');
    apiMock.readFile = vi.fn();
  
    const state = createState();
    const deps = createDeps();
    const workspace = useWorkspaceState(state, deps);
  
    // getFileDownloadUrl returns API-provided URL
    const url = workspace.getFileDownloadUrl('/some/path');
    expect(url).toBe('http://download/file');
    expect(apiMock.getFileDownloadUrl).toHaveBeenCalledWith('sess_1', '/some/path');
  
    // resolveImageUrl: pass-through for external URLs
    expect(await workspace.resolveImageUrl('https://host/image.png')).toBe('https://host/image.png');
    expect(await workspace.resolveImageUrl('data:image/png;base64,AAA')).toBe('data:image/png;base64,AAA');
  
    // successful readFile -> data: URL conversion (absolute path inside cwd)
    apiMock.readFile.mockResolvedValue({
      path: 'img.png',
      content: 'BASE64DATA',
      encoding: 'base64',
      mime: 'image/png',
      languageId: undefined,
      isBinary: true,
      size: 123,
      lineCount: undefined,
      truncated: false,
    });
    const converted = await workspace.resolveImageUrl('/workspace/img.png');
    expect(converted).toBe('data:image/png;base64,BASE64DATA');
  
    // non-binary (or other invalid) read -> fallback to original src
    apiMock.readFile.mockResolvedValue({
      path: 'img.png',
      content: 'XXX',
      encoding: 'base64',
      mime: 'image/png',
      languageId: undefined,
      isBinary: false,
      size: 0,
      lineCount: undefined,
      truncated: false,
    });
    const fallback = await workspace.resolveImageUrl('/workspace/img.png');
    expect(fallback).toBe('/workspace/img.png');
  
    // no active session -> passthrough unchanged
    const state2 = createState();
    // clear active session
    state2.activeSessionId = undefined as unknown as string;
    const deps2 = createDeps();
    const workspace2 = useWorkspaceState(state2, deps2);
    expect(await workspace2.resolveImageUrl('/workspace/img.png')).toBe('/workspace/img.png');
  });


  it('uploadImage returns metadata on success and null on failure with error push', async () => {
    const blob = new Blob(['abc'], { type: 'image/png' });
    // success case
    apiMock.uploadFile = vi.fn().mockResolvedValue({ id: 'file_1', name: 'img.png', mediaType: 'image/png' });
    const state1 = createState();
    const deps1 = createDeps();
    const workspace1 = useWorkspaceState(state1, deps1);
    const res = await workspace1.uploadImage(blob, 'img.png');
    expect(res).toEqual({ fileId: 'file_1', name: 'img.png', mediaType: 'image/png' });
  
    // failure case
    apiMock.uploadFile.mockRejectedValue(new Error('upload failed'));
    const state2 = createState();
    const deps2 = createDeps();
    deps2.pushOperationFailure = vi.fn();
    const workspace2 = useWorkspaceState(state2, deps2);
    const res2 = await workspace2.uploadImage(blob, 'img.png');
    expect(res2).toBeNull();
    expect(deps2.pushOperationFailure).toHaveBeenCalledWith('uploadImage', expect.anything());
  });


  it('enqueue adds to queue and unqueue removes by index or no-ops on invalid index', () => {
    const state = createState();
    const deps = createDeps();
    const workspace = useWorkspaceState(state, deps);
  
    // ensure activeSessionId exists in state (createState does this)
    expect(state.activeSessionId).toBe('sess_1');
  
    workspace.enqueue('first');
    workspace.enqueue('second', [{ kind: 'image', fileId: 'f1' }]);
    const queued = state.queuedBySession['sess_1'];
    expect(queued).toHaveLength(2);
    expect(queued[0].text).toBe('first');
    expect(queued[1].attachments?.[0].fileId).toBe('f1');
  
    // remove first entry
    workspace.unqueue(0);
    const after = state.queuedBySession['sess_1'];
    expect(after).toHaveLength(1);
    expect(after[0].text).toBe('second');
  
    // out-of-range does nothing
    workspace.unqueue(5);
    expect(state.queuedBySession['sess_1']).toHaveLength(1);
  });

});
