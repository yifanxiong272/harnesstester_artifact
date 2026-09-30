let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isContextOverflowError', function() {
        it('returns false for falsy/empty inputs', function() {
            assert.strictEqual(testpilot_subject.file_0001.isContextOverflowError(null), false, 'null should return false');
            assert.strictEqual(testpilot_subject.file_0001.isContextOverflowError(undefined), false, 'undefined should return false');
            assert.strictEqual(testpilot_subject.file_0001.isContextOverflowError(''), false, 'empty string should return false');
        });

            })
})