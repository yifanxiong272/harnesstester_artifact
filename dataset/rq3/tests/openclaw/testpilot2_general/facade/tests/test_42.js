let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
    describe('file_0001.isAuthAssistantError', function() {
        it('returns false for falsy msg (null)', function() {
            assert.strictEqual(testpilot_subject.file_0001.isAuthAssistantError(null), false);
            assert.strictEqual(testpilot_subject.file_0001.isAuthAssistantError(undefined), false);
        });

            })
})