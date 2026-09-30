let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0009.sanitizeToolCallId', function() {
        const fn = testpilot_subject.file_0009 && testpilot_subject.file_0009.sanitizeToolCallId;

        it('should export a function', function() {
            assert.strictEqual(typeof fn, 'function', 'sanitizeToolCallId should be a function');
        });

            })
})