let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('formatSingleSubagentStatsText - singular tool, no elapsed, no tokens', function() {
        const proto = testpilot_subject.file_0003.ToolCallComponent.prototype;

        // Create a minimal instance with 1 activity, undefined elapsed and no usage/tokens
        const inst = {
            subToolActivities: new Set([1]),
            getSubagentElapsedSeconds: () => undefined,
            subagentContextTokens: undefined,
            subagentUsage: undefined
        };

        // Use the original prototype method. Because elapsed is undefined and tokens path
        // leads to 0, the method should not attempt to call formatElapsed/formatTokens/usageTotal.
        const out = proto.formatSingleSubagentStatsText.call(inst);
        assert.strictEqual(out, ' \u00B7 1 tool');
    });

    })