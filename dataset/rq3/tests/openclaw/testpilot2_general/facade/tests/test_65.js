let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isCloudCodeAssistFormatError', function() {
        it('is deterministic for repeated calls with the same object reference', function() {
            const raw = { message: 'oops', code: 42, location: { line: 1, col: 2 } };
            // pass the message string (the function expects a string and was calling toLowerCase)
            const first = testpilot_subject.file_0001.isCloudCodeAssistFormatError(raw.message);
            const second = testpilot_subject.file_0001.isCloudCodeAssistFormatError(raw.message);
            assert.strictEqual(first, second, 'function should return the same result on repeated calls with same input');
        });

            })
})