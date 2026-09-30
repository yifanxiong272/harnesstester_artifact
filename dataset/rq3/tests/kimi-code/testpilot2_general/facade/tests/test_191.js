let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const ToolCallComponentProto = testpilot_subject.file_0003.ToolCallComponent.prototype;
    const MAX_CHARS = testpilot_subject.file_0003.MAX_LIVE_OUTPUT_CHARS;

    function makeComponent() {
        // Create an object that uses the prototype but doesn't run any constructor logic.
        const comp = Object.create(ToolCallComponentProto);

        // Provide the data structures the method expects.
        comp.subToolActivities = new Map();
        comp.ongoingSubCalls = new Map();

        // Spies / stubs for side-effect methods.
        comp._upsertCalls = [];
        comp.upsertSubToolActivity = function(id, name, args, phase, output) {
            comp._upsertCalls.push({ id, name, args, phase, output });
        };

        comp._rebuildCalled = 0;
        comp.rebuildContent = function() { comp._rebuildCalled++; };

        comp._notifyCalled = 0;
        comp.notifySnapshotChange = function() { comp._notifyCalled++; };

        comp.ui = {
            _renderCalled: 0,
            requestRender: function() { this._renderCalled++; }
        };

        return comp;
    }

    it('does nothing when text is empty', function() {
        const comp = makeComponent();
        // Add an activity just to ensure nothing happens even when maps are populated.
        comp.subToolActivities.set('t1', { name: 'N', args: {}, output: 'x', phase: 'ongoing' });

        // Call with empty text:
        ToolCallComponentProto.appendSubToolLiveOutput.call(comp, 't1', '');

        // No upsert, no rebuild, no notify, no render
        assert.strictEqual(comp._upsertCalls.length, 0);
        assert.strictEqual(comp._rebuildCalled, 0);
        assert.strictEqual(comp._notifyCalled, 0);
        assert.strictEqual(comp.ui._renderCalled, 0);
    });

    })