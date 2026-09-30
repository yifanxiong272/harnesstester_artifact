let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isImageDimensionErrorMessage', function() {
        it('should return false for unrelated error messages', function() {
            let msg = "Upload failed: network error, please retry";
            let res = testpilot_subject.file_0001.isImageDimensionErrorMessage(msg);
            assert.strictEqual(res, false);
        });

            })
})