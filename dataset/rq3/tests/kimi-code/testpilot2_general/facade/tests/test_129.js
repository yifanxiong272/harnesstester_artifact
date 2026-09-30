let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Grab the function under test
    const syncFn = testpilot_subject.file_0003.ToolCallComponent.prototype.syncSubagentElapsedTimer;

    let origSetInterval, origClearInterval;

    beforeEach(function() {
        // Preserve originals
        origSetInterval = global.setInterval;
        origClearInterval = global.clearInterval;
    });

    afterEach(function() {
        // Restore originals
        global.setInterval = origSetInterval;
        global.clearInterval = origClearInterval;
    });

    it('does not start timer and calls stopSubagentElapsedTimer when shouldTick is false', function() {
        // Build a fake "this" object where shouldTick is false
        const calls = { stopped: 0 };
        const self = {
            // phase not in queued/spawning/running
            getDerivedSubagentPhase: () => 'finished',
            isSingleSubagentView: () => false, // ensures shouldTick false
            subagentStartedAtMs: 1234,
            stopSubagentElapsedTimer: function() { calls.stopped++; },
            // ensure no accidental timer use
            ui: {},
            subagentElapsedTimer: undefined
        };

        // Call the method
        syncFn.apply(self);

        // Because shouldTick is false, stopSubagentElapsedTimer should have been invoked once
        assert.strictEqual(calls.stopped, 1);
        // No timer should have been created
        assert.strictEqual(self.subagentElapsedTimer, undefined);
    });

    })