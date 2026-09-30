let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to create a bare instance that uses the real prototype but with stubbed dependencies.
    function makeStubInstance() {
        // Create an object whose prototype is the real ToolCallComponent prototype so setResult is available.
        let inst = Object.create(testpilot_subject.file_0003.ToolCallComponent.prototype);

        // Prepopulate properties that setResult will touch, and create spies/stubs for called methods.
        inst.progressLines = ['pre'];
        inst.liveOutput = 'some live output';
        inst.detachHintVisible = true;

        // Call trackers
        inst._called = [];

        inst.stopDetachHintTimer = function() { inst._called.push('stopDetachHintTimer'); };
        inst.finalizeSubagentElapsedIfNeeded = function() { inst._called.push('finalizeSubagentElapsedIfNeeded'); };
        inst.syncStreamingProgressTimer = function() { inst._called.push('syncStreamingProgressTimer'); };
        inst.syncSubagentElapsedTimer = function() { inst._called.push('syncSubagentElapsedTimer'); };

        // buildHeader should be called and its return value passed to headerText.setText
        inst.buildHeader = function() { inst._called.push('buildHeader'); return 'HEADER-VALUE'; };

        inst.headerText = {
            setText: function(text) {
                inst._called.push('headerText.setText:' + text);
            }
        };

        inst.rebuildBody = function() { inst._called.push('rebuildBody'); };
        inst.notifySnapshotChange = function() { inst._called.push('notifySnapshotChange'); };

        return inst;
    }

    it('setResult resets fields and calls expected lifecycle methods', function() {
        let inst = makeStubInstance();

        // Confirm preconditions
        assert.deepStrictEqual(inst.progressLines, ['pre']);
        assert.strictEqual(inst.liveOutput, 'some live output');
        assert.strictEqual(inst.detachHintVisible, true);

        let resultObj = { status: 'ok', code: 123 };
        inst.setResult(resultObj);

        // result should be set by reference
        assert.strictEqual(inst.result, resultObj);

        // fields should be reset
        assert.deepStrictEqual(inst.progressLines, []);
        assert.strictEqual(inst.liveOutput, '');
        assert.strictEqual(inst.detachHintVisible, false);

        // lifecycle methods should have been called (order will be checked in next test)
        let called = inst._called.slice();
        assert(called.indexOf('stopDetachHintTimer') !== -1, 'stopDetachHintTimer should be called');
        assert(called.indexOf('finalizeSubagentElapsedIfNeeded') !== -1, 'finalizeSubagentElapsedIfNeeded should be called');
        assert(called.indexOf('syncStreamingProgressTimer') !== -1, 'syncStreamingProgressTimer should be called');
        assert(called.indexOf('syncSubagentElapsedTimer') !== -1, 'syncSubagentElapsedTimer should be called');
        assert(called.indexOf('buildHeader') !== -1, 'buildHeader should be called');
        assert(called.some(s => s.indexOf('headerText.setText:') === 0), 'headerText.setText should be called');
        assert(called.indexOf('rebuildBody') !== -1, 'rebuildBody should be called');
        assert(called.indexOf('notifySnapshotChange') !== -1, 'notifySnapshotChange should be called');
    });

    })