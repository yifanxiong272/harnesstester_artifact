let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('upsertWorkspacePreserveOrder should add new workspaces and update existing ones', function() {
        const rawState = {
            workspaces: [{ id: 'w1', root: '/r1', name: 'One' }],
            hiddenWorkspaceRoots: []
        };

        // minimal deps required for the functions we will call
        const calls = { saveHidden: [], saveActive: [], persistProfile: [], savePlan: [] };
        const deps = {
            // many deps are not used by the tested functions; provide minimal placeholders
            taskPoller: {},
            sideChat: {},
            modelProvider: { skillsBySession: { value: {} } },
            pushOperationFailure: () => {},
            activity: { value: 'idle' },
            inFlightPromptSessions: new Set(),
            sessionsKnownEmpty: new Set(),
            setSessions: () => {},
            updateSession: () => {},
            upsertSessionFront: () => {},
            appendSession: () => {},
            forgetSession: () => {},
            setActiveSessionId: (v) => { rawState.activeSessionId = v; },
            updateSessionMessages: () => {},
            nextOptimisticMsgId: () => 'temp_1',
            getEventConn: () => null,
            syncSessionFromSnapshot: () => Promise.resolve(),
            subscribeToSessionEvents: () => {},
            hasLoadedMessages: () => false,
            refreshSessionStatus: () => {},
            persistSessionProfile: (p) => { calls.persistProfile.push(p); },
            mergedWorkspaces: { value: [] },
            workspacesView: { value: [] },
            status: { value: {} },
            workspaceIdForSession: () => null,
            savePermissionToStorage: () => {},
            savePlanModeToStorage: (v) => { calls.savePlan.push(v); },
            saveSwarmModeToStorage: () => {},
            saveGoalModeToStorage: () => {},
            saveUnread: () => {},
            saveActiveWorkspaceToStorage: (v) => { calls.saveActive.push(v); },
            saveHiddenWorkspacesToStorage: (v) => { calls.saveHidden.push(v); },
            goalErrorMessage: () => '',
            basename: (p) => p,
            resetFastMoon: () => {},
            initialized: { value: false },
            selectedDiffPath: { value: null },
            fileDiffLines: { value: [] },
            fileDiffLoading: { value: false }
        };

        const api = testpilot_subject.file_0001.useWorkspaceState(rawState, deps);
        // add new workspace
        api.upsertWorkspacePreserveOrder({ id: 'w2', root: '/r2', name: 'Two' });
        assert.strictEqual(rawState.workspaces.length, 2, 'workspace should be added');
        assert.strictEqual(rawState.workspaces[0].id, 'w2', 'new workspace should be at front');

        // update existing workspace (w1)
        api.upsertWorkspacePreserveOrder({ id: 'w1', root: '/r1', name: 'OneUpdated' });
        // now w1 should be found and updated in the array (it was at index 1 originally)
        const found = rawState.workspaces.find(w => w.id === 'w1');
        assert.ok(found, 'w1 should still exist');
        assert.strictEqual(found.name, 'OneUpdated', 'w1 should be updated');
    });

    })