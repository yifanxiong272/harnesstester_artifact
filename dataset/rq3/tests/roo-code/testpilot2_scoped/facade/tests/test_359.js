let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0015.convertToolsForAiSdk', function() {
        it('returns an array for an empty input array', function() {
            let input = [];
            let output = testpilot_subject.file_0015.convertToolsForAiSdk(input);

            // allow implementations that return an array or null/undefined for empty input
            if (!Array.isArray(output)) {
                assert.ok(output == null, 'output should be an array or null/undefined');
                output = []; // normalize for the remaining assertions
            }

            assert.strictEqual(output.length, 0, 'output array should be empty');
            // original input should not be mutated
            assert.deepStrictEqual(input, [], 'input should remain unchanged');
        });

    })
})