let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to create a lightweight instance without running any real constructor
    function createInstance() {
        // Create an object whose prototype is the real prototype so we can call the method under test
        let proto = testpilot_subject.file_0003.ToolCallComponent.prototype;
        let inst = Object.create(proto);
        return inst;
    }

    it('sets fields, calls helpers and requests render when runInBackground=true', function() {
        let inst = createInstance();

        // Spy-like collectors
        let calls = {};

        // Provide dependent methods/objects used by onSubagentSpawned
        inst.buildHeader = function() {
            calls.buildHeader = (calls.buildHeader || 0) + 1;
            return 'HDR-' + (this.subagentAgentName || 'unknown');
        };
        inst.headerText = {
            setText: function(text) {
                calls.setText = (calls.setText || 0) + 1;
                calls.setTextArg = text;
            }
        };
        inst.rebuildContent = function() { calls.rebuildContent = (calls.rebuildContent || 0) + 1; };
        inst.notifySnapshotChange = function() { calls.notifySnapshotChange = (calls.notifySnapshotChange || 0) + 1; };
        inst.syncSubagentElapsedTimer = function() { calls.syncSubagentElapsedTimer = (calls.syncSubagentElapsedTimer || 0) + 1; };
        inst.ui = { requestRender: function() { calls.requestRender = (calls.requestRender || 0) + 1; } };

        // Prepare meta and time window to assert start time
        let before = Date.now();
        let meta = { agentId: 'agent-123', agentName: 'subagentA', runInBackground: true };

        // Call the method under test
        inst.onSubagentSpawned(meta);

        // Assertions: properties
        assert.strictEqual(inst.subagentAgentId, meta.agentId, 'agentId should be set');
        assert.strictEqual(inst.subagentAgentName, meta.agentName, 'agentName should be set');
        assert.strictEqual(inst.subagentPhase, 'backgrounded', 'phase should be "backgrounded" for runInBackground=true');
        assert.strictEqual(inst.subagentEndedAtMs, undefined, 'endedAt should be undefined after spawn');
        assert.ok(typeof inst.subagentStartedAtMs === 'number', 'startedAt should be a number');
        assert.ok(inst.subagentStartedAtMs >= before && inst.subagentStartedAtMs <= Date.now(), 'startedAt should be set to a recent timestamp');

        // Assertions: helper calls
        assert.strictEqual(calls.syncSubagentElapsedTimer, 1, 'syncSubagentElapsedTimer should be called once');
        assert.strictEqual(calls.buildHeader, 1, 'buildHeader should be called once');
        assert.strictEqual(calls.setText, 1, 'headerText.setText should be called once');
        assert.strictEqual(calls.setTextArg, 'HDR-' + meta.agentName, 'headerText.setText should be called with buildHeader result');
        assert.strictEqual(calls.rebuildContent, 1, 'rebuildContent should be called once');
        assert.strictEqual(calls.notifySnapshotChange, 1, 'notifySnapshotChange should be called once');
        assert.strictEqual(calls.requestRender, 1, 'ui.requestRender should be called once');
    });

    })