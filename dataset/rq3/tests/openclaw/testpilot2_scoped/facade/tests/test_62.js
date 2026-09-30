let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isCompactionFailureError', function() {
        const fn = testpilot_subject.file_0001.isCompactionFailureError;

        it('returns false for falsy values (null / empty)', function() {
            assert.strictEqual(fn(null), false, 'null should return false');
            assert.strictEqual(fn(undefined), false, 'undefined should return false');
            assert.strictEqual(fn(''), false, 'empty string should return false');
        });

            })
})