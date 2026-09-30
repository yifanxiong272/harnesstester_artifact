let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('appendSubToolCall should add new sub call, call lifecycle methods and request render when ui present', function() {
        const ToolCallComponent = testpilot_subject.file_0003.ToolCallComponent;
        // Create a plain object whose prototype is the component prototype, so we can set properties freely
        const comp = Object.create(ToolCallComponent.prototype);

        // Prepare required properties the method expects
        comp.ongoingSubCalls = new Map();

        let upsertCalls = [];
        comp.upsertSubToolActivity = function(id, name, args, state) {
            upsertCalls.push({ id, name, args, state });
        };

        comp.subagentPhase = undefined; // should transition to "running"
        comp.buildHeader = function() { return "HEADER-VALUE"; };

        let headerSetTextArg = undefined;
        comp.headerText = {
            setText: function(txt) { headerSetTextArg = txt; }
        };

        let rebuildCount = 0;
        comp.rebuildContent = function() { rebuildCount++; };

        let notifyCount = 0;
        comp.notifySnapshotChange = function() { notifyCount++; };

        let renderRequested = 0;
        comp.ui = {
            requestRender: function() { renderRequested++; }
        };

        // Call under test
        const call = { id: 'c1', name: 'toolA', args: { a: 1 } };
        comp.appendSubToolCall(call);

        // Assertions
        const stored = comp.ongoingSubCalls.get('c1');
        assert.deepStrictEqual(stored, { name: 'toolA', args: { a: 1 } }, 'ongoingSubCalls entry should match name and args');

        assert.strictEqual(upsertCalls.length, 1, 'upsertSubToolActivity should have been called once');
        assert.deepStrictEqual(upsertCalls[0], { id: 'c1', name: 'toolA', args: { a: 1 }, state: 'ongoing' });

        assert.strictEqual(comp.subagentPhase, 'running', 'subagentPhase should transition to running when undefined');

        assert.strictEqual(headerSetTextArg, 'HEADER-VALUE', 'headerText.setText should be called with buildHeader value');

        assert.strictEqual(rebuildCount, 1, 'rebuildContent should be called once');
        assert.strictEqual(notifyCount, 1, 'notifySnapshotChange should be called once');

        assert.strictEqual(renderRequested, 1, 'ui.requestRender should be called once when ui exists');
    });

    })