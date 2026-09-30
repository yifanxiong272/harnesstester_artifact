let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0003.ToolCallComponent.prototype.onSubagentFailed', function() {
        // Safely grab the function under test; tests will fail clearly if structure is not present.
        const fn = testpilot_subject &&
                   testpilot_subject.file_0003 &&
                   testpilot_subject.file_0003.ToolCallComponent &&
                   testpilot_subject.file_0003.ToolCallComponent.prototype &&
                   testpilot_subject.file_0003.ToolCallComponent.prototype.onSubagentFailed;

        it('should exist and be a function', function() {
            assert.strictEqual(typeof fn, 'function');
        });

            })
})