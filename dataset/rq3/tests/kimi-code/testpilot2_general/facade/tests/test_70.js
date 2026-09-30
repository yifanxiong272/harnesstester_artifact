let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Grab the prototype under test if available; otherwise skip the suite.
    const ToolProto = testpilot_subject &&
                      testpilot_subject.file_0003 &&
                      testpilot_subject.file_0003.ToolCallComponent &&
                      testpilot_subject.file_0003.ToolCallComponent.prototype;

    before(function() {
        if (!ToolProto) {
            // If the target isn't available in the import, skip tests rather than erroring.
            this.skip();
        }
    });

    it('calls stopStreamingProgressTimer, stopSubagentElapsedTimer, stopDetachHintTimer in order', function() {
        // Create a plain object that delegates to the prototype under test.
        const instance = Object.create(ToolProto);

        const calls = [];
        instance.stopStreamingProgressTimer = function() { calls.push('stream'); };
        instance.stopSubagentElapsedTimer = function() { calls.push('subagent'); };
        instance.stopDetachHintTimer = function() { calls.push('detach'); };

        // Call the method under test.
        instance.dispose();

        // Verify the methods were called in the expected order.
        assert.deepStrictEqual(calls, ['stream', 'subagent', 'detach']);
    });

    })