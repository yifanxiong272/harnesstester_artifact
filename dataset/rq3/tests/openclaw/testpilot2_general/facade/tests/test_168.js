let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0003.sanitizeToolUseResultPairing', function() {
        it('returns an empty array when given an empty messages array', function() {
            let messages = [];
            let options = {};
            let result = testpilot_subject.file_0003.sanitizeToolUseResultPairing(messages, options);
            // Expect an array (most sanitizers return an array) and empty for empty input
            assert.ok(Array.isArray(result), 'result should be an array');
            assert.deepStrictEqual(result, [], 'expected empty array for empty input');
        });

            })
})