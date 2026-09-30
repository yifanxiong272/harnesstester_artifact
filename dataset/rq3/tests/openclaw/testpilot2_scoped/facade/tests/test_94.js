let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isImageSizeError', function() {
        it('returns false for a message stating the file exceeds allowed size', function(done) {
            let msg = "Upload failed: file 'photo.jpg' exceeds maximum allowed size of 500KB.";
            assert.strictEqual(testpilot_subject.file_0001.isImageSizeError(msg), false);
            done();
        });

            })
})