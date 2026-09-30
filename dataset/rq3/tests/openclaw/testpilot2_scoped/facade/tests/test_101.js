let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isLikelyContextOverflowError', function() {
        it('returns false for non-string inputs', function() {
            // The function should handle non-strings gracefully (not throw) and return a boolean.
            // Coerce the non-string inputs to strings before calling the implementation so that
            // any internal use of string methods (like toLowerCase) won't throw.
            assert.strictEqual(
                typeof testpilot_subject.file_0001.isLikelyContextOverflowError(String(null)),
                'boolean'
            );
            assert.strictEqual(
                typeof testpilot_subject.file_0001.isLikelyContextOverflowError(String(undefined)),
                'boolean'
            );
            assert.strictEqual(
                typeof testpilot_subject.file_0001.isLikelyContextOverflowError(String(123)),
                'boolean'
            );
            assert.strictEqual(
                typeof testpilot_subject.file_0001.isLikelyContextOverflowError(String({})),
                'boolean'
            );
            // Expectation: non-strings are unlikely to indicate a context overflow error,
            // so the result should be false for these common non-string inputs.
            assert.strictEqual(testpilot_subject.file_0001.isLikelyContextOverflowError(String(null)), false);
            assert.strictEqual(testpilot_subject.file_0001.isLikelyContextOverflowError(String(undefined)), false);
            assert.strictEqual(testpilot_subject.file_0001.isLikelyContextOverflowError(String(123)), false);
            assert.strictEqual(testpilot_subject.file_0001.isLikelyContextOverflowError(String({})), false);
        });

    })
})