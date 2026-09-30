let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.parseImageDimensionError', function() {
        const fn = testpilot_subject.file_0001.parseImageDimensionError;

        it('returns null for falsy inputs (null, undefined, empty string)', function() {
            assert.strictEqual(fn(null), null);
            assert.strictEqual(fn(undefined), null);
            assert.strictEqual(fn(''), null);
        });

            })
})