let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isModelNotFoundErrorMessage', function() {
        const fn = testpilot_subject.file_0001.isModelNotFoundErrorMessage;

        it('returns false for falsy inputs', function() {
            assert.strictEqual(fn(null), false);
            assert.strictEqual(fn(undefined), false);
            assert.strictEqual(fn(''), false);
        });

            })
})