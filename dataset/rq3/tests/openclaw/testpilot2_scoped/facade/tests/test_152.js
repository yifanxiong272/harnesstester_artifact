let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.sanitizeUserFacingText', function() {
        const sanitize = testpilot_subject.file_0001.sanitizeUserFacingText;

        it('should return the same benign ASCII text unchanged', function() {
            const input = "Hello, world!";
            const out = sanitize(input);
            // benign, printable ASCII should be preserved
            assert.strictEqual(typeof out, 'string');
            assert.strictEqual(out, input);
        });

            })
})