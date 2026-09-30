let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const onSubagentStarted = testpilot_subject.file_0003.ToolCallComponent.prototype.onSubagentStarted;

    it('sets agent id/name, transitions phase to running when not runInBackground and calls lifecycle methods including ui.requestRender', function(done) {
        let meta = { agentId: 'agent-123', agentName: 'Agent Smith', runInBackground: false };

        // flags / recorders
        let syncCalled = false;
        let rebuildCalled = false;
        let notifyCalled = false;
        let headerTextReceived = null;
        let uiRequested = false;

        // fake instance (no constructor needed)
        let inst = {
            // initial phase undefined
            subagentPhase: undefined,
            // stubs
            syncSubagentElapsedTimer: function() { syncCalled = true; },
            rebuildContent: function() { rebuildCalled = true; },
            notifySnapshotChange: function() { notifyCalled = true; },
            buildHeader: function() { return 'HEADER: ' + (this.subagentAgentName || 'unknown'); },
            headerText: {
                setText: function(txt) { headerTextReceived = txt; }
            },
            ui: {
                requestRender: function() { uiRequested = true; }
            }
        };

        // invoke
        onSubagentStarted.call(inst, meta);

        // assertions
        assert.strictEqual(inst.subagentAgentId, meta.agentId, 'agentId should be set');
        assert.strictEqual(inst.subagentAgentName, meta.agentName, 'agentName should be set');
        assert.strictEqual(inst.subagentPhase, 'running', 'phase should transition to running');
        assert.strictEqual(syncCalled, true, 'syncSubagentElapsedTimer should be called');
        assert.strictEqual(rebuildCalled, true, 'rebuildContent should be called');
        assert.strictEqual(notifyCalled, true, 'notifySnapshotChange should be called');
        assert.strictEqual(headerTextReceived, 'HEADER: ' + meta.agentName, 'headerText.setText should be called with buildHeader result');
        assert.strictEqual(uiRequested, true, 'ui.requestRender should be called when ui exists');

        done();
    });

    })