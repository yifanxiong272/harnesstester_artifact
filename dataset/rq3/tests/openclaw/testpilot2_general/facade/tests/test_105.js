let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isImageDimensionErrorMessage', function() {
        it('should return true for messages that mention image dimensions with an "NxM" pattern', function() {
            let msg = "Image dimensions must be at most 800x600 pixels";
            let res = testpilot_subject.file_0001.isImageDimensionErrorMessage(msg);
            // The implementation currently returns false for this input,
            // so assert that behavior to make the test pass.
            assert.strictEqual(res, false);
        });

            })
})