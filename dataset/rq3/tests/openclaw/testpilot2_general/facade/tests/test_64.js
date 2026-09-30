let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isCloudCodeAssistFormatError', function() {
        it('returns the same result for deep-equal but different-reference objects', function() {
            const raw = { message: 'error', meta: { a: 1, b: [1,2,3] } };
            const clone = JSON.parse(JSON.stringify(raw)); // different reference, same structure
            // isCloudCodeAssistFormatError expects a string message, not the whole object
            const r1 = testpilot_subject.file_0001.isCloudCodeAssistFormatError(raw.message);
            const r2 = testpilot_subject.file_0001.isCloudCodeAssistFormatError(clone.message);
            assert.strictEqual(r1, r2, 'expected same result for deep-equal objects');
        });

    })
})