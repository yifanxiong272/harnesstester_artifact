let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isCompactionFailureError', function() {
        it('returns false for empty or missing message', function() {
            const fn = testpilot_subject.file_0001.isCompactionFailureError;
            assert.strictEqual(fn(null), false, 'null should return false');
            assert.strictEqual(fn(undefined), false, 'undefined should return false');
            assert.strictEqual(fn(''), false, 'empty string should return false');
        });

            })
})