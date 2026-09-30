let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isImageSizeError', function() {
        it('is case-sensitive when detecting image size errors', function(done) {
            let msg = "IMAGE SIZE TOO LARGE";
            assert.strictEqual(testpilot_subject.file_0001.isImageSizeError(msg), false);
            done();
        });

    })
})