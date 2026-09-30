let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isContextOverflowError', function() {
        it('returns false for unrelated error messages', function() {
            const negatives = [
                "Out of memory",
                "RangeError: Maximum call stack size exceeded",
                "OverflowError",
                "Some random error",
                "",
                "context overflower", // typo should not match
                "overflow" // generic overflow shouldn't necessarily be a context overflow
            ];

            negatives.forEach(msg => {
                const result = testpilot_subject.file_0001.isContextOverflowError(msg);
                assert.strictEqual(typeof result, 'boolean', `expected boolean for message: ${msg}`);
                assert.strictEqual(result, false, `expected false for message: ${msg}`);
            });
        });

            })
})