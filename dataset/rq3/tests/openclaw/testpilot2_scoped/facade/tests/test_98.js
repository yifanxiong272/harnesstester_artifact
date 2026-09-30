let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isLikelyContextOverflowError', function() {
        it('returns false for unrelated or common JS errors', function() {
            assert.strictEqual(
                testpilot_subject.file_0001.isLikelyContextOverflowError('ReferenceError: foo is not defined'),
                false
            );
            assert.strictEqual(
                testpilot_subject.file_0001.isLikelyContextOverflowError('RangeError: Maximum call stack size exceeded'),
                false
            );
            assert.strictEqual(
                testpilot_subject.file_0001.isLikelyContextOverflowError('Out of memory'),
                false
            );
            assert.strictEqual(
                testpilot_subject.file_0001.isLikelyContextOverflowError(''),
                false
            );
        });

            })
})