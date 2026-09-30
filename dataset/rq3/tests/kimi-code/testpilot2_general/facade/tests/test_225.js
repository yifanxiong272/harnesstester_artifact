let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0003.ToolCallComponent.prototype.hasSubagentState', function() {
    // grab the function under test (call it with a crafted `this` object)
    const hasSubagentState = testpilot_subject.file_0003.ToolCallComponent.prototype.hasSubagentState;

    // helper to produce an object with all the expected properties in their "empty" state
    function makeEmptyState() {
        return {
            subagentAgentId: void 0,
            ongoingSubCalls: new Set(),        // .size === 0
            finishedSubCalls: [],              // .length === 0
            subToolActivities: new Set(),      // .size === 0
            subagentText: '',                  // .length === 0
            subagentThinkingText: '',          // .length === 0
            subagentPhase: void 0,
            backgroundTaskTerminalPhase: void 0
        };
    }

    it('returns false when all subagent-related properties are empty/undefined', function() {
        const obj = makeEmptyState();
        assert.strictEqual(hasSubagentState.call(obj), false);
    });

    })