let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const proto = testpilot_subject.file_0003.ToolCallComponent.prototype;

    it('does nothing when there is no ongoing sub-call for the given id', function() {
        // create a minimal component-like object to act as "this"
        const comp = {
            ongoingSubCalls: new Map(),
            finishedSubCalls: [],
            hiddenSubCallCount: 0,
            // spies
            upsertCalled: 0,
            rebuildCalled: 0,
            notifyCalled: 0,
            headerText: { setText: function() { this._called = true; this._args = arguments; } },
            ui: { requestRender: function() { this._renderCalled = true; } }
        };
        comp.upsertSubToolActivity = function() { this.upsertCalled++; };
        comp.rebuildContent = function() { this.rebuildCalled++; };
        comp.notifySnapshotChange = function() { this.notifyCalled++; };
        comp.buildHeader = function() { return 'header'; };

        // call with an id that doesn't exist
        const result = { tool_call_id: 'missing-id', output: 'x', is_error: false };
        // call the original method with our comp as this
        proto.finishSubToolCall.call(comp, result);

        // nothing should have changed
        assert.strictEqual(comp.ongoingSubCalls.size, 0);
        assert.strictEqual(comp.finishedSubCalls.length, 0);
        assert.strictEqual(comp.upsertCalled, 0);
        assert.strictEqual(comp.rebuildCalled, 0);
        assert.strictEqual(comp.notifyCalled, 0);
        // headerText.setText should not have been invoked
        assert.strictEqual(comp.headerText._called, undefined);
        // ui.requestRender should not have been invoked
        assert.strictEqual(comp.ui._renderCalled, undefined);
    });

    })