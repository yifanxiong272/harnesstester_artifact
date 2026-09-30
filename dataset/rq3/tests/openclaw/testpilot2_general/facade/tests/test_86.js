let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isContextOverflowError', function() {
        const fn = testpilot_subject.file_0001.isContextOverflowError;

        it('returns false for falsy/empty input', function() {
            assert.strictEqual(fn(null), false, 'null should not be considered a context overflow error');
            assert.strictEqual(fn(undefined), false, 'undefined should not be considered a context overflow error');
            assert.strictEqual(fn(''), false, 'empty string should not be considered a context overflow error');
        });

            })
})