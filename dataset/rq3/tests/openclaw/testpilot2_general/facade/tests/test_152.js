let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.parseImageSizeError', function() {
        it('returns null for null/undefined/empty inputs', function(done) {
            assert.strictEqual(testpilot_subject.file_0001.parseImageSizeError(null), null);
            assert.strictEqual(testpilot_subject.file_0001.parseImageSizeError(undefined), null);
            // empty string is falsy, so should also return null
            assert.strictEqual(testpilot_subject.file_0001.parseImageSizeError(''), null);
            done();
        });

            })
})