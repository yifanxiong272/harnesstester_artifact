let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0012.sanitizeToolCallId', function() {
        it('should export a function', function() {
            assert.ok(testpilot_subject);
            assert.ok(testpilot_subject.file_0012, 'file_0012 namespace exists');
            assert.strictEqual(typeof testpilot_subject.file_0012.sanitizeToolCallId, 'function',
                'sanitizeToolCallId should be a function');
        });

            })
})