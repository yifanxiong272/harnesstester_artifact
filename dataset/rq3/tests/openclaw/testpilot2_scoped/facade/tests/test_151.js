let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.parseImageSizeError', function() {

        it('returns null for falsy input', function() {
            const fn = testpilot_subject.file_0001.parseImageSizeError;
            assert.strictEqual(fn(null), null);
            assert.strictEqual(fn(undefined), null);
            // empty string is falsy-ish for user input; function checks !raw so empty should return null
            assert.strictEqual(fn(''), null);
        });

            })
})