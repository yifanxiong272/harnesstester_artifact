let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0004.injectSyntheticToolResults', function() {

        it('returns the same array reference when there are no tool_use blocks', function() {
            const messages = [
                { role: "assistant", content: [{ type: "text", content: "hello" }] },
                { role: "user", content: [{ type: "text", content: "hi" }] }
            ];

            const result = testpilot_subject.file_0004.injectSyntheticToolResults(messages);

            // No orphan tool_use -> should return the same array reference (no change)
            assert.strictEqual(result, messages);
        });

            })
})