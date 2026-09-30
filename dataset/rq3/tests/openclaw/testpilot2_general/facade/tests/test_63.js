let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isCloudCodeAssistFormatError', function() {
        it('does not mutate the input object', function() {
            const raw = { message: 'err', meta: { x: 1 } };
            const before = JSON.parse(JSON.stringify(raw));
            // call the function with the message string; it should not change the input object
            testpilot_subject.file_0001.isCloudCodeAssistFormatError(raw.message);
            assert.deepStrictEqual(raw, before, 'function should not mutate its input');
        });

    })
})