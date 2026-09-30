let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('should set subagent meta and call expected side-effect methods', function(done) {
        // Create a lightweight instance using the prototype so we don't need full constructor behavior.
        let proto = testpilot_subject.file_0003.ToolCallComponent.prototype;
        let comp = Object.create(proto);

        // initial values
        comp.subagentAgentId = undefined;
        comp.subagentAgentName = undefined;

        // spies / stubs
        let headerTextArg = null;
        let headerTextCalls = 0;
        comp.headerText = {
            setText: function(arg) { headerTextArg = arg; headerTextCalls++; }
        };

        // buildHeader should reflect the new values so we can assert the passed text
        comp.buildHeader = function() {
            return 'HEADER:' + this.subagentAgentId + '/' + this.subagentAgentName;
        };

        let rebuildCalled = 0;
        comp.rebuildContent = function() { rebuildCalled++; };

        let notifyCalled = 0;
        comp.notifySnapshotChange = function() { notifyCalled++; };

        let uiCalled = 0;
        comp.ui = { requestRender: function() { uiCalled++; } };

        // Call with new values
        comp.setSubagentMeta('agent-1', 'Alice');

        // Assertions
        assert.strictEqual(comp.subagentAgentId, 'agent-1', 'subagentAgentId should be set');
        assert.strictEqual(comp.subagentAgentName, 'Alice', 'subagentAgentName should be set');

        assert.strictEqual(headerTextCalls, 1, 'headerText.setText should be called once');
        assert.strictEqual(headerTextArg, 'HEADER:agent-1/Alice', 'header text should be built from new values');

        assert.strictEqual(rebuildCalled, 1, 'rebuildContent should be called once');
        assert.strictEqual(notifyCalled, 1, 'notifySnapshotChange should be called once');
        assert.strictEqual(uiCalled, 1, 'ui.requestRender should be called once');

        done();
    });

    })