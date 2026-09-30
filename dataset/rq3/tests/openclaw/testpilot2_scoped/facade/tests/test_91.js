let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isImageSizeError', function() {
        it('returns false for other image-related errors (not size-related)', function(done) {
            let msg = "Image corrupted or unreadable.";
            assert.strictEqual(testpilot_subject.file_0001.isImageSizeError(msg), false);
            done();
        });

            })
})